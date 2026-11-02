"""Label text as QGIS writes it (ideas of QGIS2VectorTiles 4.1): its type
case (title case, first letter, small caps; data-defined too) applied with
QGIS's own capitalize, the spaces at the start and end of a line kept
behind a word joiner (MapLibre trims them), and a data-defined priority
as each feature's symbol-sort-key."""

import json
import os
import sqlite3
import sys

from qgis.core import QgsPalLayerSettings, QgsProperty, QgsTextFormat, QgsVectorLayerSimpleLabeling, Qgis

from publishing import mvt
from publishing.controller import export_local

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_publishing_basemap_themes import EXTENT, _setup  # noqa: E402  pylint: disable=wrong-import-position

WJ = "⁠"


def _label(layer, expression, case=Qgis.Capitalization.MixedCase, properties=()):
    settings = QgsPalLayerSettings()
    settings.fieldName, settings.isExpression = expression, True
    text_format = QgsTextFormat()
    text_format.setSize(10)
    text_format.setCapitalization(case)
    settings.setFormat(text_format)
    for key, value in properties:
        settings.dataDefinedProperties().setProperty(key, QgsProperty.fromExpression(value))
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)


def _labels(result):
    texts = set()
    with sqlite3.connect(os.path.join(result.export_dir, "tiles.mbtiles")) as conn:
        for (data,) in conn.execute("SELECT tile_data FROM tiles"):
            for layer in mvt.decode(data).values():
                for feature in layer["features"]:
                    if "q2vt_label" in feature["properties"]:
                        texts.add(feature["properties"]["q2vt_label"])
    return texts


def _label_layers(result):
    style = json.load(open(os.path.join(result.release.release_dir, "style.json"), encoding="utf-8"))
    return [layer for layer in style["layers"] if "text-field" in layer.get("layout", {})]


def test_title_case_and_edge_spaces(tmp_path):
    project, profile, parcels, _second = _setup(tmp_path)
    _label(parcels, "'  the lord of tHE rings ' || \"hrsz\" || '  '", Qgis.Capitalization.TitleCase)
    result = export_local(project, profile, EXTENT)
    texts = _labels(result)
    # A word joiner outside the edge spaces (MapLibre trims whitespace at
    # the ends of a line only); the case is QGIS's own title case.
    from qgis.core import QgsStringUtils
    expected = QgsStringUtils.capitalize("  the lord of tHE rings 00123/4  ", Qgis.Capitalization.TitleCase)
    assert "Lord of THE Rings" in expected
    assert f"{WJ}{expected}{WJ}" in texts, texts
    assert all(layer["layout"].get("text-transform", "none") == "none" for layer in _label_layers(result)
               if layer["id"].startswith("l00"))


def test_data_defined_case_and_priority(tmp_path):
    project, profile, parcels, _second = _setup(tmp_path)
    _label(parcels, "'a ' || \"hrsz\"", Qgis.Capitalization.AllUppercase, [
        (QgsPalLayerSettings.Property.FontCase, "if(\"hrsz\" = '0099', 'Lower', 'Capitalize')"),
        (QgsPalLayerSettings.Property.Priority, "\"terulet\" / 100")])
    result = export_local(project, profile, EXTENT)
    texts = _labels(result)
    assert "A 00123/4" in texts, texts  # Capitalize, not the static upper case
    layers = [layer for layer in _label_layers(result) if layer["id"].startswith("l00")]  # the parcels
    assert layers and all(layer["layout"].get("text-transform", "none") == "none" for layer in layers)
    keys = [layer["layout"].get("symbol-sort-key") for layer in layers]
    assert all(isinstance(key, list) for key in keys), keys


def test_polygon_label_point_follows_force_inside(plugin):
    """Over point polygon labels: QGIS's centroid, moved inside the polygon
    only with "Force point inside polygon" (pal PointSet::getCentroid)."""
    from qgis.core import QgsExpression, QgsExpressionContext, QgsFeature, QgsGeometry, QgsRectangle
    from q2vt_plugin.src.core.rules_exporter import RulesExporter  # pylint: disable=import-error
    exporter = RulesExporter.__new__(RulesExporter)
    exporter.cent_source, exporter.extent = 2, QgsRectangle(-10, -10, 10, 10)
    u_shape = QgsGeometry.fromWkt("POLYGON((0 0, 6 0, 6 6, 4 6, 4 2, 2 2, 2 6, 0 6, 0 0))")
    feature = QgsFeature()
    feature.setGeometry(u_shape)
    for force, inside in ((False, False), (True, True)):
        context = QgsExpressionContext()
        context.setFeature(feature)
        expression = exporter._get_polygon_centroids_expression(force_inside=force)  # pylint: disable=protected-access
        point = QgsExpression(expression).evaluate(context)
        assert u_shape.contains(point) is inside, (force, point.asWkt())


def test_data_defined_font_family(tmp_path):
    """A data-defined family: each feature's family (installed ones), the
    format's font for the others; glyphs for both (idea of QGIS2VectorTiles 4.2)."""
    from q2vt_support import font_database  # pylint: disable=import-error
    if "DejaVu Sans Mono" not in font_database().families():
        import pytest
        pytest.skip("DejaVu Sans Mono is not installed")
    project, profile, parcels, _second = _setup(tmp_path)
    _label(parcels, "\"hrsz\"", properties=[
        (QgsPalLayerSettings.Property.Family,
         "if(\"hrsz\" = '00123/4', 'DejaVu Sans Mono', if(\"hrsz\" = '00123/5', 'No Such Font', NULL))")])
    result = export_local(project, profile, EXTENT)
    layer = next(layer for layer in _label_layers(result) if layer["id"].startswith("l00"))
    fonts = layer["layout"]["text-font"]
    assert fonts[0] == "match" and fonts[2] == "DejaVu Sans Mono", fonts  # "No Such Font": the format's
    assert fonts[3][1][0].startswith("DejaVu Sans Mono") and len(fonts) == 5, fonts  # one family case
    glyphs = os.listdir(os.path.join(result.release.release_dir, "glyphs"))
    assert fonts[3][1][0] in glyphs and fonts[4][1][0] in glyphs, glyphs
