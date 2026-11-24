"""
detail_scale.py

How close visitors can zoom, for the simple view: a QGIS map scale (what
planners think in; the same meaning whatever the map shows) instead of a
web zoom level, a recommendation made from the project itself, and a
preview of the project's own map at that scale.

Measuring reads the layers through feature sources made on the main
thread (``snapshot``), so it can run in a background task (``MeasureTask``):
a large project does not freeze the window while it is measured.

Recommendation (``recommend``): the scale at which the published layers'
smallest typical features are clearly visible (their median size about
40 px), never less detail than a layer that only appears when zoomed in
needs (its scale range), and no more tiles than a web map of this kind
sensibly holds.
"""

import math
import statistics
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from qgis.core import (Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeatureRequest,
                       QgsFeedback, QgsMapLayer, QgsMapSettings, QgsPointXY, QgsRectangle, QgsTask,
                       QgsUnitTypes, QgsVectorLayerFeatureSource)
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


@dataclass
class LayerInput:
    """What the measuring reads of a vector layer, safe to use in another
    thread (a feature source is a copy of the layer's data access)."""
    name: str
    crs: Any
    geometry_type: Any
    source: Any
    min_scale: float


def snapshot(layers: List[QgsMapLayer]) -> List[LayerInput]:
    """(Main thread.) The vector layers of ``layers`` for measuring."""
    out = []
    for layer in layers:
        if layer is None or layer.type() != QgsMapLayer.LayerType.VectorLayer or not layer.isSpatial():
            continue
        min_scale = layer.minimumScale() if layer.hasScaleBasedVisibility() and layer.minimumScale() > 0 else 0.0
        out.append(LayerInput(layer.name(), layer.crs(), layer.geometryType(),
                              QgsVectorLayerFeatureSource(layer), float(min_scale)))
    return out


def _request(feedback: Optional[QgsFeedback]) -> QgsFeatureRequest:
    request = QgsFeatureRequest()
    if feedback is not None and hasattr(request, "setFeedback"):
        request.setFeedback(feedback)
    return request


def _canceled(feedback: Optional[QgsFeedback]) -> bool:
    return feedback is not None and feedback.isCanceled()


def _feature_size_m(layer: LayerInput, extent_3857: QgsRectangle, context, cos_lat: float,
                    feedback: Optional[QgsFeedback] = None) -> Optional[float]:
    """Median ground size (m) of the layer's features in the area: the larger
    side of a line's or polygon's box; the spacing of points."""
    mercator = QgsCoordinateReferenceSystem("EPSG:3857")
    try:
        to_layer = QgsCoordinateTransform(mercator, layer.crs, context)
        to_web = QgsCoordinateTransform(layer.crs, mercator, context)
        area = to_layer.transformBoundingBox(extent_3857)
    except Exception:  # noqa: BLE001 - not measurable
        return None
    if layer.geometry_type == Qgis.GeometryType.Point:
        request = _request(feedback).setFilterRect(area).setNoAttributes() \
            .setFlags(_NO_GEOMETRY).setLimit(20000)
        count = 0
        for _ in layer.source.getFeatures(request):
            count += 1
            if count % 500 == 0 and _canceled(feedback):
                return None
        if count < 2:
            return None
        ground = extent_3857.width() * extent_3857.height() * cos_lat * cos_lat
        return math.sqrt(ground / count)
    if layer.geometry_type not in (Qgis.GeometryType.Line, Qgis.GeometryType.Polygon):
        return None
    request = _request(feedback).setFilterRect(area).setNoAttributes().setLimit(SAMPLE)
    sizes = []
    for feature in layer.source.getFeatures(request):
        if _canceled(feedback):
            return None
        geometry = feature.geometry()
        if geometry is None or geometry.isEmpty():
            continue
        try:
            box = to_web.transformBoundingBox(geometry.boundingBox())
        except Exception:  # noqa: BLE001
            continue
        sizes.append(max(box.width(), box.height()) * cos_lat)
    return statistics.median(sizes) if sizes else None


def recommend_inputs(layers: List[LayerInput], extent_3857: Optional[QgsRectangle], factor: float,
                     min_zoom: int, context, feedback: Optional[QgsFeedback] = None) -> Tuple[float, List[str]]:
    """(scale, reasons in plain words) for these measured layers and area
    (any thread)."""
    reasons = []
    candidates = []
    cos_lat = 1.0
    if extent_3857 is not None and not extent_3857.isEmpty():
        cos_lat = _cos_lat(extent_3857)
    smallest = None
    for layer in layers:
        if _canceled(feedback):
            break
        if layer.min_scale > 0:
            candidates.append(layer.min_scale / 2.0)  # shown over a couple of zooms at least
            reasons.append(tr("“{}” appears from {} on").format(layer.name, nice(layer.min_scale)))
        if extent_3857 is None:
            continue
        size = _feature_size_m(layer, extent_3857, context, cos_lat, feedback)
        if size and size > 0 and (smallest is None or size < smallest[0]):
            smallest = (size, layer.name)
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


def recommend(project, layers: List[QgsMapLayer], extent_3857: Optional[QgsRectangle], factor: float,
              min_zoom: int) -> Tuple[float, List[str]]:
    """(scale, reasons in plain words) for these published layers and area."""
    return recommend_inputs(snapshot(layers), extent_3857, factor, min_zoom, project.transformContext())


def centre_inputs(layers: List[LayerInput], extent_3857: QgsRectangle, footprint_m: float, context,
                  feedback: Optional[QgsFeedback] = None) -> QgsPointXY:
    """Where the preview looks (EPSG:3857): where the published features are
    densest, on a grid of the preview's size (the middle of the area may be
    empty land at 1:1 000); nearer the middle on a tie (any thread)."""
    mercator = QgsCoordinateReferenceSystem("EPSG:3857")
    middle = extent_3857.center()
    cell = max(1.0, footprint_m)
    cells = {}
    for layer in layers:
        if _canceled(feedback):
            break
        try:
            to_layer = QgsCoordinateTransform(mercator, layer.crs, context)
            to_web = QgsCoordinateTransform(layer.crs, mercator, context)
            request = _request(feedback).setFilterRect(to_layer.transformBoundingBox(extent_3857)) \
                .setNoAttributes().setLimit(3000)
            for feature in layer.source.getFeatures(request):
                if _canceled(feedback):
                    break
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
        return QgsPointXY(middle)
    key, (count, sum_x, sum_y) = max(cells.items(),
                                     key=lambda kv: (kv[1][0], -(kv[0][0] ** 2 + kv[0][1] ** 2)))
    return QgsPointXY(sum_x / count, sum_y / count)


def footprint_m(extent_3857: QgsRectangle, scale: float, size: QSize) -> float:
    """The preview's width on the ground in Web Mercator metres."""
    return size.width() * scale * METRES_PER_PX / _cos_lat(extent_3857)


def preview_centre(project, layers: List[QgsMapLayer], extent_3857: QgsRectangle, footprint: float):
    return centre_inputs(snapshot(layers), extent_3857, footprint, project.transformContext())


class MeasureTask(QgsTask):
    """In the background: the automatic scale (``auto``) and where the
    preview looks. ``on_done(task)`` is called on the main thread."""

    def __init__(self, layers: List[LayerInput], extent_3857: QgsRectangle, factor: float, min_zoom: int,
                 context, auto: bool, scale: float, size: QSize, on_done):
        flags = QgsTask.Flag.CanCancel
        hidden = getattr(QgsTask.Flag, "Hidden", None)  # (QGIS 3.26+: not listed in the status bar)
        if hidden is not None:
            flags |= hidden
        super().__init__(tr("Measuring the layers for the web map preview"), flags)
        self.layers, self.extent, self.factor, self.min_zoom = layers, extent_3857, factor, min_zoom
        self.context, self.auto, self.scale, self.size = context, auto, scale, size
        self.feedback = QgsFeedback()
        self.on_done = on_done
        self.recommended: Optional[float] = None
        self.reasons: List[str] = []
        self.centre: Optional[QgsPointXY] = None
        self.ended = False

    def run(self) -> bool:  # (a worker thread)
        try:
            scale = self.scale
            if self.auto:
                self.recommended, self.reasons = recommend_inputs(
                    self.layers, self.extent, self.factor, self.min_zoom, self.context, self.feedback)
                scale = scale_of_zoom(self.factor, zoom_for_scale(self.factor, self.recommended))
            if not self.isCanceled():
                self.centre = centre_inputs(self.layers, self.extent, footprint_m(self.extent, scale, self.size),
                                            self.context, self.feedback)
        except Exception:  # noqa: BLE001 - no preview, never a broken window
            return False
        return not self.isCanceled()

    def cancel(self):
        self.feedback.cancel()
        super().cancel()

    def finished(self, result: bool):  # (the main thread)
        self.ended = True
        self.layers = []  # (the feature sources go with the task)
        self.on_done(self, result)


def preview_settings(project, layers: List[QgsMapLayer], extent_3857: QgsRectangle, scale: float,
                     size: QSize, centre_3857: Optional[QgsPointXY] = None) -> Optional[QgsMapSettings]:
    """Map settings drawing ``layers`` at ``scale`` at ``centre_3857`` (by
    default where the area has features: preview_centre), in the project's
    CRS (its scale as QGIS shows it)."""
    if extent_3857 is None or extent_3857.isEmpty() or not layers:
        return None
    crs = project.crs() if project.crs().isValid() else QgsCoordinateReferenceSystem("EPSG:3857")
    if centre_3857 is None:
        centre_3857 = preview_centre(project, layers, extent_3857, footprint_m(extent_3857, scale, size))
    try:
        centre = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:3857"), crs,
                                        project).transform(centre_3857)
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
