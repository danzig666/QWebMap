"""HTML labels keep each run's colour, bold / italic and family (QGIS draws
them; only their sizes were kept): one ``format`` section per run, its
``text-color`` and ``text-font`` from fields, the fonts' glyphs built."""

import json
import os
import sys

from qgis.core import (QgsFeature, QgsField, QgsGeometry, QgsMarkerSymbol, QgsPalLayerSettings,
                       QgsSingleSymbolRenderer, QgsTextFormat, QgsVectorLayer,
                       QgsVectorLayerSimpleLabeling)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QFont

from q2vt_fixtures import to_geopackage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_end_to_end import export  # noqa: E402,F401  pylint: disable=wrong-import-position,unused-import

TEXT = ('Plain <b>Bold</b> <span style="color:#ff0000">Red</span> '
        '<span style="background-color:yellow">Marked</span>')


def _labelled_points(path, text=TEXT):
    layer = QgsVectorLayer("Point?crs=EPSG:3857", "pts", "memory")
    layer.dataProvider().addAttributes([QgsField("t", QVariant.String)])
    layer.updateFields()
    feature = QgsFeature(layer.fields())
    feature.setAttributes([text])
    feature.setGeometry(QgsGeometry.fromWkt("POINT(2121000 6021000)"))
    layer.dataProvider().addFeatures([feature])
    layer = to_geopackage(layer, path)
    layer.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple({"size": "2"})))
    settings = QgsPalLayerSettings()
    settings.fieldName = "t"
    fmt = QgsTextFormat()
    fmt.setFont(QFont("DejaVu Sans"))
    fmt.setSize(10)
    fmt.setAllowHtmlFormatting(True)
    settings.setFormat(fmt)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)
    return layer


def test_html_runs_get_their_colour_and_font(plugin, tmp_path, export):  # noqa: F811
    exporter, result = export(_labelled_points(str(tmp_path / "p.gpkg")), min_zoom=14, max_zoom=15)
    style = json.load(open(os.path.join(result, "style", "style.json"), encoding="utf-8"))
    [label] = [l for l in style["layers"] if l.get("type") == "symbol" and "text-field" in l["layout"]]
    field = label["layout"]["text-field"]
    assert field[0] == "format"
    options = field[2]
    assert options["text-color"][:2] == ["to-color", ["get", "q2vt_label_c0"]]
    font = options["text-font"]
    assert font[0] == "match" and font[2] == "|1|", font
    bold_stack, default = font[3][1][0], font[-1]
    assert "Bold" in bold_stack and default == ["literal", label["layout"]["text-font"]]
    # The bold face's glyphs are built like the label font's.
    glyph_dirs = set()
    for root, dirs, _ in os.walk(result):
        if os.path.basename(root) == "glyphs":
            glyph_dirs.update(dirs)
    assert bold_stack in glyph_dirs and label["layout"]["text-font"][0] in glyph_dirs, glyph_dirs
    codes = [d.code for d in exporter.diagnostics.items] if hasattr(exporter, "diagnostics") else []
    report = os.path.join(result, "fidelity_report.json")
    if os.path.exists(report):
        codes += [d["code"] + " " + d.get("message", "")
                  for d in json.load(open(report, encoding="utf-8")).get("diagnostics", [])]
    assert any("background colour" in str(c) for c in codes), codes


def _exported_runs(tmp_path, text):
    from qgis.core import QgsProcessingFeedback, QgsRectangle  # pylint: disable=import-outside-toplevel
    from q2vt_fixtures import reset_project  # pylint: disable=import-outside-toplevel
    from q2vt_plugin.src.core.rules_flattener import RulesFlattener  # pylint: disable=import-error
    from q2vt_plugin.src.core.rules_exporter import RulesExporter  # pylint: disable=import-error
    from fidelity.diagnostics import DiagnosticCollector  # pylint: disable=import-error
    layer = _labelled_points(str(tmp_path / "p.gpkg"), text)
    reset_project(layer)
    diags = DiagnosticCollector()
    rules = RulesFlattener(0, 22, str(tmp_path), QgsProcessingFeedback(), diags).flatten_all_rules()
    utils = tmp_path / "utils"
    utils.mkdir()
    extent = QgsRectangle(2120000, 6020000, 2122000, 6022000)
    layers, rules = RulesExporter(rules, extent, 0, 22, str(utils), 0, QgsProcessingFeedback(),
                                  diagnostics=diags).export()
    [labels] = [l for l, r in zip(layers, rules) if r.get_attr("t") == 1]
    [feature] = list(labels.getFeatures())
    names = labels.fields().names()
    runs = [(feature[f"q2vt_label_h{i}"], feature[f"q2vt_label_s{i}"], feature[f"q2vt_label_c{i}"],
             feature[f"q2vt_label_f{i}"]) for i in range(4) if f"q2vt_label_h{i}" in names]
    def plain(value):
        return None if value is None or str(value) == "NULL" else value
    return [tuple(plain(v) for v in run) for run in runs]


def test_html_runs_in_the_exported_fields(plugin, tmp_path):
    """The run fields as the exporter writes them (one feature)."""
    runs = _exported_runs(tmp_path, 'A <i>it</i> <span style="font-size:20pt;color:blue">big</span>')
    assert runs[:4] == [("A ", None, None, None), ("it", None, None, "||1"), (" ", None, None, None),
                        ("big", 2.0, "blue", None)], runs


def test_size_only_span_keeps_its_text_apart(plugin, tmp_path):
    """A span setting only an absolute size: its text field holds only its
    text, paired with its scale (not the whole label scaled)."""
    runs = _exported_runs(tmp_path, '<span style="font-size:20pt">Big</span> small')
    assert runs[:2] == [("Big", 2.0, None, None), (" small", None, None, None)], runs
    assert all(run[0] is None for run in runs[2:]), runs


def test_html_entities_get_their_glyphs(plugin, tmp_path):
    """The glyph scan reads the stored label (raw markup): the characters its
    entities decode to, drawn from the section fields, are built too."""
    from q2vt_plugin.src.core.glyphs_generator import GlyphGenerator  # pylint: disable=import-error
    path = str(tmp_path / "p.gpkg")
    _labelled_points(path, "Caf&eacute; &#8364;5&nbsp;x AT&amp;T")
    chars = GlyphGenerator._extract_unique_chars([path], "t")  # pylint: disable=protected-access
    assert {"é", "€", " ", "&", "a", "m", "p", ";"} <= chars, chars
