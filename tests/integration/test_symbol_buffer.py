"""A marker symbol's buffer (QGIS 3.40+ symbol buffer settings) around the
whole symbol, drawn once under all its layers, as QGIS draws it
(QgsSymbol::renderFeature buffers the shape of the rendered symbol).
Split into one icon per symbol layer, each layer had kept the buffer: a
buffer around every part, painted over the layers below it."""

import json
import os
import sys

import pytest
from qgis.core import (QgsFeature, QgsFillSymbol, QgsGeometry, QgsMarkerSymbol, QgsSimpleMarkerSymbolLayer,
                       QgsSingleSymbolRenderer, QgsVectorLayer)
from qgis.PyQt.QtCore import QPointF
from qgis.PyQt.QtGui import QColor, QImage

from q2vt_fixtures import to_geopackage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_end_to_end import export  # noqa: E402,F401  pylint: disable=wrong-import-position,unused-import

pytestmark = pytest.mark.skipif(not hasattr(QgsMarkerSymbol(), "bufferSettings"),
                                reason="symbol buffers need QGIS 3.40")


def _buffered_points(tmp_path):
    from qgis.core import QgsSymbolBufferSettings  # pylint: disable=import-outside-toplevel
    layer = QgsVectorLayer("Point?crs=EPSG:3857", "trees", "memory")
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromWkt("POINT(2121000 6021000)"))
    layer.dataProvider().addFeatures([feature])
    layer = to_geopackage(layer, str(tmp_path / "trees.gpkg"))
    big = QgsSimpleMarkerSymbolLayer(size=6, color=QColor(0, 120, 0))
    big.setStrokeStyle(0)  # Qt.NoPen
    small = QgsSimpleMarkerSymbolLayer(size=2, color=QColor(200, 0, 0))
    small.setStrokeStyle(0)
    small.setOffset(QPointF(4, 0))  # sticks out of the big circle on the right
    symbol = QgsMarkerSymbol([big, small])
    buffer = QgsSymbolBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(1)
    buffer.setFillSymbol(QgsFillSymbol.createSimple({"color": "255,255,255,255", "outline_style": "no"}))
    symbol.setBufferSettings(buffer)
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    return layer


def test_the_buffer_is_drawn_once_under_the_whole_symbol(export, tmp_path):  # noqa: F811
    _, result = export(_buffered_points(tmp_path))
    style = json.load(open(os.path.join(result, "style", "style.json"), encoding="utf-8"))
    icons = [layer for layer in style["layers"] if "icon-image" in layer.get("layout", {})]
    assert len(icons) == 3, [layer["id"] for layer in icons]  # buffer, big, small
    index = json.load(open(os.path.join(result, "style", "sprite", "sprite.json"), encoding="utf-8"))
    sheet = QImage(os.path.join(result, "style", "sprite", "sprite.png"))
    entries = [index[layer["layout"]["icon-image"]] for layer in icons]
    widths = [entry["width"] / entry["pixelRatio"] for entry in entries]
    # Bottom first: the buffer, wider than the symbol (1 mm each side), then
    # the layers without a buffer of their own (the big circle: 6 mm).
    mm = 96 / 25.4
    # Cropped symmetrically about the point: the small circle reaches 4 + 1 mm
    # to the right, the buffer 1 mm more: 2 x 6 mm.
    assert widths[0] == pytest.approx(12 * mm, abs=3)
    big = entries[1]
    assert big["width"] / big["pixelRatio"] == pytest.approx(6 * mm, abs=2)
    # The buffer's image is white where the symbol is not (its edge).
    buffer = entries[0]
    edge = sheet.pixelColor(buffer["x"] + buffer["width"] // 2, buffer["y"] + int(0.5 * mm * buffer["pixelRatio"]))
    assert edge.alpha() > 200 and min(edge.red(), edge.green(), edge.blue()) > 230


def test_a_font_marker_drawn_as_text_gets_its_buffer_as_a_halo(export, tmp_path):  # noqa: F811
    """A cluster's count style: a font marker with a symbol buffer."""
    from qgis.core import QgsFontMarkerSymbolLayer, QgsSymbolBufferSettings  # pylint: disable=import-outside-toplevel
    layer = _buffered_points(tmp_path)
    font = QgsFontMarkerSymbolLayer("DejaVu Sans", "7", 4, QColor(0, 0, 0))
    font.setStrokeWidth(0)
    symbol = QgsMarkerSymbol([font])
    buffer = QgsSymbolBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(0.5)
    buffer.setFillSymbol(QgsFillSymbol.createSimple({"color": "255,255,0,255", "outline_style": "no"}))
    symbol.setBufferSettings(buffer)
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    _, result = export(layer)
    style = json.load(open(os.path.join(result, "style", "style.json"), encoding="utf-8"))
    texts = [layer for layer in style["layers"] if layer.get("layout", {}).get("text-field") == "7"]
    assert texts and texts[0]["paint"]["text-halo-color"].startswith("rgba(255, 255, 0")
    assert texts[0]["paint"]["text-halo-width"] == pytest.approx(0.5 * 96 / 25.4, rel=0.05)
