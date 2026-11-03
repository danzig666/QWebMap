"""
QGIS raster layers -> their own raster PMTiles archive (PNG / JPEG / WebP).

Vector layers are never rasterized: the map data stays MVT. A *raster*
layer of the project (an orthophoto, a scanned plan, a DEM rendered with its
QGIS colour ramp, a WMS/XYZ layer) is rendered by QGIS itself, exactly as on
the canvas (its renderer, resampling, layer opacity and scale range), into
Web Mercator tiles packed into ``data/raster-<id>.pmtiles``. The viewer's
opacity slider multiplies that.

* Rendering runs on QGIS's main thread in metatiles (``RenderMapTile``
  flag, no seams), one layer at a time; cancellation is checked per
  metatile.
* Fully transparent tiles are not stored (the viewer shows nothing there).
* Identical tiles are stored once; the archive is validated (structure,
  image signatures) before it is renamed into place.
* Layer blend modes (the browser has none): a *multiply* layer becomes black
  with transparency 1 - brightness, a *screen* layer white with transparency
  = brightness - exact for grey rasters such as a hillshade, whatever is
  drawn below. Colour pixels use their luminance (reported as approximate).
"""

import math
import os
import shutil
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsMapRendererParallelJob,
                       QgsMapSettings, QgsRasterLayer, QgsRectangle, QgsSettings)
from qgis.PyQt.QtCore import QBuffer, QByteArray, QIODevice, QRect, QSize
from qgis.PyQt.QtGui import QColor, QImage, QImageWriter, QPainter

from .errors import PublishingError
from .models import LayerConfig, PublicationProfile
from .pmtiles_builder import IMAGE_TILE_TYPES, ArchiveDescriptor, TileSink
from .progress import Progress
from .vendor.pmtiles.tile import Compression

ORIGIN = 20037508.342789244          # half the Web Mercator world width (m)
WEB_MERCATOR = "EPSG:3857"
LARGE_TILES_PER_LAYER = 400_000      # past this a layer takes hours: warned about (no limit)
ONLINE_PROVIDERS = {"wms", "arcgismapserver", "arcgisfeatureserver", "xyz", "wcs"}


@dataclass
class RasterPlan:
    layer_id: str
    min_zoom: int
    max_zoom: int
    tiles: int                        # upper bound (tiles touching the area)
    extent_3857: Tuple[float, float, float, float]
    online: bool = False
    warnings: List[str] = field(default_factory=list)
    # Ground metres per pixel of the layer's own image (None: unknown, e.g.
    # an online service) and the latitude the tile resolutions refer to.
    native_m: Optional[float] = None
    latitude: float = 0.0
    hidpi: bool = False

    def resolution(self, zoom: int) -> float:
        """Ground metres per tile pixel at ``zoom`` (512 px tiles: half)."""
        return ground_resolution(zoom, self.latitude, self.hidpi)


def is_raster(layer) -> bool:
    return isinstance(layer, QgsRasterLayer)


def ground_resolution(zoom: float, latitude: float, hidpi: bool = False) -> float:
    """Ground metres per pixel of a Web Mercator tile at ``zoom`` and ``latitude``
    (256 px tiles; 512 px "HiDPI" tiles have twice the pixels)."""
    return 2 * ORIGIN / 256 / 2 ** zoom * math.cos(math.radians(latitude)) / (2 if hidpi else 1)


def native_zoom(native_m: float, latitude: float, hidpi: bool = False) -> int:
    """The lowest zoom whose tiles are as sharp as an image of ``native_m``
    ground metres per pixel (3.5 % tolerance: 0.4 m at 48° N is zoom 18)."""
    exact = math.log2(2 * ORIGIN / 256 * math.cos(math.radians(latitude))
                      / (native_m * (2 if hidpi else 1)))
    return max(0, min(22, int(math.ceil(exact - 0.05))))


def sharp_zoom(native_m: float, latitude: float, hidpi: bool = False, online: bool = False) -> int:
    """The maximum zoom of "Like the image": one deeper than native_zoom
    for an image of its own. At native_zoom the tiles are as fine as the
    image but resampled from it on another pixel grid, and zoomed in past
    them the browser enlarges those already resampled tiles: two bilinear
    passes, where QGIS draws from the image itself (measured: 78-85 % of
    QGIS's edge sharpness one to two zooms in, 91-99 % with one zoom more,
    no gain with two). An online tiled service keeps native_zoom: its tiles
    are on the same grid, copied as they are."""
    zoom = native_zoom(native_m, latitude, hidpi)
    return zoom if online else min(22, zoom + 1)


def native_resolution(layer, transform_context=None) -> Optional[float]:
    """Ground metres per pixel of the layer's own image (the mean of x and y,
    one pixel measured on the WGS 84 ellipsoid at the image's centre, so any
    CRS works: Web Mercator metres are not ground metres), or None when
    unknown: online services serve any resolution."""
    if (layer.providerType() or "").lower() in ONLINE_PROVIDERS:
        return None
    try:
        px, py = abs(float(layer.rasterUnitsPerPixelX())), abs(float(layer.rasterUnitsPerPixelY()))
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None
    if not px > 0 or not py > 0 or not layer.crs().isValid():
        return None
    from qgis.core import (QgsCoordinateTransformContext, QgsDistanceArea,  # pylint: disable=import-outside-toplevel
                           QgsPointXY)
    area = QgsDistanceArea()
    area.setSourceCrs(layer.crs(), transform_context or QgsCoordinateTransformContext())
    area.setEllipsoid("WGS84")
    centre = layer.extent().center()
    try:
        dx = area.measureLine(QgsPointXY(centre.x(), centre.y()), QgsPointXY(centre.x() + px, centre.y()))
        dy = area.measureLine(QgsPointXY(centre.x(), centre.y()), QgsPointXY(centre.x(), centre.y() + py))
    except Exception:  # noqa: BLE001 - a point outside the CRS's area
        return None
    if not dx > 0 or not dy > 0:
        return None
    return math.sqrt(dx * dy)


def service_resolution(layer, transform_context, at_3857) -> Optional[float]:
    """Ground metres per pixel of the finest tiles of a tiled online service
    (XYZ, WMTS: QGIS lists their tile resolutions), measured at ``at_3857``
    (the published area's centre, Web Mercator); None for services that
    draw at any resolution (plain WMS)."""
    try:
        finest = min((r for r in layer.dataProvider().nativeResolutions() if r > 0), default=None)
    except (AttributeError, RuntimeError, TypeError, ValueError):
        finest = None
    if not finest:
        finest = _xyz_zmax_resolution(layer)
    if not finest or not layer.crs().isValid():
        return None
    from qgis.core import (QgsCoordinateTransformContext, QgsDistanceArea,  # pylint: disable=import-outside-toplevel
                           QgsPointXY)
    context = transform_context or QgsCoordinateTransformContext()
    try:
        to_layer = QgsCoordinateTransform(QgsCoordinateReferenceSystem(WEB_MERCATOR), layer.crs(), context)
        centre = to_layer.transform(QgsPointXY(at_3857))
        area = QgsDistanceArea()
        area.setSourceCrs(layer.crs(), context)
        area.setEllipsoid("WGS84")
        dx = area.measureLine(centre, QgsPointXY(centre.x() + finest, centre.y()))
        dy = area.measureLine(centre, QgsPointXY(centre.x(), centre.y() + finest))
    except Exception:  # noqa: BLE001 - a point outside the CRS's area
        return None
    return math.sqrt(dx * dy) if dx > 0 and dy > 0 else None


def _xyz_zmax_resolution(layer) -> Optional[float]:
    """Web Mercator metres per pixel at the ``zmax`` of an XYZ layer's source
    ("type=xyz&url=...&zmax=18"), or None."""
    from urllib.parse import parse_qs  # pylint: disable=import-outside-toplevel
    query = parse_qs(layer.source() or "")
    if (query.get("type") or [""])[0].lower() != "xyz":
        return None
    try:
        zmax = int((query.get("zmax") or [""])[0])
    except ValueError:
        return None
    return 2 * ORIGIN / 256 / (1 << max(0, min(zmax, 24)))


def zoom_range(config: LayerConfig, profile: PublicationProfile) -> Tuple[int, int]:
    low = profile.view.min_zoom if config.raster_min_zoom is None else config.raster_min_zoom
    high = profile.view.max_zoom if config.raster_max_zoom is None else config.raster_max_zoom
    return int(low), int(max(low, high))


def tile_span(extent: Tuple[float, float, float, float], z: int) -> Tuple[int, int, int, int]:
    """Inclusive XYZ tile range (x0, y0, x1, y1) covering a 3857 extent."""
    size = 2 * ORIGIN / (1 << z)
    n = (1 << z) - 1
    x0 = int(math.floor((extent[0] + ORIGIN) / size))
    x1 = int(math.floor((extent[2] + ORIGIN) / size - 1e-9))
    y0 = int(math.floor((ORIGIN - extent[3]) / size))
    y1 = int(math.floor((ORIGIN - extent[1]) / size - 1e-9))
    return max(0, x0), max(0, y0), min(n, x1), min(n, y1)


def count_tiles(extent, min_zoom: int, max_zoom: int) -> int:
    total = 0
    for z in range(min_zoom, max_zoom + 1):
        x0, y0, x1, y1 = tile_span(extent, z)
        total += max(0, x1 - x0 + 1) * max(0, y1 - y0 + 1)
    return total


def plan_layer(project, layer, config: LayerConfig, profile: PublicationProfile,
               extent_3857: QgsRectangle) -> RasterPlan:
    """Zooms, area (export extent ∩ layer extent) and an upper bound of tiles.
    Without a maximum zoom, "like the image" (``raster_match_native``): the
    zoom past which the image has no more detail (sharp_zoom); else the map's."""
    web = QgsCoordinateReferenceSystem(WEB_MERCATOR)
    area = QgsRectangle(extent_3857)
    warnings = []
    try:
        to_web = QgsCoordinateTransform(layer.crs(), web, project.transformContext())
        layer_extent = to_web.transformBoundingBox(layer.extent())
        if layer_extent.isFinite() and not layer_extent.isEmpty():
            area = area.intersect(layer_extent)
    except Exception:  # noqa: BLE001 - provider without a usable extent (e.g. XYZ): the export extent
        pass
    centre_y = (area if not area.isEmpty() else QgsRectangle(extent_3857)).center().y()
    latitude = math.degrees(math.atan(math.sinh(centre_y / 6378137.0)))
    native_m = native_resolution(layer, project.transformContext())
    if native_m is None and (layer.providerType() or "").lower() in ONLINE_PROVIDERS:
        # A tiled service (XYZ, WMTS): as sharp as its finest tiles.
        centre = (area if not area.isEmpty() else QgsRectangle(extent_3857)).center()
        native_m = service_resolution(layer, project.transformContext(), centre)
    hidpi = bool(getattr(config, "raster_hidpi", False))
    low, high = zoom_range(config, profile)
    online = (layer.providerType() or "").lower() in ONLINE_PROVIDERS
    if config.raster_max_zoom is None and getattr(config, "raster_match_native", False) and native_m:
        high = max(low, sharp_zoom(native_m, latitude, hidpi, online))
    # Not rendered where the layer is hidden on the web (its scale range).
    from .qgis_model import _zoom_of_scale, layer_scale_range  # pylint: disable=import-outside-toplevel
    out_scale, in_scale = layer_scale_range(layer, config)
    if out_scale and _zoom_of_scale(out_scale) is not None:
        low = min(high, max(low, int(math.floor(_zoom_of_scale(out_scale)))))
    if in_scale and _zoom_of_scale(in_scale) is not None:
        high = max(low, min(high, int(math.ceil(_zoom_of_scale(in_scale)))))
    if online:
        warnings.append(f'"{layer.name()}" is an online map service: check that its licence allows '
                        "republishing its images.")
    box = (area.xMinimum(), area.yMinimum(), area.xMaximum(), area.yMaximum())
    tiles = 0 if area.isEmpty() else count_tiles(box, low, high)
    return RasterPlan(layer.id(), low, high, tiles, box, online, warnings, native_m, latitude, hidpi)


def plan_vector_image(project, layer, profile: PublicationProfile, extent_3857: QgsRectangle,
                      below: int, hidpi: bool = False) -> Optional[RasterPlan]:
    """Image tiles of a vector layer drawn as images zoomed out
    (LayerConfig.zoomed_out "image"): the publication's first zoom up to
    the zoom below ``below``, over the export extent ∩ the layer's extent
    (and its web scale range, as plan_layer). None: no such zoom.
    ``hidpi``: rendered at twice the pixels (and DPI), as vector_image_hidpi."""
    config = LayerConfig(layer.id(), raster_match_native=False, raster_min_zoom=int(profile.view.min_zoom),
                         raster_max_zoom=int(below) - 1, raster_hidpi=bool(hidpi))
    if config.raster_max_zoom < config.raster_min_zoom:
        return None
    plan = plan_layer(project, layer, config, profile, extent_3857)
    if plan.max_zoom >= below or plan.min_zoom > plan.max_zoom:
        plan.max_zoom = min(plan.max_zoom, int(below) - 1)
        if plan.min_zoom > plan.max_zoom:
            return None
        plan.tiles = count_tiles(plan.extent_3857, plan.min_zoom, plan.max_zoom)
    return plan


def vector_image_hidpi(profile: PublicationProfile) -> bool:
    """Image tiles of vector layers at twice the pixels and DPI when the web
    map thins its hairlines (OutputOptions.thin_hairlines): QGIS draws a
    hairline one image pixel wide, so at 2x it is half a CSS pixel - what
    the thinned vector hairlines are on a high-resolution screen (and a
    lighter line on others, the browser scaling it down) - instead of a
    full, on such screens blurred, pixel that fills a dense parcel grid in.
    Every other size stays: the DPI doubles with the pixels."""
    return bool(getattr(profile.output, "thin_hairlines", True))


def _metres(value: float) -> str:
    return f"{value:.2f} m" if value < 10 else f"{value:.0f} m"


def large_raster_advice(plan: RasterPlan, name: str, config: LayerConfig, map_max_zoom: int) -> str:
    """Why a raster layer has more than LARGE_TILES_PER_LAYER tiles (the
    setting that sets its sharpest zoom) and what brings it under that:
    each zoom less is about a quarter of the tiles, a smaller extent fewer."""
    def count(high):
        return count_tiles(plan.extent_3857, plan.min_zoom, max(plan.min_zoom, high))

    def number(value):
        return f"{value:,}".replace(",", "\u202f")

    top = plan.max_zoom
    if config.raster_max_zoom is not None:
        cause = f'"Sharpest detail" is {_metres(plan.resolution(top))} per pixel (zoom {top})'
    elif config.raster_match_native and plan.native_m:
        cause = (f'"Sharpest detail" is "Like the image" ({_metres(plan.native_m)} per pixel: '
                 f"zoom {top})")
    else:
        cause = (f'"Sharpest detail" is "Like the map": the Map tab\'s Maximum tile zoom, {map_max_zoom} '
                 f"({_metres(plan.resolution(top))} per pixel)")
    lines = [f'"{name}": up to {number(plan.tiles)} tiles at zooms {plan.min_zoom}–{top}. '
             f"Its {cause}.", "To go lower (Interaction tab, the layer's raster settings):"]
    fits = next((z for z in range(top - 1, plan.min_zoom - 1, -1) if count(z) <= LARGE_TILES_PER_LAYER), None)
    if top - 1 >= plan.min_zoom:
        lines.append(f"• Sharpest detail {_metres(plan.resolution(top - 1))} per pixel (zoom {top - 1}): "
                     f"about {number(count(top - 1))} tiles")
    if fits is not None and fits != top - 1:
        lines.append(f"• Sharpest detail {_metres(plan.resolution(fits))} per pixel (zoom {fits}): "
                     f"about {number(count(fits))} tiles")
    side = math.sqrt(plan.tiles / LARGE_TILES_PER_LAYER)
    lines.append(f"• Or a smaller extent: about {side:.1f}× smaller on each side for "
                 f"{number(LARGE_TILES_PER_LAYER)} tiles.")
    lines.append('"Shown from zoom" barely helps: the sharpest zoom holds three quarters of the tiles.')
    return "\n".join(lines)


def large_raster_warning(plan: RasterPlan, name: str) -> str:
    """One line for the export log."""
    return (f'Raster layer "{name}": up to {plan.tiles} tiles at zooms {plan.min_zoom}-{plan.max_zoom}; '
            "the export can take hours. A coarser \"Sharpest detail\" (Interaction tab) or a smaller "
            "extent makes it much faster.")


def _encoder(fmt: str) -> str:
    return {"png": "PNG", "jpeg": "JPEG", "webp": "WEBP"}[fmt]


def tile_format(fmt: str) -> str:
    """The image format the tiles are written in: WebP (the default) falls
    back to PNG, also transparent, where this QGIS cannot write WebP."""
    if fmt == "webp":
        supported = {bytes(f).decode().lower() for f in QImageWriter.supportedImageFormats()}
        if "webp" not in supported:
            return "png"
    return fmt


def _encode(image: QImage, writer_format: str, quality: int) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, writer_format, -1 if writer_format == "PNG" else int(quality)):
        raise PublishingError("Q2VT_PUB_BUNDLE_INVALID", f"Could not encode a {writer_format} tile.")
    buffer.close()
    return bytes(data)


def _transparent(image: QImage) -> bool:
    """True when every pixel's alpha is 0 (nothing to show)."""
    import numpy as np  # pylint: disable=import-outside-toplevel
    image = image.convertToFormat(QImage.Format.Format_ARGB32)
    ptr = image.constBits()
    size = image.sizeInBytes() if hasattr(image, "sizeInBytes") else image.byteCount()
    ptr.setsize(size)
    pixels = np.frombuffer(ptr, dtype=np.uint8).reshape(image.height(), image.bytesPerLine())
    alpha = pixels[:, 3:image.width() * 4:4]  # ARGB32 little endian: B G R A
    return not alpha.any()


# QgsOpenClUtils::enabled() reads this setting on every raster block
# (QgsSettings, section Core); the class itself is not in PyQGIS.
OPENCL_SETTING = "core/OpenClEnabled"


@contextmanager
def opencl_off():
    """OpenCL raster processing switched off for the renders inside
    (QGIS's *Settings > Options > Acceleration*), restored afterwards.

    QGIS's OpenCL hillshade (QgsHillshadeRenderer::block, QGIS 3.x and 4.x)
    copies the block's second row before checking there is one: a block one
    pixel high, as the many small reprojected tile renders of an export ask
    for, reads a null row and crashes QGIS; its program cache is also shared
    by renders running at once. The CPU path draws the same hillshade."""
    settings = QgsSettings()
    had = settings.contains(OPENCL_SETTING)
    before = settings.value(OPENCL_SETTING, False)
    on = str(before).lower() in ("1", "true")
    if on:
        settings.setValue(OPENCL_SETTING, False)
    try:
        yield
    finally:
        if on:
            if had:
                settings.setValue(OPENCL_SETTING, before)
            else:
                settings.remove(OPENCL_SETTING)


def render_layer(project, layer, config: LayerConfig, plan: RasterPlan, output: str,
                 progress: Optional[Progress] = None, metatile: int = 8,
                 title: str = "", blend: str = "normal", threads: int = 1) -> Optional[ArchiveDescriptor]:
    """_render_layer with OpenCL off (opencl_off: QGIS's OpenCL hillshade
    crashes on the export's renders)."""
    with opencl_off():
        warped = warped_copy(layer, plan, 512 if config.raster_hidpi else 256, output + ".warp.tif")
        try:
            return _render_layer(project, warped or layer, config, plan, output, progress, metatile,
                                 title, blend, threads)
        finally:
            if warped is not None:
                source = warped.source()
                del warped
                for path in (source, source + ".aux.xml"):
                    try:
                        os.remove(path)
                    except OSError:
                        pass


# A copy warped once is used up to this many pixels (and while the disk has
# room for it): beyond, the tiles are rendered from the layer itself.
WARP_MAX_PIXELS = 1_500_000_000


def warped_copy(layer, plan: RasterPlan, tile_px: int, path: str) -> Optional[QgsRasterLayer]:
    """The layer's image warped once to Web Mercator (GDAL, all cores) as a
    layer with the same style, or None to render from the layer itself.

    QGIS reprojects a raster for every tile it renders (QgsRasterProjector,
    pixel by pixel); a polar image tiled to zoom 7 took 27 s, from the copy
    12 s with its warping. The copy covers the tiles of the plan's lowest
    zoom (zoomed-out tiles show the image outside the export extent too) cut
    to the image, at the resolution of the highest zoom's tile pixels.
    Nearest neighbour, or the layer's own resampling for a continuous
    (not paletted) image. An image without nodata gets an alpha band, so the
    area around it stays transparent. Local GDAL files in another CRS only."""
    from osgeo import gdal  # pylint: disable=import-outside-toplevel
    if layer.providerType() != "gdal" or layer.crs().authid() == WEB_MERCATOR:
        return None
    renderer = layer.renderer()
    if renderer is None or renderer.type() in ("hillshade", "contour"):
        # Drawn from the slope / the heights between neighbouring pixels, by
        # their size in the layer's CRS: a Web Mercator copy (pixels about
        # 1/cos(latitude) longer) would shade flatter, contour differently.
        return None
    source = layer.source().split("|")[0]
    if not os.path.isfile(source) or not _curved_to_mercator(layer):
        return None
    try:
        dataset = gdal.Open(source)
        if dataset is None:
            return None
        bands = [dataset.GetRasterBand(i + 1) for i in range(dataset.RasterCount)]
        mercator = gdal.AutoCreateWarpedVRT(dataset, None, _mercator_wkt())
        if mercator is None:
            return None
        gt = mercator.GetGeoTransform()
        image = (gt[0], gt[3] + gt[5] * mercator.RasterYSize, gt[0] + gt[1] * mercator.RasterXSize, gt[3])
        mercator = None
        x0, y0, x1, y1 = tile_span(plan.extent_3857, plan.min_zoom)
        size = 2 * ORIGIN / (1 << plan.min_zoom)
        tiles = (-ORIGIN + x0 * size, ORIGIN - (y1 + 1) * size, -ORIGIN + (x1 + 1) * size, ORIGIN - y0 * size)
        bounds = (max(image[0], tiles[0], -ORIGIN), max(image[1], tiles[1], -ORIGIN),
                  min(image[2], tiles[2], ORIGIN), min(image[3], tiles[3], ORIGIN))
        if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
            return None
        resolution = 2 * ORIGIN / (tile_px * (1 << plan.max_zoom))
        pixels = (bounds[2] - bounds[0]) / resolution * (bounds[3] - bounds[1]) / resolution
        bytes_per_pixel = sum(gdal.GetDataTypeSize(b.DataType) // 8 for b in bands) + 1
        free = shutil.disk_usage(os.path.dirname(path) or ".").free
        if pixels > WARP_MAX_PIXELS or pixels * bytes_per_pixel > free / 2:
            return None
        alpha = any(b.GetColorInterpretation() == gdal.GCI_AlphaBand for b in bands)
        nodata = [b.GetNoDataValue() for b in bands]
        add_alpha, fill = False, None
        if not alpha and any(value is None for value in nodata):
            # The area around the image must stay transparent: an alpha band
            # for 8-bit images (QGIS reads alpha as 0-255), else a nodata
            # value the image does not use.
            if all(b.DataType == gdal.GDT_Byte for b in bands):
                add_alpha = True
            else:
                fill = _unused_value(bands)
                if fill is None:
                    return None
        options = dict(dstSRS=WEB_MERCATOR, xRes=resolution, yRes=resolution, outputBounds=bounds,
                       targetAlignedPixels=True, resampleAlg=_warp_resampling(layer),
                       creationOptions=["TILED=YES", "COMPRESS=ZSTD", "ZSTD_LEVEL=1",
                                        "NUM_THREADS=ALL_CPUS", "BIGTIFF=IF_SAFER", "SPARSE_OK=YES"],
                       warpOptions=["NUM_THREADS=ALL_CPUS"], multithread=True, warpMemoryLimit=512,
                       dstAlpha=add_alpha)
        if fill is not None:
            options["dstNodata"] = fill
        dataset = None
        if os.path.exists(path):
            os.remove(path)
        if gdal.Warp(path, source, **options) is None:
            return None
    except (RuntimeError, OSError):  # GDAL (exceptions on), disk: from the layer itself
        return None
    from qgis.PyQt.QtXml import QDomDocument  # pylint: disable=import-outside-toplevel
    copy = QgsRasterLayer(path, layer.name(), "gdal")
    if not copy.isValid():
        return None
    document = QDomDocument()
    layer.exportNamedStyle(document)
    copy.importNamedStyle(document)
    if add_alpha and copy.renderer() is not None:
        copy.renderer().setAlphaBand(copy.bandCount())
    return copy


# Warped once only where QGIS's per-tile reprojection is slow: the image's
# way to Web Mercator is far from linear (a polar projection: tens of
# percent; a national grid over a town: a millionth, where a copy at the
# finest zoom took longer than it saved).
_CURVED = 0.002


def _curved_to_mercator(layer) -> bool:
    """Whether the layer's extent, taken to Web Mercator, departs from the
    best affine fit by more than _CURVED of its size."""
    import numpy as np  # pylint: disable=import-outside-toplevel
    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPointXY, QgsProject  # pylint: disable=import-outside-toplevel
    box = layer.extent()
    if box.isEmpty():
        return False
    transform = QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem(WEB_MERCATOR),
                                       QgsProject.instance())
    source, target = [], []
    for fx in np.linspace(0, 1, 7):
        for fy in np.linspace(0, 1, 7):
            x, y = box.xMinimum() + fx * box.width(), box.yMinimum() + fy * box.height()
            try:
                point = transform.transform(QgsPointXY(x, y))
            except Exception:  # noqa: BLE001 - outside the CRS's area: curved enough
                return True
            if not (math.isfinite(point.x()) and math.isfinite(point.y())):
                return True
            source.append((x, y, 1.0))
            target.append((point.x(), point.y()))
    a, b = np.array(source), np.array(target)
    fit, *_ = np.linalg.lstsq(a, b, rcond=None)
    misfit = float(np.abs(a @ fit - b).max())
    size = float(max(np.ptp(b[:, 0]), np.ptp(b[:, 1]), 1e-9))
    return misfit / size > _CURVED


def _unused_value(bands) -> Optional[float]:
    """A value outside every band's range that their data type holds (a
    nodata value for the warped copy), or None."""
    from osgeo import gdal  # pylint: disable=import-outside-toplevel
    low = min(b.ComputeRasterMinMax(False)[0] for b in bands)
    high = max(b.ComputeRasterMinMax(False)[1] for b in bands)
    kind = bands[0].DataType
    if any(b.DataType != kind for b in bands):
        return None
    if kind in (gdal.GDT_Float32, gdal.GDT_Float64):
        return -3.4e38 if low > -3.4e38 else None
    ranges = {gdal.GDT_UInt16: (0, 65535), gdal.GDT_Int16: (-32768, 32767),
              gdal.GDT_UInt32: (0, 4294967295), gdal.GDT_Int32: (-2147483648, 2147483647)}
    if kind not in ranges:
        return None
    first, last = ranges[kind]
    if low > first:
        return float(first)
    if high < last:
        return float(last)
    return None


def _mercator_wkt() -> str:
    from osgeo import osr  # pylint: disable=import-outside-toplevel
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3857)
    return srs.ExportToWkt()


def _warp_resampling(layer) -> str:
    """gdalwarp resampling of the warped copy: nearest neighbour, or the
    layer's zoomed-in resampling (bilinear / cubic) for an image that is not
    paletted (QGIS resamples its colours; values in between are no class)."""
    renderer = layer.renderer()
    if renderer is None or renderer.type() in ("paletted", "singlebandcolordata"):
        return "near"
    resample = layer.resampleFilter()
    method = resample.zoomedInResampler() if resample is not None else None
    name = type(method).__name__.lower() if method is not None else ""
    return "cubic" if "cubic" in name else "bilinear" if "bilinear" in name else "near"


def _render_layer(project, layer, config: LayerConfig, plan: RasterPlan, output: str,
                  progress: Optional[Progress] = None, metatile: int = 8,
                  title: str = "", blend: str = "normal", threads: int = 1) -> Optional[ArchiveDescriptor]:
    """Render ``layer`` into ``output`` (PMTiles). Returns None when the layer
    draws nothing in the export extent. ``blend`` "multiply" / "screen":
    the tiles are converted to the equivalent normal image (blend_to_alpha);
    a colour (not grey) layer is then approximate (added to plan.warnings).

    ``threads``: metatiles rendered at once (QGIS map render jobs, as QGIS's
    own XYZ tile tool runs them, started and collected on this thread) and
    tiles cut and encoded at once (Qt releases the GIL while encoding).
    Results are written in a fixed order: the archive is the same for any
    number of threads."""
    progress = progress or Progress()
    if plan.tiles == 0:
        return None
    from collections import deque  # pylint: disable=import-outside-toplevel
    from concurrent.futures import ThreadPoolExecutor  # pylint: disable=import-outside-toplevel
    fmt = tile_format(config.raster_format)
    if fmt != config.raster_format:
        plan.warnings.append(f'Raster layer "{layer.name()}": this QGIS cannot write WebP images, '
                             "so its tiles are PNG (larger).")
    writer_format = _encoder(fmt)
    tile_px = 512 if config.raster_hidpi else 256
    settings = QgsMapSettings()
    settings.setLayers([layer])
    settings.setDestinationCrs(QgsCoordinateReferenceSystem(WEB_MERCATOR))
    settings.setTransformContext(project.transformContext())
    settings.setBackgroundColor(QColor(0, 0, 0, 0))
    settings.setOutputDpi(96.0 * tile_px / 256)
    settings.setFlag(QgsMapSettings.Flag.Antialiasing, True)
    settings.setFlag(QgsMapSettings.Flag.RenderMapTile, True)
    settings.setFlag(QgsMapSettings.Flag.DrawLabeling, False)
    jpeg = fmt == "jpeg"
    if blend in ("multiply", "screen") and jpeg:
        plan.warnings.append(f'Raster layer "{layer.name()}": its {blend} blend mode needs transparency; '
                             "JPEG has none, so it is drawn as normal. Choose PNG or WebP.")
        blend = "normal"
    threads = max(1, int(threads))

    def cut(image: QImage, z: int, mx: int, my: int, nx: int, ny: int):
        """Worker: the metatile's non-empty tiles, encoded."""
        grey = True
        if blend in ("multiply", "screen"):
            image, grey = blend_to_alpha(image, blend)
        tiles = []
        for ix in range(nx):
            for iy in range(ny):
                tile = image.copy(QRect(ix * tile_px, iy * tile_px, tile_px, tile_px))
                if _transparent(tile):
                    continue
                if jpeg:  # no alpha: composite on white
                    flat = QImage(tile.size(), QImage.Format.Format_RGB32)
                    flat.fill(QColor(255, 255, 255))
                    p = QPainter(flat)
                    p.drawImage(0, 0, tile)
                    p.end()
                    tile = flat
                tiles.append((z, mx + ix, my + iy, _encode(tile, writer_format, config.raster_quality)))
        return tiles, grey, nx * ny

    def metatiles():
        for z in range(plan.min_zoom, plan.max_zoom + 1):
            x0, y0, x1, y1 = tile_span(plan.extent_3857, z)
            size = 2 * ORIGIN / (1 << z)
            for mx in range(x0, x1 + 1, metatile):
                for my in range(y0, y1 + 1, metatile):
                    nx, ny = min(metatile, x1 - mx + 1), min(metatile, y1 - my + 1)
                    rect = QgsRectangle(-ORIGIN + mx * size, ORIGIN - (my + ny) * size,
                                        -ORIGIN + (mx + nx) * size, ORIGIN - my * size)
                    yield z, mx, my, nx, ny, rect

    colour_blend = False
    done = 0
    rendering = deque()  # (job, z, mx, my, nx, ny), in start order
    cutting = deque()    # futures of cut(), in start order
    with TileSink(output) as sink, ThreadPoolExecutor(max_workers=threads,
                                                      thread_name_prefix="q2vt-raster") as pool:
        def write_ready(block: bool) -> None:
            nonlocal colour_blend, done
            while cutting and (block or cutting[0].done()):
                tiles, grey, count = cutting.popleft().result()
                for tile in tiles:
                    sink.add(*tile)
                colour_blend = colour_blend or not grey
                done += count
                progress.update(0.9 * done / max(1, plan.tiles),
                                f'Raster "{layer.name()}": {done}/{plan.tiles} tiles')

        def finish_oldest() -> None:
            job, z, mx, my, nx, ny = rendering.popleft()
            job.waitForFinished()
            cutting.append(pool.submit(cut, job.renderedImage(), z, mx, my, nx, ny))
            write_ready(len(cutting) > 2 * threads)

        try:
            for z, mx, my, nx, ny, rect in metatiles():
                progress.check()
                job_settings = QgsMapSettings(settings)
                job_settings.setExtent(rect)
                job_settings.setOutputSize(QSize(nx * tile_px, ny * tile_px))
                job = QgsMapRendererParallelJob(job_settings)
                job.start()
                rendering.append((job, z, mx, my, nx, ny))
                while len(rendering) >= threads:
                    finish_oldest()
            while rendering:
                finish_oldest()
            write_ready(True)
        finally:
            for job, *_ in rendering:  # cancelled or failed: stop the renders still running
                job.cancel()
        if colour_blend:
            plan.warnings.append(f'Raster layer "{layer.name()}": {blend} blend mode with colours is '
                                 "approximated in the web map (by brightness); grey layers such as a "
                                 "hillshade are exact.")
        if not sink.count:
            return None
        metadata = {"name": title or layer.name(), "format": fmt,
                    "type": "overlay", "description": "QGIS raster layer rendered by QWebMap"}
        return sink.write(IMAGE_TILE_TYPES[fmt], Compression.NONE, metadata,
                          progress=progress.sub(0.9, 1.0))


# QPainter composition modes (QgsMapLayer.blendMode) the browser can reproduce.
BLEND_NAMES = {0: "normal", 13: "multiply", 14: "screen", 15: "overlay", 16: "darken", 17: "lighten",
               18: "dodge", 19: "burn", 20: "hard light", 21: "soft light", 22: "difference",
               23: "exclusion", 12: "addition"}


def blend_name(layer) -> str:
    """The layer's blend mode name ("normal", "multiply", ...)."""
    try:
        mode = int(getattr(layer.blendMode(), "value", layer.blendMode()))
    except (AttributeError, TypeError, ValueError):
        return "normal"
    return BLEND_NAMES.get(mode, f"mode {mode}")


def blend_to_alpha(image: QImage, blend: str) -> Tuple[QImage, bool]:
    """A rendered multiply/screen layer as a normal (alpha) image with the
    same result: multiply by grey g = black with alpha 1 - g; screen by g =
    white with alpha g (both times the pixel's own alpha). Returns the image
    and whether every visible pixel was grey (else luminance: approximate)."""
    import numpy as np  # pylint: disable=import-outside-toplevel
    argb = image.convertToFormat(QImage.Format.Format_ARGB32)
    width, height = argb.width(), argb.height()
    ptr = argb.constBits()
    ptr.setsize(argb.sizeInBytes() if hasattr(argb, "sizeInBytes") else argb.byteCount())
    rows = np.frombuffer(ptr, dtype=np.uint8).reshape(height, argb.bytesPerLine())
    pixels = rows[:, :width * 4].reshape(height, width, 4).astype(np.float32)  # B G R A
    b, g, r, a = pixels[..., 0], pixels[..., 1], pixels[..., 2], pixels[..., 3]
    visible = a > 0
    grey = not visible.any() or float(np.max(np.maximum(np.abs(r - g), np.abs(g - b))[visible])) <= 2.0
    level = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    alpha = a * ((1.0 - level) if blend == "multiply" else level)
    out = np.empty((height, width, 4), dtype=np.uint8)
    out[..., :3] = 0 if blend == "multiply" else 255
    out[..., 3] = np.clip(np.rint(alpha), 0, 255).astype(np.uint8)
    result = QImage(out.tobytes(), width, height, width * 4, QImage.Format.Format_ARGB32).copy()
    return result, grey


def raster_source_id(logical_id: str) -> str:
    return f"q2vt_raster_{logical_id.replace('-', '_')}"


def raster_style_layer_id(logical_id: str) -> str:
    return f"q2vt-raster-{logical_id}"


# -- export cache ---------------------------------------------------------------
# Files next to a raster that change how GDAL / QGIS read or draw it.
_RASTER_SIDECARS = (".aux.xml", ".ovr", ".msk", ".tfw", ".tifw", ".wld", ".jgw", ".pgw", ".prj")


def _raster_files(layer) -> Optional[List[str]]:
    """The local files of a GDAL raster layer (with its sidecars), or None
    when it is not a plain local file (web, database, virtual sources)."""
    if layer.providerType() not in ("gdal", "ogr"):  # ogr: a vector layer drawn as images
        return None
    path = layer.source().split("|")[0]
    if not path or not os.path.isfile(path):
        return None
    files = [path]
    stem = os.path.splitext(path)[0]
    for side in _RASTER_SIDECARS:
        for candidate in (path + side, stem + side):
            if os.path.isfile(candidate):
                files.append(candidate)
    return sorted(set(files))


def raster_cache_key(project, layer, config: LayerConfig, plan: RasterPlan, blend: str) -> Optional[str]:
    """Content key of a rendered raster archive: the source files (size and
    modification time), the layer's whole QGIS style (renderer, resampling,
    brightness/contrast, opacity...), CRS and datum transformations, the
    tiles (extent, zooms) and the image settings; the plugin's raster code and
    QGIS/GDAL versions. None: not cacheable (online, database or virtual
    sources)."""
    from qgis.core import QgsMapLayerStyle  # pylint: disable=import-outside-toplevel
    from ..core import export_cache  # pylint: disable=import-outside-toplevel
    files = _raster_files(layer)
    if files is None:
        return None
    sources = []
    for path in files:
        stat = os.stat(path)
        sources.append([os.path.abspath(path), stat.st_size, stat.st_mtime_ns])
    style = QgsMapLayerStyle()
    style.readFromLayer(layer)
    here = os.path.dirname(os.path.abspath(__file__))
    code = []
    for name in ("raster_tiles.py", "pmtiles_builder.py"):
        with open(os.path.join(here, name), "rb") as handle:
            code.append(export_cache.hashlib.sha256(handle.read()).hexdigest())
    try:
        operations = sorted(project.transformContext().coordinateOperations().items())
    except AttributeError:
        operations = []
    return export_cache.make_key(
        "raster", code, sources, style.xmlData(), layer.crs().toWkt(), operations,
        [plan.min_zoom, plan.max_zoom, list(plan.extent_3857)],
        [tile_format(config.raster_format), int(config.raster_quality), bool(config.raster_hidpi)],
        config.title or layer.name(), blend)


def descriptor_to_dict(descriptor: ArchiveDescriptor) -> dict:
    data = dict(descriptor.__dict__)
    data.pop("path", None)
    data["zoom_counts"] = {str(k): v for k, v in descriptor.zoom_counts.items()}
    return data


def descriptor_from_dict(data: dict, path: str) -> ArchiveDescriptor:
    data = dict(data)
    for name in ("bounds", "center"):
        if name in data:
            data[name] = tuple(data[name])
    data["zoom_counts"] = {int(k): v for k, v in data.get("zoom_counts", {}).items()}
    return ArchiveDescriptor(path=path, **data)
