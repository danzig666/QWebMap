"""QGIS 4 marker / hash line extras render like QGIS: trim distance at start
/ end (4.2), data-defined blank segments (4.0) and extra items (4.2).

Each test renders the original layer with QGIS and the exported dataset(s)
with the converted symbol(s), also with QGIS, and compares inked pixels.
Skipped where the QGIS API is missing.
"""

import math

import pytest
from qgis.core import (Qgis, QgsFeature, QgsField, QgsFillSymbol, QgsGeometry,
                       QgsHashedLineSymbolLayer, QgsLineSymbol, QgsLineSymbolLayer,
                       QgsMarkerLineSymbolLayer,
                       QgsMarkerSymbol, QgsProcessingFeedback, QgsProperty, QgsRectangle,
                       QgsSimpleMarkerSymbolLayer, QgsSingleSymbolRenderer, QgsSymbolLayer,
                       QgsVectorLayer)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor

from q2vt_fixtures import reset_project, to_geopackage
from q2vt_render import ink_mask, mask_difference, render

EXTENT = QgsRectangle(-120, -120, 120, 120)
TRIM = hasattr(QgsMarkerLineSymbolLayer, "setTrimDistanceStart")
BLANKS = getattr(QgsSymbolLayer.Property, "BlankSegments", None)
EXTRA = getattr(QgsSymbolLayer.Property, "ExtraItems", None)
needs_trim = pytest.mark.skipif(not TRIM, reason="marker-line trims need QGIS 4.2")
needs_blanks = pytest.mark.skipif(BLANKS is None, reason="blank segments need QGIS 4.0")
needs_extra = pytest.mark.skipif(EXTRA is None, reason="extra items need QGIS 4.2")

LINES = ["LINESTRING(-100 -80, -20 -80, -20 40, 90 90)", "LINESTRING(80 -100, 30 -30)"]
MULTI = ["MULTILINESTRING((-100 -80, -20 -80, -20 40, 90 90),(80 -100, 30 -30))"]
P = Qgis.MarkerLinePlacement


def _layer(kind, wkts, path, labels=None):
    layer = QgsVectorLayer(f"{kind}?crs=EPSG:3857", "src", "memory")
    layer.dataProvider().addAttributes([QgsField("id", QVariant.Int),
                                        QgsField("label", QVariant.String)])
    layer.updateFields()
    feats = []
    for i, wkt in enumerate(wkts):
        f = QgsFeature(layer.fields())
        f.setAttributes([i, labels[i] if labels else None])
        f.setGeometry(QgsGeometry.fromWkt(wkt))
        feats.append(f)
    layer.dataProvider().addFeatures(feats)
    return to_geopackage(layer, path)


def _export(layer, tmp_path):
    from q2vt_plugin.src.core.rules_flattener import RulesFlattener
    from q2vt_plugin.src.core.rules_exporter import RulesExporter
    from fidelity.diagnostics import DiagnosticCollector
    reset_project(layer)
    diags = DiagnosticCollector()
    rules = RulesFlattener(0, 22, str(tmp_path), QgsProcessingFeedback(), diags).flatten_all_rules()
    utils = tmp_path / "utils"
    utils.mkdir()
    layers, rules = RulesExporter(rules, EXTENT, 0, 22, str(utils), 0, QgsProcessingFeedback(),
                                  diagnostics=diags).export()
    by_name = {l.name(): l for l in layers}
    rendered = []
    for rule in rules:
        out = by_name[rule.output_dataset]
        out.setRenderer(QgsSingleSymbolRenderer(rule.rule.symbol().clone()))
        rendered.append(out)
    return rendered, rules, diags


def _marker(shape=Qgis.MarkerShape.ArrowHeadFilled, size=12):
    m = QgsSimpleMarkerSymbolLayer(shape, size)
    m.setSizeUnit(Qgis.RenderUnit.Pixels)
    m.setColor(QColor("black"))
    m.setStrokeColor(QColor("black"))
    return QgsMarkerSymbol([m])


def _markers(placements, interval=17.0, average=0.0):
    ml = QgsMarkerLineSymbolLayer(True, interval)
    ml.setIntervalUnit(Qgis.RenderUnit.MapUnits)
    ml.setPlacements(placements)
    ml.setSubSymbol(_marker(size=9))
    ml.setAverageAngleLength(average)  # (4 mm by default)
    ml.setAverageAngleUnit(Qgis.RenderUnit.MapUnits)
    return ml


def _drawn_at(outputs, rules, size=(300, 300)):
    """The outputs of the rules the web map draws at the render's scale."""
    from fidelity.zoom import scale_to_zoom
    zoom = scale_to_zoom(EXTENT.width() / size[0] / 0.0254 * 96)
    return [o for o, r in zip(outputs, rules) if r.visibility is None or (
        r.visibility.min_zoom <= zoom
        and (r.visibility.max_zoom is None or zoom < r.visibility.max_zoom))]


def _plain(symbol):
    """``symbol`` without trims, blank segments and extra items."""
    plain = symbol.clone()
    for sl in plain.symbolLayers():
        if TRIM:
            sl.setTrimDistanceStart(0)
            sl.setTrimDistanceEnd(0)
        for key in (QgsSymbolLayer.Property.PropertyTrimStart,
                    QgsSymbolLayer.Property.PropertyTrimEnd, BLANKS, EXTRA):
            if key is not None:
                sl.setDataDefinedProperty(key, QgsProperty())
    return plain


def _compare(layer, symbol, tmp_path, limit=0.06, size=(300, 300), changed=True):
    """Exported like QGIS draws it; ``changed``: QGIS draws it otherwise
    without the extras (the test exercises them)."""
    layer.setRenderer(QgsSingleSymbolRenderer(_plain(symbol)))
    plain = ink_mask(render([layer], EXTENT, size))
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    reference = ink_mask(render([layer], EXTENT, size))
    assert reference
    assert (mask_difference(reference, plain) > 0.05) == changed
    outputs, rules, diags = _export(layer, tmp_path)
    drawn = _drawn_at(outputs, rules, size)
    ours = ink_mask(render(drawn, EXTENT, size)) if drawn else set()
    assert mask_difference(reference, ours) < limit
    return rules, diags


ALL_PLACEMENTS = [P.Interval, P.Vertex, P.FirstVertex, P.LastVertex, P.InnerVertices,
                  P.CentralPoint, P.SegmentCenter]


@needs_trim
@pytest.mark.parametrize("placements", ALL_PLACEMENTS)
@pytest.mark.parametrize("unit", ["map", "percent"])
def test_trimmed_marker_lines_match_qgis(plugin, tmp_path, placements, unit):
    """QGIS trims every part before placing anything on it (trimPoints):
    markers (offset, interval and first / last vertex on the trimmed
    line) are placed on what is left."""
    layer = _layer("LineString", MULTI, str(tmp_path / "t.gpkg"))
    ml = _markers(placements)
    if placements == P.FirstVertex:
        ml.setOffset(6)  # screen offset is exact at the line's start
        ml.setOffsetUnit(Qgis.RenderUnit.Pixels)
    elif placements != P.LastVertex:
        ml.setOffset(4)  # QGIS offsets the (trimmed) line first
        ml.setOffsetUnit(Qgis.RenderUnit.MapUnits)
    ml.setOffsetAlongLine(6)
    ml.setOffsetAlongLineUnit(Qgis.RenderUnit.MapUnits)
    inner = placements == P.InnerVertices  # trimmed past the first inner vertex
    ml.setTrimDistanceStart((90 if inner else 30) if unit == "map" else (30 if inner else 12))
    ml.setTrimDistanceEnd(25 if unit == "map" else 20)
    trim_unit = Qgis.RenderUnit.MapUnits if unit == "map" else Qgis.RenderUnit.Percentage
    ml.setTrimDistanceStartUnit(trim_unit)
    ml.setTrimDistanceEndUnit(trim_unit)
    rules, diags = _compare(layer, QgsLineSymbol([ml]), tmp_path)
    assert any(r.recipe is not None and r.recipe.param("trim") for r in rules)
    assert not diags.by_code("Q2VT_DDP_NO_EMITTER")


@needs_trim
def test_data_defined_trim_of_a_hash_line_matches_qgis(plugin, tmp_path):
    layer = _layer("LineString", LINES, str(tmp_path / "h.gpkg"))
    hashes = QgsHashedLineSymbolLayer(True, 8)
    hashes.setIntervalUnit(Qgis.RenderUnit.MapUnits)
    hashes.setHashLength(10)
    hashes.setHashLengthUnit(Qgis.RenderUnit.Pixels)
    hashes.setSubSymbol(QgsLineSymbol.createSimple({"color": "black", "width": "0.5"}))
    hashes.setTrimDistanceStart(5)
    hashes.setTrimDistanceStartUnit(Qgis.RenderUnit.MapUnits)
    hashes.setTrimDistanceEndUnit(Qgis.RenderUnit.MapUnits)
    hashes.setDataDefinedProperty(QgsSymbolLayer.Property.PropertyTrimStart,
                                  QgsProperty.fromExpression('if("id" = 0, 45, NULL)'))
    hashes.setDataDefinedProperty(QgsSymbolLayer.Property.PropertyTrimEnd,
                                  QgsProperty.fromExpression('10 + 20 * "id"'))
    _, diags = _compare(layer, QgsLineSymbol([hashes]), tmp_path)
    assert not diags.by_code("Q2VT_DDP_NO_EMITTER")


@needs_trim
@pytest.mark.parametrize("placements", [P.Interval, P.FirstVertex, P.Vertex])
def test_screen_unit_trims_are_converted_per_zoom(plugin, tmp_path, placements):
    """A trim in millimetres covers half as much line at every zoom in: the
    recipes of a quarter of a zoom trim by its middle's length; the band
    drawn at the render's scale matches QGIS."""
    from fidelity.zoom import scale_to_zoom
    layer = _layer("LineString", LINES, str(tmp_path / "s.gpkg"))
    ml = _markers(placements)
    ml.setTrimDistanceStart(6)
    ml.setTrimDistanceEnd(4)
    ml.setTrimDistanceStartUnit(Qgis.RenderUnit.Millimeters)
    ml.setTrimDistanceEndUnit(Qgis.RenderUnit.Millimeters)
    layer.setRenderer(QgsSingleSymbolRenderer(QgsLineSymbol([ml])))
    reference = ink_mask(render([layer], EXTENT))
    outputs, rules, _ = _export(layer, tmp_path)
    trimmed = [(o, r) for o, r in zip(outputs, rules)
               if r.recipe is not None and r.recipe.param("trim")]
    assert len({r.get_attr("o") for _, r in trimmed}) > 5
    # 240 map units over 300 px at 96 dpi
    zoom = scale_to_zoom(240 / 300 / 0.0254 * 96)
    band = [(o, r) for o, r in trimmed if r.visibility.min_zoom <= zoom
            and (r.visibility.max_zoom is None or zoom < r.visibility.max_zoom)]
    assert band
    ours = ink_mask(render([o for o, _ in band], EXTENT))
    assert mask_difference(reference, ours) < 0.08


# Parts 320.4 and 86 long. Segment centres of the first, as QGIS measures
# them (from the segment's end vertex): 120, 260, 380.6 (along it: 40, 140,
# 260.2); the interval marker 2 before its start: 2.
BLANK_LINES = "(((0 3, 60 80, 115 125, 300 330)),((30 50)))"


@needs_blanks
@pytest.mark.parametrize("placements", ALL_PLACEMENTS)
def test_blank_segments_match_qgis(plugin, tmp_path, placements):
    """Items whose distance along their part falls inside a blank segment
    are not drawn (BlankSegmentsWalker, both bounds inclusive; a segment
    centre measured from its end vertex, a marker before the start by how
    far before it), whatever the placement."""
    layer = _layer("LineString", MULTI, str(tmp_path / "b.gpkg"))
    ml = _markers(placements, interval=9)
    ml.setOffsetAlongLine(-2)
    ml.setOffsetAlongLineUnit(Qgis.RenderUnit.MapUnits)
    ml.setDataDefinedProperty(BLANKS, QgsProperty.fromValue(BLANK_LINES))
    rules, diags = _compare(layer, QgsLineSymbol([ml]), tmp_path)
    assert any(r.recipe is not None and r.recipe.param("blank") for r in rules)
    assert not diags.by_code("Q2VT_DDP_NO_EMITTER")


@needs_blanks
def test_blank_segments_of_end_markers_moved_along_the_line(plugin, tmp_path):
    """renderOffsetVertexAlongLine measures a marker from the vertex before
    the segment it lands on: walking back 30 from the first part's end,
    258 (straight from its second vertex), not 290.4; on the one segment of
    the second part never blanked."""
    layer = _layer("LineString", MULTI, str(tmp_path / "ba.gpkg"))
    ml = _markers(P.FirstVertex | P.LastVertex)
    ml.setOffsetAlongLine(30)
    ml.setOffsetAlongLineUnit(Qgis.RenderUnit.MapUnits)
    ml.setDataDefinedProperty(BLANKS, QgsProperty.fromValue("(((25 35, 250 265)),((50 60)))"))
    _compare(layer, QgsLineSymbol([ml]), tmp_path)


@needs_blanks
def test_blank_segments_read_from_a_field_with_trim_offset_and_averaging(plugin, tmp_path):
    """Blank segments are measured along the trimmed, offset line, per
    feature (a field), with the angle averaged."""
    layer = _layer("LineString", LINES, str(tmp_path / "f.gpkg"),
                   labels=["((0 20, 50 90))", "((12 30))"])
    ml = _markers(P.Interval | P.Vertex, interval=8, average=10)
    ml.setOffset(-5)
    ml.setOffsetUnit(Qgis.RenderUnit.MapUnits)
    if TRIM:
        ml.setTrimDistanceStart(15)
        ml.setTrimDistanceStartUnit(Qgis.RenderUnit.MapUnits)
    ml.setDataDefinedProperty(BLANKS, QgsProperty.fromField("label"))
    _compare(layer, QgsLineSymbol([ml]), tmp_path)


@needs_blanks
@pytest.mark.parametrize("ring_filter", [0, 2])
def test_blank_segments_of_polygon_rings_match_qgis(plugin, tmp_path, ring_filter):
    layer = _layer("Polygon", ["POLYGON((-97 -83, 53 -83, 53 71, -97 71, -97 -83),"
                               "(-40 -40, 10 -40, 10 10, -40 10, -40 -40))"],
                   str(tmp_path / "p.gpkg"))
    ml = _markers(P.Interval | P.Vertex, interval=11)
    ml.setRingFilter(QgsLineSymbolLayer.RenderRingFilter(ring_filter))
    ml.setDataDefinedProperty(BLANKS, QgsProperty.fromValue("(((20 140, 300 400),(30 90)))"))
    _compare(layer, QgsFillSymbol([ml]), tmp_path)


@needs_blanks
def test_blank_segments_in_millimetres_are_converted_per_zoom(plugin, tmp_path):
    from fidelity.zoom import scale_to_zoom
    layer = _layer("LineString", LINES, str(tmp_path / "bm.gpkg"))
    ml = _markers(P.Interval, interval=6)
    ml.setBlankSegmentsUnit(Qgis.RenderUnit.Millimeters)
    ml.setDataDefinedProperty(BLANKS, QgsProperty.fromValue("((10 30, 50 60)),((4 20))"))
    layer.setRenderer(QgsSingleSymbolRenderer(QgsLineSymbol([ml])))
    reference = ink_mask(render([layer], EXTENT))
    outputs, rules, _ = _export(layer, tmp_path)
    zoom = scale_to_zoom(240 / 300 / 0.0254 * 96)
    band = [o for o, r in zip(outputs, rules) if r.recipe is not None and r.recipe.param("blank")
            and r.visibility.min_zoom <= zoom
            and (r.visibility.max_zoom is None or zoom < r.visibility.max_zoom)]
    assert band
    ours = ink_mask(render(band, EXTENT))
    assert mask_difference(reference, ours) < 0.08


@needs_blanks
def test_badly_formatted_blank_segments_blank_nothing(plugin, tmp_path):
    layer = _layer("LineString", LINES, str(tmp_path / "bad.gpkg"))
    ml = _markers(P.Interval, interval=9)
    ml.setDataDefinedProperty(BLANKS, QgsProperty.fromValue("(((40 10)))"))  # end < start
    _compare(layer, QgsLineSymbol([ml]), tmp_path, changed=False)


@needs_extra
@pytest.mark.parametrize("kind", ["markers", "hashes"])
@pytest.mark.parametrize("rotate", [True, False])
def test_extra_items_match_qgis(plugin, tmp_path, kind, rotate):
    """Every "x y angle" is drawn once a part at that map position, turned
    by the angle (clockwise): hashes always, markers when they follow the
    line. (QGIS keeps a hash line's last extra angle for the next
    features' unrotated hashes: the items are on the last feature here.)"""
    layer = _layer("LineString", LINES, str(tmp_path / "e.gpkg"),
                   labels=["", "-60 60 30, 0 -100 270, 70 20 0"])
    if kind == "markers":
        layer_ = _markers(P.FirstVertex)
    else:
        layer_ = QgsHashedLineSymbolLayer(True, 8)
        layer_.setPlacements(P.FirstVertex)
        layer_.setHashLength(14)
        layer_.setHashLengthUnit(Qgis.RenderUnit.Pixels)
        layer_.setHashAngle(20)
        layer_.setSubSymbol(QgsLineSymbol.createSimple({"color": "black", "width": "0.6"}))
    layer_.setRotateSymbols(rotate)
    layer_.setDataDefinedProperty(EXTRA, QgsProperty.fromField("label"))
    rules, diags = _compare(layer, QgsLineSymbol([layer_]), tmp_path)
    extra = [r for r in rules if r.recipe is not None and r.recipe.placements == ("ExtraItems",)]
    assert len(extra) == 1
    assert not diags.by_code("Q2VT_DDP_NO_EMITTER")


@needs_extra
def test_extra_items_of_a_polygon_outline_are_drawn_once_per_polygon(plugin, tmp_path):
    """Drawn with the exterior ring only (renderPolygonStroke blocks them
    for the rings after it)."""
    layer = _layer("Polygon", ["POLYGON((-97 -83, 53 -83, 53 71, -97 71, -97 -83),"
                               "(-40 -40, 10 -40, 10 10, -40 10, -40 -40))"],
                   str(tmp_path / "ep.gpkg"))
    ml = _markers(P.FirstVertex)
    ml.setDataDefinedProperty(EXTRA, QgsProperty.fromValue("80 80 45, 90 -90 180"))
    rules, _ = _compare(layer, QgsFillSymbol([ml]), tmp_path)
    assert any(r.recipe is not None and r.recipe.placements == ("ExtraItems",) for r in rules)


def test_blank_segment_and_extra_item_strings_parse_like_qgis():
    from q2vt_plugin.src.core import marker_points as mp
    assert mp.parse_blank_segments("(((2.90402 7.36,11.8776 30.4499),()),((2 7)))") == [
        [[(2.90402, 7.36), (11.8776, 30.4499)], []], [[(2.0, 7.0)]]]
    assert mp.parse_blank_segments("") == []
    for bad in ("((1 2))", "(((1 2)", "(((2 1)))", "(((1 2, 1.5 3)))", "(((1 2 3)))",
                "(((1)))", "(((a 2)))", "((((1 2))))", "(((-1 2)))"):
        assert mp.parse_blank_segments(bad) is None, bad
    assert mp.parse_extra_items("2.5 4.5 8.1,2 7 0, 4 8 12") == [
        (2.5, 4.5, 8.1), (2.0, 7.0, 0.0), (4.0, 8.0, 12.0)]
    assert mp.parse_extra_items("-3 -4 360") == [(-3.0, -4.0, 360.0)]
    for bad in ("1 2", "1 2 3 4", "1 2 400", ",1 2 3", "1 2 x", "1 2 -1"):
        assert mp.parse_extra_items(bad) == [], bad
    walker = mp.BlankWalker([(2.0, 4.0), (6.0, 6.0)])
    assert [walker.inside(d) for d in (1, 2, 3, 4, 5, 6, 7)] == [
        False, True, True, True, False, True, False]
    assert mp.trim_points([0, 10, 10], [0, 0, 10], 5, 5) == ([5.0, 10, 10.0], [0.0, 0, 5.0])
    # Trims that cross leave the piece between them reversed, as
    # polylineSubstring leaves it; one longer than the line leaves nothing.
    assert mp.trim_points([0, 10], [0, 0], 6, 5) == ([6.0, 5.0], [0.0, 0.0])
    assert mp.trim_points([0, 10], [0, 0], 10, 0) is None
    assert mp.trim_points([0, 10, 10], [0, 0, 10], 40, 0, True) == ([8.0, 10, 10], [0.0, 0, 10])
    # A start exactly on an inner vertex is found on no segment: QGIS draws
    # nothing of that part (polylineSubstring).
    assert mp.trim_points([0, 10, 10], [0, 0, 10], 50, 0, True) is None
    assert math.isclose(mp.polyline_length([0, 3], [0, 4]), 5.0)
