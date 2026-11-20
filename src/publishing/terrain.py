"""
Terrain for the web map's 3D view, hillshade and elevation profiles: a DEM
(a QGIS raster layer of heights in metres, band 1) resampled by GDAL to Web
Mercator tiles of 256 px and stored as "terrain-RGB" PNG images
(height = -10000 + (R * 65536 + G * 256 + B) * 0.1 m, MapLibre's
``raster-dem`` "mapbox" encoding) in their own PMTiles archive.

Each zoom is warped once over its whole tile-aligned area (bilinear) and cut
into tiles; holes and the area beyond the DEM take the nearest heights (GDAL
FillNodata), so the relief has no cliff at the DEM's edge; tiles without
any data are left out.
"""

import math
from typing import Optional, Tuple

from .errors import PublishingError
from .pmtiles_builder import ArchiveDescriptor, TileSink
from .progress import Progress
from .raster_tiles import ORIGIN, native_resolution, native_zoom, tile_span
from .vendor.pmtiles.tile import Compression, TileType

TILE = 256
MAX_PIXELS = 48_000_000      # one zoom's warped area (~190 MB as float32)
MAX_TERRAIN_ZOOM = 15
NODATA = -32768.0
# DEM pixels the pyramid may cover beyond the area (read once to build it):
# the low zooms' tiles reach past the area, and get real heights there
# instead of edge heights while that part of the DEM stays this small.
PYRAMID_PIXELS = 100_000_000


def encode_heights(heights) -> bytes:
    """RGB bytes (row-major, 3 per pixel) of a height array in metres."""
    import numpy as np  # pylint: disable=import-outside-toplevel
    value = np.clip(np.round((np.asarray(heights, dtype=np.float64) + 10000.0) * 10.0), 0, 2 ** 24 - 1)
    value = value.astype(np.uint32)
    rgb = np.stack([(value >> 16) & 255, (value >> 8) & 255, value & 255], axis=-1).astype(np.uint8)
    return rgb.tobytes()


def decode_rgb(r: int, g: int, b: int) -> float:
    return -10000.0 + (r * 65536 + g * 256 + b) * 0.1


def _png(rgb: bytes, width: int, height: int) -> bytes:
    from qgis.PyQt.QtGui import QImage  # pylint: disable=import-outside-toplevel
    from .raster_tiles import _encode  # pylint: disable=import-outside-toplevel
    image = QImage(rgb, width, height, width * 3, QImage.Format.Format_RGB888).copy()
    return _encode(image, "PNG", 100)


def terrain_zooms(layer, profile_min_zoom: int, latitude: float) -> Tuple[int, int]:
    """(min, max) zoom of the terrain tiles: down to two levels below the
    map's first zoom, up to the DEM's own resolution (at most 15)."""
    native = native_resolution(layer)
    high = native_zoom(native, latitude) if native else 14
    high = max(0, min(MAX_TERRAIN_ZOOM, high))
    low = max(0, min(high, int(profile_min_zoom) - 2))
    return low, high


def render_terrain(layer, extent_3857, min_zoom: int, max_zoom: int, output: str,
                   progress: Optional[Progress] = None) -> Optional[ArchiveDescriptor]:
    """Terrain-RGB PMTiles of ``layer`` over ``extent_3857`` (x0, y0, x1, y1).

    Each zoom is warped from the DEM (from a pyramid of it built once, so a
    zoomed-out level does not read the whole DEM). Holes and the area beyond
    the DEM take the nearest edge heights: filled (GDAL) at the lowest zoom,
    each higher zoom takes them from the one below, resampled (filling every
    zoom anew cost minutes at the highest one)."""
    from osgeo import gdal  # pylint: disable=import-outside-toplevel
    import numpy as np  # pylint: disable=import-outside-toplevel
    progress = progress or Progress()
    source = layer.source().split("|")[0]
    dataset = gdal.Open(source)
    if dataset is None:
        raise PublishingError("Q2VT_PUB_TERRAIN", f'Terrain: "{layer.name()}" cannot be read as a file '
                                                  "(online services cannot be used as terrain).")
    band = dataset.GetRasterBand(1)
    source_nodata = band.GetNoDataValue()
    has_overviews = band.GetOverviewCount() > 0
    dataset = None
    # The CRS QGIS uses for the layer (a file without one, or one set in QGIS).
    source_srs = layer.crs().toWkt() if layer.crs().isValid() else None
    zooms = list(range(int(min_zoom), int(max_zoom) + 1))
    # Only the DEM's part around the area: a pyramid of a whole national DEM
    # read every pixel of it (hours, gigabytes) for a town's terrain.
    footprints = [_bounds(z, *span) for z, span in ((z, tile_span(extent_3857, z)) for z in zooms)
                  if span[2] >= span[0] and span[3] >= span[1]]
    pyramid = None if has_overviews else _pyramid(source, output + ".dem.vrt", extent_3857, source_srs,
                                                  progress, wider=footprints)
    below = None  # the zoom below, filled: (MEM dataset)
    try:
        with TileSink(output) as sink:
            for step, z in enumerate(zooms):
                progress.check()
                x0, y0, x1, y1 = tile_span(extent_3857, z)
                nx, ny = x1 - x0 + 1, y1 - y0 + 1
                if nx <= 0 or ny <= 0:
                    continue
                if nx * ny * TILE * TILE > MAX_PIXELS:
                    progress.info(f"Terrain: zoom {z} and above left out (area too large)")
                    break
                bounds = _bounds(z, x0, y0, x1, y1)
                options = gdal.WarpOptions(format="MEM", outputBounds=bounds, width=nx * TILE,
                                           height=ny * TILE, dstSRS="EPSG:3857", resampleAlg="bilinear",
                                           outputType=gdal.GDT_Float32, dstNodata=NODATA,
                                           srcNodata=source_nodata, srcSRS=source_srs, multithread=True)
                warped = gdal.Warp("", pyramid or source, options=options)
                if warped is None:
                    raise PublishingError("Q2VT_PUB_TERRAIN",
                                          f'Terrain: "{layer.name()}" could not be resampled.')
                band = warped.GetRasterBand(1)
                heights = band.ReadAsArray().astype(np.float64)
                valid = np.isfinite(heights) & (heights > NODATA + 1)
                if not valid.any():
                    continue
                if valid.all():
                    pass
                elif below is None:
                    # The lowest zoom with heights: small; filled from the edges.
                    gdal.FillNodata(targetBand=band, maskBand=None, maxSearchDist=max(nx, ny) * TILE,
                                    smoothingIterations=0)
                    heights = band.ReadAsArray().astype(np.float64)
                else:
                    filler = gdal.Warp("", below, options=gdal.WarpOptions(
                        format="MEM", outputBounds=bounds, width=nx * TILE, height=ny * TILE,
                        resampleAlg="bilinear", outputType=gdal.GDT_Float32))
                    fill = filler.GetRasterBand(1).ReadAsArray().astype(np.float64)
                    filler = None
                    heights[~valid] = fill[~valid]
                    band.WriteArray(heights.astype(np.float32))
                filled = np.isfinite(heights) & (heights > NODATA + 1)
                if not filled.all():
                    heights[~filled] = float(heights[filled].mean())
                    band.WriteArray(heights.astype(np.float32))
                band.SetNoDataValue(-1e38)  # filled: every value is a height for the zoom above
                below = warped
                for ty in range(ny):
                    for tx in range(nx):
                        window = (slice(ty * TILE, (ty + 1) * TILE), slice(tx * TILE, (tx + 1) * TILE))
                        if not valid[window].any():
                            continue
                        sink.add(z, x0 + tx, y0 + ty, _png(encode_heights(heights[window]), TILE, TILE))
                progress.update(0.9 * (step + 1) / len(zooms), f"Terrain: zoom {z}, {sink.count} tiles")
            below = None
            if not sink.count:
                return None
            metadata = {"name": layer.name(), "format": "png", "type": "baselayer",
                        "description": "Terrain-RGB heights (mapbox encoding) by QWebMap", "encoding": "mapbox"}
            return sink.write(TileType.PNG, Compression.NONE, metadata, progress=progress.sub(0.9, 1.0))
    finally:
        below = None
        if pyramid is not None:
            import os  # pylint: disable=import-outside-toplevel
            for path in (pyramid, pyramid + ".ovr"):
                try:
                    os.remove(path)
                except OSError:
                    pass


def _bounds(z: int, x0: int, y0: int, x1: int, y1: int):
    """3857 bounds of the tile range x0..x1, y0..y1 of zoom ``z``."""
    size = 2 * ORIGIN / (1 << z)
    return (-ORIGIN + x0 * size, ORIGIN - (y1 + 1) * size, -ORIGIN + (x1 + 1) * size, ORIGIN - y0 * size)


def _window(dataset, extent_3857, source_srs: Optional[str]):
    """The pixel window [x, y, width, height] of ``dataset`` around the 3857
    extent (two pixels more on every side for bilinear), or None (unknown
    CRS, rotated grid: the whole DEM)."""
    from osgeo import osr  # pylint: disable=import-outside-toplevel
    gt = dataset.GetGeoTransform(can_return_null=True)
    wkt = source_srs or dataset.GetProjection()
    if gt is None or gt[2] or gt[4] or not gt[1] or not gt[5] or not wkt:
        return None
    web, src = osr.SpatialReference(), osr.SpatialReference()
    web.ImportFromEPSG(3857)
    if src.SetFromUserInput(wkt) != 0:
        return None
    for srs in (web, src):
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    x0, y0, x1, y1 = osr.CoordinateTransformation(web, src).TransformBounds(*extent_3857, 21)
    cols = sorted(((x0 - gt[0]) / gt[1], (x1 - gt[0]) / gt[1]))
    rows = sorted(((y0 - gt[3]) / gt[5], (y1 - gt[3]) / gt[5]))
    left = max(0, int(math.floor(cols[0])) - 2)
    top = max(0, int(math.floor(rows[0])) - 2)
    right = min(dataset.RasterXSize, int(math.ceil(cols[1])) + 2)
    bottom = min(dataset.RasterYSize, int(math.ceil(rows[1])) + 2)
    return [left, top, max(0, right - left), max(0, bottom - top)]


def _pyramid(source: str, path: str, extent_3857=None, source_srs: Optional[str] = None,
             progress: Optional[Progress] = None, wider=()) -> Optional[str]:
    """A VRT of ``source`` (its part around ``extent_3857``, or around the
    first extent of ``wider`` whose part has at most PYRAMID_PIXELS) with
    averaged overviews (heights, nodata left out) at ``path``, or None (then
    the DEM itself is read). Cancel stops building the overviews."""
    import os  # pylint: disable=import-outside-toplevel
    from osgeo import gdal  # pylint: disable=import-outside-toplevel
    from .errors import Cancelled  # pylint: disable=import-outside-toplevel
    progress = progress or Progress()
    vrt = None
    try:
        dataset = gdal.Open(source)
        window = None
        if dataset is not None and extent_3857 is not None:
            try:
                window = _window(dataset, extent_3857, source_srs)
            except (RuntimeError, AttributeError, TypeError, ValueError):  # no transformation: the whole DEM
                window = None
            for extent in wider if window is not None and window[2] and window[3] else ():
                try:
                    bigger = _window(dataset, extent, source_srs)
                except (RuntimeError, AttributeError, TypeError, ValueError):  # beyond the CRS's area
                    continue
                if bigger is None or not bigger[2] or not bigger[3]:
                    continue
                # Always holding the area (a far extent may transform oddly).
                left, top = min(window[0], bigger[0]), min(window[1], bigger[1])
                right = max(window[0] + window[2], bigger[0] + bigger[2])
                bottom = max(window[1] + window[3], bigger[1] + bigger[3])
                if (right - left) * (bottom - top) <= PYRAMID_PIXELS:
                    window = [left, top, right - left, bottom - top]
                    break
        whole = window is None or window == [0, 0, dataset.RasterXSize, dataset.RasterYSize]
        dataset = None
        if window is not None and (not window[2] or not window[3]):
            return None  # the DEM is outside the area
        if whole:
            vrt = gdal.BuildVRT(path, [source])
        else:
            vrt = gdal.Translate(path, source, format="VRT", srcWin=window)
        if vrt is None:
            return None
        width, height = vrt.RasterXSize, vrt.RasterYSize
        levels, factor = [], 2
        while max(width, height) / factor >= 256:
            levels.append(factor)
            factor *= 2
        if not levels:
            vrt = None
            # The part of the DEM is small: read it (not the whole DEM) as is.
            return None if whole else path
        gdal.SetConfigOption("COMPRESS_OVERVIEW", "ZSTD")
        try:
            done = vrt.BuildOverviews("AVERAGE", levels, callback=lambda *_: 0 if progress.canceled() else 1)
        finally:
            gdal.SetConfigOption("COMPRESS_OVERVIEW", None)
        vrt = None
        progress.check()
        if done not in (None, 0):  # GDAL without exceptions: an error code
            raise RuntimeError("overviews failed")
        return path
    except (RuntimeError, Cancelled):  # GDAL (exceptions on): the DEM itself is read
        pass
    # Removed here: inside ``except`` the traceback still holds the open VRT.
    vrt = None
    for name in (path, path + ".ovr"):
        try:
            os.remove(name)
        except OSError:
            pass
    if progress.canceled():
        raise Cancelled()
    return None


def grow(extent_3857, fraction: float = 0.2):
    """The extent grown by ``fraction`` of its size on every side (the 3D
    view looks beyond the extent towards the horizon)."""
    x0, y0, x1, y1 = extent_3857
    dx, dy = (x1 - x0) * fraction, (y1 - y0) * fraction
    return (max(-ORIGIN, x0 - dx), max(-ORIGIN, y0 - dy), min(ORIGIN, x1 + dx), min(ORIGIN, y1 + dy))


def latitude_of(extent_3857) -> float:
    y = (extent_3857[1] + extent_3857[3]) / 2
    return math.degrees(2 * math.atan(math.exp(y / 6378137.0)) - math.pi / 2)
