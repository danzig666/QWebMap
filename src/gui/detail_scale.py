"""
detail_scale.py

How close visitors can zoom, for the simple view: a QGIS map scale (what
planners think in; the same meaning whatever the map shows) instead of a
web zoom level, a recommendation made from the project itself, and a
preview of the project's own map at that scale.

Recommendation (``recommend``): the scale at which the published layers'
smallest typical features are clearly visible (their median size about
40 px), never less detail than a layer that only appears when zoomed in
needs (its scale range), and no more tiles than a web map of this kind
sensibly holds.
"""

import math
import statistics
from typing import List, Optional, Tuple

from qgis.core import (Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeatureRequest,
                       QgsMapLayer, QgsMapSettings, QgsRectangle, QgsUnitTypes)
from qgis.PyQt.QtCore import QCoreApplication, QSize

# (QGIS 3.36+: Qgis.FeatureRequestFlag; QGIS 3.34, the tests: QgsFeatureRequest.Flag.)
_NO_GEOMETRY = getattr(getattr(Qgis, "FeatureRequestFlag", None), "NoGeometry", None) \
    or QgsFeatureRequest.Flag.NoGeometry

# The scales offered (left: less detail), as on printed maps.
SCALES = (100000, 50000, 25000, 10000, 5000, 2000, 1000, 500)
FEATURE_PX = 40          # a typical feature's size on screen at the recommended scale
METRES_PER_PX = 0.0254 / 96.0
MAX_TILES = 300000       # more: a coarser scale (export time, archive size)
SAMPLE = 400             # features measured per layer


def tr(text: str) -> str:
    return QCoreApplication.translate("PublishDialog", text)


def nice(scale: float) -> str:
    """1:2 000 style (thin spaces)."""
    return "1:" + f"{round(scale):,}".replace(",", " ")


def _cos_lat(extent_3857: QgsRectangle) -> float:
    latitude = math.degrees(math.atan(math.sinh(extent_3857.center().y() / 6378137.0)))
    return max(0.05, math.cos(math.radians(latitude)))


def zoom_for_scale(factor: float, scale: float) -> int:
    """The closest tile zoom that shows at least the detail of ``scale``."""
    return max(0, min(22, int(math.ceil(math.log2(factor / scale) - 0.05))))


def scale_of_zoom(factor: float, zoom: int) -> float:
    return factor / 2.0 ** zoom


def nearest_index(scale: float) -> int:
    return min(range(len(SCALES)), key=lambda i: abs(math.log(SCALES[i] / scale)))


def _snap_finer(scale: float) -> float:
    """The offered scale with at least the detail of ``scale``."""
    finer = [s for s in SCALES if s <= scale * 1.15]
    return max(finer) if finer else SCALES[-1]


def _feature_size_m(layer, extent_3857: QgsRectangle, project, cos_lat: float) -> Optional[float]:
    """Median ground size (m) of the layer's features in the area: the larger
    side of a line's or polygon's box; the spacing of points."""
    mercator = QgsCoordinateReferenceSystem("EPSG:3857")
    try:
        to_layer = QgsCoordinateTransform(mercator, layer.crs(), project)
        to_web = QgsCoordinateTransform(layer.crs(), mercator, project)
        area = to_layer.transformBoundingBox(extent_3857)
    except Exception:  # noqa: BLE001 - not measurable
        return None
    geometry_type = layer.geometryType()
    if geometry_type == Qgis.GeometryType.Point:
        request = QgsFeatureRequest().setFilterRect(area).setNoAttributes() \
            .setFlags(_NO_GEOMETRY).setLimit(20000)
        count = sum(1 for _ in layer.getFeatures(request))
        if count < 2:
            return None
        ground = extent_3857.width() * extent_3857.height() * cos_lat * cos_lat
        return math.sqrt(ground / count)
    if geometry_type not in (Qgis.GeometryType.Line, Qgis.GeometryType.Polygon):
        return None
    request = QgsFeatureRequest().setFilterRect(area).setNoAttributes().setLimit(SAMPLE)
    sizes = []
    for feature in layer.getFeatures(request):
        geometry = feature.geometry()
        if geometry is None or geometry.isEmpty():
            continue
        try:
            box = to_web.transformBoundingBox(geometry.boundingBox())
        except Exception:  # noqa: BLE001
            continue
        sizes.append(max(box.width(), box.height()) * cos_lat)
    return statistics.median(sizes) if sizes else None


def recommend(project, layers: List[QgsMapLayer], extent_3857: Optional[QgsRectangle], factor: float,
              min_zoom: int) -> Tuple[float, List[str]]:
    """(scale, reasons in plain words) for these published layers and area."""
    reasons = []
    candidates = []
    cos_lat = 1.0
    if extent_3857 is not None and not extent_3857.isEmpty():
        latitude = math.degrees(math.atan(math.sinh(extent_3857.center().y() / 6378137.0)))
        cos_lat = max(0.05, math.cos(math.radians(latitude)))
    smallest = None
    for layer in layers:
        if layer is None or layer.type() != QgsMapLayer.LayerType.VectorLayer:
            continue
        if layer.hasScaleBasedVisibility() and layer.minimumScale() > 0:
            needed = layer.minimumScale() / 2.0  # shown over a couple of zooms at least
            candidates.append(needed)
            reasons.append(tr("“{}” appears from {} on").format(layer.name(), nice(layer.minimumScale())))
        if extent_3857 is None:
            continue
        size = _feature_size_m(layer, extent_3857, project, cos_lat)
        if size and size > 0 and (smallest is None or size < smallest[0]):
            smallest = (size, layer.name())
    if smallest is not None:
        candidates.append(smallest[0] / FEATURE_PX / METRES_PER_PX)
        reasons.insert(0, tr("the features of “{}” are about {} m across").format(
            smallest[1], f"{smallest[0]:.0f}" if smallest[0] >= 10 else f"{smallest[0]:.1f}"))
    scale = _snap_finer(min(candidates)) if candidates else 5000.0
    if extent_3857 is not None and not extent_3857.isEmpty():
        from ..publishing.raster_tiles import count_tiles  # pylint: disable=import-outside-toplevel
        box = [extent_3857.xMinimum(), extent_3857.yMinimum(), extent_3857.xMaximum(), extent_3857.yMaximum()]
        limited = False
        while scale < SCALES[0] and count_tiles(box, min_zoom, zoom_for_scale(factor, scale)) > MAX_TILES:
            scale = SCALES[max(0, SCALES.index(scale) - 1)] if scale in SCALES else SCALES[0]
            limited = True
        if limited:
            reasons.append(tr("less detail to keep a map of this large area quick to make"))
    return float(scale), reasons


def preview_centre(project, layers: List[QgsMapLayer], extent_3857: QgsRectangle, footprint_m: float):
    """Where the preview looks (EPSG:3857): where the published features are
    densest, on a grid of the preview's size (the middle of the area may be
    empty land at 1:1 000); nearer the middle on a tie."""
    from qgis.core import QgsPointXY  # pylint: disable=import-outside-toplevel
    mercator = QgsCoordinateReferenceSystem("EPSG:3857")
    middle = extent_3857.center()
    cell = max(1.0, footprint_m)
    cells = {}
    for layer in layers:
        if layer is None or layer.type() != QgsMapLayer.LayerType.VectorLayer:
            continue
        try:
            to_layer = QgsCoordinateTransform(mercator, layer.crs(), project)
            to_web = QgsCoordinateTransform(layer.crs(), mercator, project)
            request = QgsFeatureRequest().setFilterRect(to_layer.transformBoundingBox(extent_3857)) \
                .setNoAttributes().setLimit(3000)
            for feature in layer.getFeatures(request):
                geometry = feature.geometry()
                if geometry is None or geometry.isEmpty():
                    continue
                box = to_web.transformBoundingBox(geometry.boundingBox())
                if max(box.width(), box.height()) > 4 * cell:
                    continue  # (a large polygon or a long line tells nothing of where details are)
                point = box.center()
                key = (int((point.x() - middle.x()) // cell), int((point.y() - middle.y()) // cell))
                entry = cells.setdefault(key, [0, 0.0, 0.0])
                entry[0] += 1
                entry[1] += point.x()
                entry[2] += point.y()
        except Exception:  # noqa: BLE001 - this layer not measurable
            continue
    if not cells:
        return middle
    key, (count, sum_x, sum_y) = max(cells.items(),
                                     key=lambda kv: (kv[1][0], -(kv[0][0] ** 2 + kv[0][1] ** 2)))
    return QgsPointXY(sum_x / count, sum_y / count)


def preview_settings(project, layers: List[QgsMapLayer], extent_3857: QgsRectangle, scale: float,
                     size: QSize) -> Optional[QgsMapSettings]:
    """Map settings drawing ``layers`` at ``scale`` where the area has
    features (preview_centre), in the project's CRS (its scale as QGIS shows it)."""
    if extent_3857 is None or extent_3857.isEmpty() or not layers:
        return None
    crs = project.crs() if project.crs().isValid() else QgsCoordinateReferenceSystem("EPSG:3857")
    try:
        centre = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:3857"), crs,
                                        project).transform(preview_centre(
                                            project, layers, extent_3857,
                                            size.width() * scale * METRES_PER_PX / _cos_lat(extent_3857)))
    except Exception:  # noqa: BLE001
        return None
    metres = size.width() * scale * METRES_PER_PX
    if crs.isGeographic():
        latitude = centre.y()
        width = metres / (111320.0 * max(0.05, math.cos(math.radians(latitude))))
    else:
        width = metres * QgsUnitTypes.fromUnitToUnitFactor(Qgis.DistanceUnit.Meters, crs.mapUnits())
    height = width * size.height() / size.width()
    settings = QgsMapSettings()
    settings.setLayers(layers)
    settings.setDestinationCrs(crs)
    settings.setTransformContext(project.transformContext())
    settings.setOutputSize(size)
    settings.setOutputDpi(96)
    settings.setExtent(QgsRectangle(centre.x() - width / 2, centre.y() - height / 2,
                                    centre.x() + width / 2, centre.y() + height / 2))
    settings.setBackgroundColor(project.backgroundColor())
    return settings
