"""QGIS 4 label placement modes: multi-part behaviour (label the largest
part, every part, or split the text's lines over the parts) and curved
label modes (characters at vertices, stretched spacing).

The QGIS 4 settings tests skip on QGIS 3, where only ``labelPerPart``
exists; the helpers then read it as before.
"""

import json
import os
import sys

import pytest
from qgis.core import (Qgis, QgsFeature, QgsField, QgsGeometry, QgsLineSymbol,
                       QgsPalLayerSettings, QgsProcessingFeedback, QgsProperty, QgsRectangle,
                       QgsSingleSymbolRenderer, QgsFillSymbol, QgsTextFormat, QgsVectorLayer,
                       QgsVectorLayerSimpleLabeling)
from qgis.PyQt.QtCore import QVariant

from q2vt_fixtures import reset_project, to_geopackage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_end_to_end import export  # noqa: E402,F401  pylint: disable=wrong-import-position,unused-import

EXTENT = QgsRectangle(-200, -200, 200, 200)
QGIS4 = hasattr(Qgis, "MultiPartLabelingBehavior")
qgis4 = pytest.mark.skipif(not QGIS4, reason="QGIS 4 label placement modes")


def _layer(kind, rows, path):
    layer = QgsVectorLayer(f"{kind}?crs=EPSG:3857", "src", "memory")
    layer.dataProvider().addAttributes([QgsField("id", QVariant.Int), QgsField("t", QVariant.String)])
    layer.updateFields()
    features = []
    for i, (wkt, text) in enumerate(rows):
        feature = QgsFeature(layer.fields())
        feature.setAttributes([i, text])
        feature.setGeometry(QgsGeometry.fromWkt(wkt))
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    return to_geopackage(layer, path)


def _labelled(layer, settings):
    symbol = QgsFillSymbol.createSimple({"color": "200,200,200"}) \
        if layer.geometryType() == Qgis.GeometryType.Polygon \
        else QgsLineSymbol.createSimple({"color": "200,200,200"})
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)
    return layer


def _settings(placement=Qgis.LabelPlacement.OverPoint, multipart=None, curved=None):
    settings = QgsPalLayerSettings()
    settings.fieldName = "t"
    settings.placement = placement
    fmt = QgsTextFormat()
    fmt.setSize(10)
    settings.setFormat(fmt)
    if multipart is not None:
        placement_settings = settings.placementSettings()
        placement_settings.setMultiPartBehavior(getattr(Qgis.MultiPartLabelingBehavior, multipart))
        settings.setPlacementSettings(placement_settings)
    if curved is not None:
        line_settings = settings.lineSettings()
        line_settings.setCurvedLabelMode(getattr(Qgis.CurvedLabelMode, curved))
        settings.setLineSettings(line_settings)
    return settings


def _export(layer, tmp_path):
    from q2vt_plugin.src.core.rules_flattener import RulesFlattener
    from q2vt_plugin.src.core.rules_exporter import RulesExporter
    from fidelity.diagnostics import DiagnosticCollector
    reset_project(layer)
    diags = DiagnosticCollector()
    rules = RulesFlattener(0, 22, str(tmp_path), QgsProcessingFeedback(), diags).flatten_all_rules()
    (tmp_path / "utils").mkdir()
    outputs, rules = RulesExporter(rules, EXTENT, 0, 22, str(tmp_path / "utils"), 0,
                                   QgsProcessingFeedback(), diagnostics=diags).export()
    return {o.name(): o for o in outputs}, rules, diags


def _labels(outputs, rules):
    """(orig id, label text, geometry) of the label dataset's features."""
    rule = [r for r in rules if r.get_attr("t") == 1][0]
    dataset = outputs[rule.output_dataset]
    return [(int(f["q2vt_orig_id"]), f["q2vt_label"], f.geometry()) for f in dataset.getFeatures()]


def test_multipart_mode_reads_label_per_part_without_qgis4(plugin):
    from q2vt_plugin.src.utils.qt_compat import label_multipart_mode, curved_label_mode
    settings = QgsPalLayerSettings()
    settings.placement = Qgis.LabelPlacement.Curved
    assert curved_label_mode(settings) == "default"
    if QGIS4:  # the shim: labelPerPart sets "every part"
        settings.labelPerPart = True
        assert label_multipart_mode(settings) == "every"
        return
    assert label_multipart_mode(settings) == "largest"
    settings.labelPerPart = True
    assert label_multipart_mode(settings) == "every"


@qgis4
@pytest.mark.parametrize("behavior,value,expected", [
    ("SplitLabelTextLinesOverParts", None, "split"),
    ("LabelEveryPartWithEntireLabel", None, "every"),
    ("LabelLargestPartOnly", None, "largest"),
    ("LabelLargestPartOnly", "SplitLabelTextLinesOverParts", "split"),
    ("SplitLabelTextLinesOverParts", " labeleverypart", "every"),
    ("SplitLabelTextLinesOverParts", True, "every"),
    ("LabelEveryPartWithEntireLabel", "0", "largest"),
])
def test_multipart_mode_follows_the_qgis4_behaviour(plugin, behavior, value, expected):
    """QGIS 4 keeps labelPerPart as a lossy shim (split reads False): the
    behaviour is read from the placement settings, a static data-defined
    "LabelAllParts" by name or as a boolean (QgsLabelPlacementSettings::
    updateDataDefinedProperties)."""
    from q2vt_plugin.src.utils.qt_compat import label_mode_data_defined, label_multipart_mode
    settings = _settings(multipart=behavior)
    if value is not None:
        settings.dataDefinedProperties().setProperty(
            QgsPalLayerSettings.Property.LabelAllParts, QgsProperty.fromValue(value))
    assert label_multipart_mode(settings) == expected
    assert not label_mode_data_defined(settings, "LabelAllParts")
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.LabelAllParts, QgsProperty.fromField("t"))
    assert label_mode_data_defined(settings, "LabelAllParts")


@qgis4
@pytest.mark.parametrize("placement", ["OverPoint", "Horizontal"])
def test_split_lines_go_one_per_part(plugin, tmp_path, placement):
    """SplitLabelTextLinesOverParts: part i of a feature gets line i of its
    text (after the wrap character and automatic wrapping); parts without a
    line get no label; a single-part feature shows its first line only
    (QgsPalLayerSettings::registerFeatureWithDetails)."""
    layer = _layer("MultiPolygon", [
        ("MULTIPOLYGON(((-150 -150, -100 -150, -100 -100, -150 -100, -150 -150)),"
         "((0 0, 50 0, 50 50, 0 50, 0 0)),((100 100, 150 100, 150 150, 100 150, 100 100)))",
         "North|South"),
        ("MULTIPOLYGON(((-150 100, -100 100, -100 150, -150 150, -150 100)))", "Alpha|Beta"),
        ("MULTIPOLYGON(((100 -150, 150 -150, 150 -100, 100 -100, 100 -150)),"
         "((150 -50, 190 -50, 190 -10, 150 -10, 150 -50)))", "one two three"),
    ], str(tmp_path / "parts.gpkg"))
    settings = _settings(getattr(Qgis.LabelPlacement, placement), multipart="SplitLabelTextLinesOverParts")
    settings.wrapChar = "|"
    settings.autoWrapLength = 4
    settings.useMaxLineLengthForAutoWrap = False  # at least 4 characters a line
    outputs, rules, _ = _export(_labelled(layer, settings), tmp_path)
    labels = sorted((orig, text, round(g.asPoint().x()), round(g.asPoint().y()))
                    for orig, text, g in _labels(outputs, rules))
    assert labels == [(1, "North", -125, -125), (1, "South", 25, 25), (2, "Alpha", -125, 125),
                      (3, "one two", 125, -125), (3, "three", 170, -30)], labels


@qgis4
def test_split_lines_of_curved_line_labels(plugin, tmp_path):
    """Curved line labels split over the parts: one line per part (a curved
    label may have several lines in this mode), the third part none."""
    layer = _layer("MultiLineString", [
        ("MULTILINESTRING((-150 -100, 150 -100),(-150 50, 150 50),(-150 150, 150 150))", "Upper\nLower"),
    ], str(tmp_path / "lines.gpkg"))
    settings = _settings(Qgis.LabelPlacement.Curved, multipart="SplitLabelTextLinesOverParts")
    outputs, rules, _ = _export(_labelled(layer, settings), tmp_path)
    labels = sorted((text, round(g.asPoint().y())) for _, text, g in _labels(outputs, rules))
    assert labels == [("Lower", 50), ("Upper", -100)], labels


@qgis4
def test_whole_label_on_every_part_and_on_the_largest(plugin, tmp_path):
    rows = [("MULTIPOLYGON(((-150 -150, -100 -150, -100 -100, -150 -100, -150 -150)),"
             "((0 0, 80 0, 80 80, 0 80, 0 0)))", "North|South")]
    for behavior, expected in (("LabelEveryPartWithEntireLabel", 2), ("LabelLargestPartOnly", 1)):
        out = tmp_path / behavior
        out.mkdir()
        layer = _layer("MultiPolygon", rows, str(out / "parts.gpkg"))
        settings = _settings(multipart=behavior)
        settings.wrapChar = "|"
        outputs, rules, _ = _export(_labelled(layer, settings), out)
        labels = _labels(outputs, rules)
        assert len(labels) == expected
        assert {text for _, text, _ in labels} == {"North\nSouth"}


@qgis4
def test_characters_at_vertices(plugin, tmp_path):
    """PlaceCharactersAtVertices: the characters, blanks skipped, one at each
    vertex (more characters than vertices: the rest left out), turned to the
    segment from their vertex (pal FeaturePart::
    createCurvedCandidateWithCharactersAtVertices)."""
    layer = _layer("LineString", [
        ("LINESTRING(-100 0, -50 0, -50 50, 0 100, 50 50)", "Ab c de f"),
        ("LINESTRING(100 -100, 150 -100, 150 -150)", "XY"),
    ], str(tmp_path / "lines.gpkg"))
    settings = _settings(Qgis.LabelPlacement.Curved, curved="PlaceCharactersAtVertices")
    outputs, rules, _ = _export(_labelled(layer, settings), tmp_path)
    rule = [r for r in rules if r.get_attr("t") == 1][0]
    dataset = outputs[rule.output_dataset]
    rotation = [f.name() for f in dataset.fields() if "rotation" in f.name()]
    assert rotation, [f.name() for f in dataset.fields()]
    chars = sorted((int(f["q2vt_orig_id"]), round(f.geometry().asPoint().x()),
                    round(f.geometry().asPoint().y()), f["q2vt_label"], round(f[rotation[0]]))
                   for f in dataset.getFeatures())
    assert chars == [
        (1, -100, 0, "A", 0), (1, -50, 0, "b", -90), (1, -50, 50, "c", -45), (1, 0, 100, "d", 45),
        (1, 50, 50, "e", 45),
        (2, 100, -100, "X", 0), (2, 150, -100, "Y", 90)], chars


@qgis4
def test_stretch_modes_keep_the_viewer_line_label(plugin, tmp_path):
    """Stretched curved labels stay one label at the line's middle (the
    viewer stretches it over the visible line) and are not laid out in
    windows."""
    layer = _layer("LineString", [("LINESTRING(-150 0, 150 0)", "Mill Road")], str(tmp_path / "l.gpkg"))
    settings = _settings(Qgis.LabelPlacement.Curved, curved="StretchCharacterSpacingToFitLine")
    outputs, rules, _ = _export(_labelled(layer, settings), tmp_path)
    labels = _labels(outputs, rules)
    assert [(text, round(g.asPoint().x())) for _, text, g in labels] == [("Mill Road", 0)]
    assert any(getattr(r, "line_curved", False) for r in rules)
    assert all(r.label_modes["curved"] == "stretch_chars" for r in rules if r.get_attr("t") == 1)


def _style_layers(layer, export):
    exporter, result = export(layer, min_zoom=14, max_zoom=16)
    style = json.load(open(os.path.join(result, "style", "style.json"), encoding="utf-8"))
    return exporter, [l for l in style["layers"] if l.get("type") == "symbol"]


def _web_layer(tmp_path, kind, wkt, text):
    """A layer near the end-to-end export extent (test_end_to_end.EXTENT)."""
    x, y = 2121000, 6021000
    shifted = QgsGeometry.fromWkt(wkt)
    shifted.translate(x, y)
    return _layer(kind, [(shifted.asWkt(), text)], str(tmp_path / "web.gpkg"))


@qgis4
def test_characters_at_vertices_style(plugin, tmp_path, export):  # noqa: F811
    layer = _web_layer(tmp_path, "LineString", "LINESTRING(-100 0, -50 0, -50 50)", "abc")
    settings = _settings(Qgis.LabelPlacement.Curved, curved="PlaceCharactersAtVertices")
    settings.dist = 2
    settings.distUnits = Qgis.RenderUnit.Millimeters
    exporter, labels = _style_layers(_labelled(layer, settings), export)
    layout = labels[0]["layout"]
    assert layout["symbol-placement"] == "point" and layout["text-anchor"] == "bottom-left"
    assert layout["text-rotation-alignment"] == "map" and layout["text-keep-upright"] is False
    assert layout["text-allow-overlap"] is True
    assert layout["text-offset"][0] == 0 and layout["text-offset"][1] < 0  # to the left of the line
    assert "get" in str(layout["text-rotate"])
    assert any("vertices" in d.message for d in exporter.diagnostics.by_code("Q2VT_LABEL_APPROXIMATE"))


@qgis4
def test_stretch_and_whitespace_options_are_reported(plugin, tmp_path, export):  # noqa: F811
    layer = _web_layer(tmp_path, "LineString", "LINESTRING(-100 0, 100 0)", "Mill Road")
    settings = _settings(Qgis.LabelPlacement.Curved, curved="StretchWordSpacingToFitLine")
    placement_settings = settings.placementSettings()
    placement_settings.setWhitespaceCollisionHandling(
        Qgis.LabelWhitespaceCollisionHandling.IgnoreWhitespaceCollisions)
    settings.setPlacementSettings(placement_settings)
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.CurvedLabelMode, QgsProperty.fromField("t"))
    exporter, labels = _style_layers(_labelled(layer, settings), export)
    stretched = [l for l in labels if (l.get("metadata") or {}).get("q2vt:curved-stretch")]
    assert stretched and stretched[0]["metadata"]["q2vt:curved-stretch"] == "words"
    messages = " ".join(d.message for d in exporter.diagnostics.by_code("Q2VT_LABEL_APPROXIMATE"))
    assert "whitespace" in messages and "Stretch word spacing" in messages
    assert "Data-defined CurvedLabelMode" in messages


@qgis4
def test_split_lines_are_not_wrapped_again(plugin, tmp_path, export):  # noqa: F811
    layer = _web_layer(tmp_path, "MultiPolygon",
                       "MULTIPOLYGON(((0 0, 50 0, 50 50, 0 50, 0 0)),((100 0, 150 0, 150 50, 100 50, 100 0)))",
                       "Some long text")
    settings = _settings(multipart="SplitLabelTextLinesOverParts")
    settings.autoWrapLength = 5
    _, labels = _style_layers(_labelled(layer, settings), export)
    assert labels and all(l["layout"]["text-max-width"] == 999 for l in labels)
    assert all((l.get("metadata") or {}).get("q2vt:label-per-part", True) for l in labels)


def _vertex_chars(outputs, rules):
    """(orig id, x, y, character, rotation) of a characters-at-vertices dataset."""
    rule = [r for r in rules if r.get_attr("t") == 1][0]
    dataset = outputs[rule.output_dataset]
    rotation = [f.name() for f in dataset.fields() if "rotation" in f.name()][0]
    return sorted((int(f["q2vt_orig_id"]), round(f.geometry().asPoint().x()), round(f.geometry().asPoint().y()),
                   f["q2vt_label"], round(f[rotation])) for f in dataset.getFeatures())


@pytest.mark.parametrize("value", ["no", "n", "f", "0.0", "", " ", "0", "false", "FALSE", " false", "yes",
                                   0, 0.0, 2, True, False, None])
def test_static_label_all_parts_reads_as_qgis(plugin, value):
    """A static data-defined "LabelAllParts" that names no behaviour is read
    as QgsProperty::valueAsBool reads it (QVariant::toBool: a string is
    false only when empty, "0" or "false", any case, untrimmed; NULL keeps
    the default, "every part" only if it was), on QGIS 3 as on QGIS 4."""
    from q2vt_plugin.src.utils.qt_compat import label_multipart_mode
    from qgis.core import QgsExpressionContext
    for every in (False, True):
        settings = QgsPalLayerSettings()
        if QGIS4:
            placement_settings = settings.placementSettings()
            placement_settings.setMultiPartBehavior(
                Qgis.MultiPartLabelingBehavior.LabelEveryPartWithEntireLabel if every
                else Qgis.MultiPartLabelingBehavior.LabelLargestPartOnly)
            settings.setPlacementSettings(placement_settings)
        else:
            settings.labelPerPart = every
        prop = QgsProperty.fromValue(value)
        settings.dataDefinedProperties().setProperty(QgsPalLayerSettings.Property.LabelAllParts, prop)
        expected, _ = prop.valueAsBool(QgsExpressionContext(), every)
        assert label_multipart_mode(settings) == ("every" if expected else "largest"), (value, every)


@qgis4
def test_split_with_a_null_label_all_parts_is_largest_part_only(plugin):
    """QGIS 4: a NULL static "LabelAllParts" names nothing and reads as
    false (the default: split is not "every part")."""
    from q2vt_plugin.src.utils.qt_compat import label_multipart_mode
    settings = _settings(multipart="SplitLabelTextLinesOverParts")
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.LabelAllParts, QgsProperty.fromValue(None))
    assert label_multipart_mode(settings) == "largest"


@qgis4
def test_characters_at_vertices_of_a_multipart_polygon_keep_its_ring(plugin, tmp_path):
    """"Largest part only": the characters go on the longest ring of the
    whole feature from its first vertex, in its direction, as stored (QGIS
    labels the polygon's boundary): not on a ring rewritten by a dissolve
    (another start vertex, reversed)."""
    layer = _layer("MultiPolygon", [
        ("MULTIPOLYGON(((100 100, -100 100, -100 -100, 100 -100, 100 100)),"
         "((150 150, 160 150, 160 160, 150 150)))", "ABCDEF")], str(tmp_path / "p.gpkg"))
    settings = _settings(Qgis.LabelPlacement.PerimeterCurved, curved="PlaceCharactersAtVertices")
    outputs, rules, _ = _export(_labelled(layer, settings), tmp_path)
    assert _vertex_chars(outputs, rules) == [
        (1, -100, -100, "C", 0), (1, -100, 100, "B", 90), (1, 100, -100, "D", -90),
        (1, 100, 100, "A", -180), (1, 100, 100, "E", -90)]


@qgis4
def test_characters_at_vertices_on_every_ring(plugin, tmp_path):
    """"Label every part": every ring of the boundary is a part, holes
    included, each with the text from its first vertex."""
    layer = _layer("Polygon", [
        ("POLYGON((100 100, -100 100, -100 -100, 100 -100, 100 100),(-10 -10, 10 -10, 10 10, -10 -10))",
         "AB")], str(tmp_path / "p.gpkg"))
    settings = _settings(Qgis.LabelPlacement.PerimeterCurved, curved="PlaceCharactersAtVertices",
                         multipart="LabelEveryPartWithEntireLabel")
    outputs, rules, _ = _export(_labelled(layer, settings), tmp_path)
    chars = [(x, y, text) for _, x, y, text, _ in _vertex_chars(outputs, rules)]
    assert sorted(chars) == [(-100, 100, "B"), (-10, -10, "A"), (10, -10, "B"), (100, 100, "A")], chars


@qgis4
def test_characters_at_vertices_are_graphemes(plugin, tmp_path):
    """One grapheme a vertex (QgsPalLabeling::splitToGraphemes): an emoji
    or a letter with a combining accent is one character, never half a
    surrogate pair; blanks (any white space) take no vertex."""
    layer = _layer("LineString", [("LINESTRING(-100 0, -50 0, 0 0, 50 0, 100 0)",
                                   "a\U0001F600 é b")], str(tmp_path / "l.gpkg"))
    settings = _settings(Qgis.LabelPlacement.Curved, curved="PlaceCharactersAtVertices")
    outputs, rules, _ = _export(_labelled(layer, settings), tmp_path)
    chars = [(x, text) for _, x, _, text, _ in _vertex_chars(outputs, rules)]
    assert chars == [(-100, "a"), (-50, "\U0001F600"), (0, "é"), (50, "b")], chars


@qgis4
def test_characters_at_vertices_of_html_labels_are_plain(plugin, tmp_path, export):  # noqa: F811
    """An HTML label's characters at vertices are its text's, not its
    markup's, and each point draws its own character (plain text-field)."""
    layer = _layer("LineString", [("LINESTRING(-100 0, -50 0, 0 0, 50 0, 100 0)", "<b>Ab</b> c")],
                   str(tmp_path / "l.gpkg"))
    settings = _settings(Qgis.LabelPlacement.Curved, curved="PlaceCharactersAtVertices")
    fmt = settings.format()
    fmt.setAllowHtmlFormatting(True)
    settings.setFormat(fmt)
    outputs, rules, _ = _export(_labelled(layer, settings), tmp_path)
    assert [(x, text) for _, x, _, text, _ in _vertex_chars(outputs, rules)] == [
        (-100, "A"), (-50, "b"), (0, "c")]
    web = tmp_path / "web"
    web.mkdir()
    layer = _web_layer(web, "LineString", "LINESTRING(-100 0, -50 0, 0 0, 50 0)", "<b>Ab</b> c")
    settings = _settings(Qgis.LabelPlacement.Curved, curved="PlaceCharactersAtVertices")
    fmt = settings.format()
    fmt.setAllowHtmlFormatting(True)
    settings.setFormat(fmt)
    _, labels = _style_layers(_labelled(layer, settings), export)
    assert labels[0]["layout"]["text-field"] == ["get", "q2vt_label"]


@qgis4
def test_split_lines_follow_the_part_number(plugin, tmp_path):
    """Line i goes to part i of the feature (asGeometryCollection) even
    where the rule's filter drops another part of it: the parts are
    numbered in the base layer."""
    from qgis.core import QgsRuleBasedLabeling
    layer = _layer("MultiPolygon", [(
        "MULTIPOLYGON(((-150 -150, -140 -150, -140 -140, -150 -140, -150 -150)),"
        "((0 0, 50 0, 50 50, 0 50, 0 0)),((100 100, 150 100, 150 150, 100 150, 100 100)))",
        "One|Two|Three")], str(tmp_path / "p.gpkg"))
    settings = _settings(Qgis.LabelPlacement.OverPoint, multipart="SplitLabelTextLinesOverParts")
    settings.wrapChar = "|"
    _labelled(layer, settings)
    root = QgsRuleBasedLabeling.Rule(None)
    rule = QgsRuleBasedLabeling.Rule(settings)
    rule.setFilterExpression("$area > 1000")  # evaluated on each part here
    root.appendChild(rule)
    layer.setLabeling(QgsRuleBasedLabeling(root))
    outputs, rules, _ = _export(layer, tmp_path)
    labels = sorted((text, round(g.asPoint().x())) for _, text, g in _labels(outputs, rules))
    assert labels == [("Three", 125), ("Two", 25)], labels
    rule = [r for r in rules if r.get_attr("t") == 1][0]
    assert outputs[rule.output_dataset].fields().indexFromName("q2vt_part") < 0  # only used here


@qgis4
def test_split_lines_over_generated_parts(plugin, tmp_path):
    """A label geometry generator: QGIS shares the lines out over the parts
    of the generated geometry."""
    layer = _layer("LineString", [("LINESTRING(-100 0, 100 0)", "Start|End")], str(tmp_path / "g.gpkg"))
    settings = _settings(Qgis.LabelPlacement.OverPoint, multipart="SplitLabelTextLinesOverParts")
    settings.wrapChar = "|"
    settings.geometryGeneratorEnabled = True
    settings.geometryGeneratorType = Qgis.GeometryType.Point
    settings.geometryGenerator = "collect_geometries(start_point($geometry), end_point($geometry))"
    outputs, rules, _ = _export(_labelled(layer, settings), tmp_path)
    assert sorted((text, round(g.asPoint().x())) for _, text, g in _labels(outputs, rules)) == [
        ("End", 100), ("Start", -100)]


@qgis4
def test_split_lines_with_data_defined_wrapping(plugin, tmp_path):
    """A data-defined wrap character and automatic wrap length decide the
    lines shared out over the parts (QgsPalLayerSettings::
    evaluateLabelContent); NULL keeps the layer's."""
    layer = _layer("MultiPolygon", [
        ("MULTIPOLYGON(((-150 -150, -100 -150, -100 -100, -150 -100, -150 -150)),"
         "((0 0, 50 0, 50 50, 0 50, 0 0)))", "North;South"),
        ("MULTIPOLYGON(((100 -150, 150 -150, 150 -100, 100 -100, 100 -150)),"
         "((150 -50, 190 -50, 190 -10, 150 -10, 150 -50)))", "one two")], str(tmp_path / "p.gpkg"))
    settings = _settings(multipart="SplitLabelTextLinesOverParts")
    settings.wrapChar = "|"
    props = settings.dataDefinedProperties()
    props.setProperty(QgsPalLayerSettings.Property.MultiLineWrapChar,
                      QgsProperty.fromExpression("if(\"id\" = 0, ';', NULL)"))
    props.setProperty(QgsPalLayerSettings.Property.AutoWrapLength,
                      QgsProperty.fromExpression("if(\"id\" = 1, 3, NULL)"))
    outputs, rules, _ = _export(_labelled(layer, settings), tmp_path)
    labels = sorted((orig, text) for orig, text, _ in _labels(outputs, rules))
    assert labels == [(1, "North"), (1, "South"), (2, "one"), (2, "two")], labels


@qgis4
def test_characters_at_vertices_report_what_they_do_not_follow(plugin, tmp_path, export):  # noqa: F811
    layer = _web_layer(tmp_path, "LineString", "LINESTRING(-100 0, -50 0, -50 50)", "abc")
    settings = _settings(Qgis.LabelPlacement.Curved, curved="PlaceCharactersAtVertices")
    line_settings = settings.lineSettings()
    line_settings.setMergeLines(True)
    settings.setLineSettings(line_settings)
    exporter, _ = _style_layers(_labelled(layer, settings), export)
    assert any("merge connected lines" in d.message
               for d in exporter.diagnostics.by_code("Q2VT_LABEL_APPROXIMATE"))
