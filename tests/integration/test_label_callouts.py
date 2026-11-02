"""Callouts of point labels at their point (ideas of QGIS2VectorTiles
4.1-4.2): the simple, Manhattan or curved line QGIS draws from the label's
box to the point, drawn with the callout's line symbol as the label's icon,
and a balloon as the label's icon stretched to its text."""

import json
import os
import sys

import pytest
from qgis.core import (QgsBalloonCallout, QgsCurvedLineCallout, QgsFeature, QgsGeometry, QgsLineSymbol,
                       QgsManhattanLineCallout, QgsMarkerSymbol, QgsPalLayerSettings, QgsSimpleLineCallout,
                       QgsSingleSymbolRenderer, QgsTextFormat, QgsVectorLayer, QgsVectorLayerSimpleLabeling,
                       Qgis)
from qgis.PyQt.QtGui import QImage

from q2vt_fixtures import to_geopackage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_end_to_end import export  # noqa: E402,F401  pylint: disable=wrong-import-position,unused-import


def _labelled(tmp_path, callout, placement=Qgis.LabelPlacement.OverPoint, quadrant=None):
    layer = QgsVectorLayer("Point?crs=EPSG:3857&field=name:string", "sites", "memory")
    feature = QgsFeature(layer.fields())
    feature.setAttributes(["Kút"])
    feature.setGeometry(QgsGeometry.fromWkt("POINT(2121000 6021000)"))
    layer.dataProvider().addFeatures([feature])
    layer = to_geopackage(layer, str(tmp_path / "sites.gpkg"))
    layer.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple({"size": "2"})))
    settings = QgsPalLayerSettings()
    settings.fieldName = "name"
    settings.placement = placement
    if quadrant is not None:
        settings.quadOffset = quadrant
    settings.xOffset, settings.yOffset = 4, -4
    settings.offsetUnits = Qgis.RenderUnit.Millimeters
    text_format = QgsTextFormat()
    text_format.setSize(10)
    settings.setFormat(text_format)
    callout.setEnabled(True)
    settings.setCallout(callout)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)
    return layer


def _label_layer(result):
    style = json.load(open(os.path.join(result, "style", "style.json"), encoding="utf-8"))
    return next(layer for layer in style["layers"] if layer.get("layout", {}).get("text-field"))


@pytest.mark.parametrize("callout", [QgsSimpleLineCallout, QgsManhattanLineCallout, QgsCurvedLineCallout])
def test_line_callouts_are_the_labels_icon(export, tmp_path, callout):  # noqa: F811
    instance = callout()
    instance.setLineSymbol(QgsLineSymbol.createSimple({"line_color": "255,0,0", "line_width": "0.5"}))
    layer = _labelled(tmp_path, instance, quadrant=Qgis.LabelQuadrantPosition.AboveRight)
    _, result = export(layer)
    label = _label_layer(result)
    layout = label["layout"]
    assert layout.get("icon-image", "").startswith("callout_"), (layout, label.get("metadata"))
    assert layout["icon-allow-overlap"] and layout["icon-ignore-placement"]
    index = json.load(open(os.path.join(result, "style", "sprite", "sprite.json"), encoding="utf-8"))
    entry = index[layout["icon-image"]]
    sheet = QImage(os.path.join(result, "style", "sprite", "sprite.png"))
    # Red ink between the point (the centre) and the label (up and right):
    # none on the opposite side.
    x0, y0, w, h = entry["x"], entry["y"], entry["width"], entry["height"]
    ratio = entry["pixelRatio"]
    red = [((x - x0 - w / 2) / ratio, (y - y0 - h / 2) / ratio) for x in range(x0, x0 + w)
           for y in range(y0, y0 + h) if sheet.pixelColor(x, y).alpha() > 128 and sheet.pixelColor(x, y).red() > 150]
    if os.environ.get("Q2VT_DUMP"):
        sheet.copy(x0, y0, w, h).save(os.path.join(os.environ["Q2VT_DUMP"], f"{callout.__name__}.png"))
    # QGIS: from the label's box corner, 4 mm (15 px) right and up, to the point.
    assert red and all(dx > -1.5 and dy < 1.5 for dx, dy in red), (w, h, red[:5])
    assert max(dx for dx, _ in red) == pytest.approx(15.1, abs=1.5)


def test_a_balloon_is_the_labels_stretched_icon(export, tmp_path):  # noqa: F811
    from qgis.core import QgsFillSymbol
    balloon = QgsBalloonCallout()
    balloon.setFillSymbol(QgsFillSymbol.createSimple({"color": "255,255,200", "outline_color": "0,0,0"}))
    layer = _labelled(tmp_path, balloon, quadrant=Qgis.LabelQuadrantPosition.AboveRight)
    _, result = export(layer)
    layout = _label_layer(result)["layout"]
    assert layout.get("icon-text-fit") == "both" and layout["icon-image"].startswith("frame_")
    index = json.load(open(os.path.join(result, "style", "sprite", "sprite.json"), encoding="utf-8"))
    entry = index[layout["icon-image"]]
    assert entry["stretchX"] and entry["stretchY"] and len(entry["content"]) == 4
    # The wedge reaches down and left of the text (the point is there).
    left, top, right, bottom = entry["content"]
    assert left > 4 and entry["height"] / entry["pixelRatio"] - bottom > 4
