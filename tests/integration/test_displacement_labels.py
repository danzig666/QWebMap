"""A point displacement renderer's own labels in the web style: a text layer
of the label attribute in the renderer's font and colour, anchored per
point (idea of QGIS2VectorTiles 4.1)."""

import json
import os
import sys

from qgis.core import QgsMarkerSymbol, QgsPointDisplacementRenderer, QgsSingleSymbolRenderer
from qgis.PyQt.QtGui import QColor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_end_to_end import export  # noqa: E402,F401  pylint: disable=wrong-import-position,unused-import
from test_materialize import _layer  # noqa: E402  pylint: disable=wrong-import-position

# A cluster of five, a pair and a lone point in the export extent (m).
POINTS = [f"POINT({2120000 + dx} {6020000 + dy})" for dx, dy in
          ((0, 0), (3, 0), (0, 3), (-3, 0), (0, -3), (500, 500), (503, 500), (1500, 1500))]


def test_displacement_labels_become_a_text_layer(export, tmp_path):  # noqa: F811
    layer = _layer("Point", POINTS, str(tmp_path / "pts.gpkg"))
    renderer = QgsPointDisplacementRenderer("id")
    renderer.setLabelColor(QColor(200, 0, 0))
    renderer.setEmbeddedRenderer(QgsSingleSymbolRenderer(
        QgsMarkerSymbol.createSimple({"name": "circle", "size": "2", "color": "#2b83ba"})))
    layer.setRenderer(renderer)
    _, result = export(layer, min_zoom=15, max_zoom=17)
    style = json.load(open(os.path.join(result, "style", "style.json"), encoding="utf-8"))
    texts = [layer for layer in style["layers"]
             if json.dumps(layer.get("layout", {}).get("text-field", "")).find('"id"') >= 0]
    assert texts, [layer["id"] for layer in style["layers"]]
    assert texts[0]["paint"]["text-color"] == "rgba(200, 0, 0, 1.0)"
    assert "q2vt_label_anchor" in json.dumps(texts[0]["layout"]["text-anchor"])
    # The tiles carry the label text and its anchor.
    import sqlite3
    from publishing import mvt
    seen = set()
    with sqlite3.connect(os.path.join(result, "tiles.mbtiles")) as conn:
        for (data,) in conn.execute("SELECT tile_data FROM tiles"):
            for name, tile_layer in mvt.decode(data).items():
                if name == texts[0]["source-layer"]:
                    for feature in tile_layer["features"]:
                        seen.add((feature["properties"].get("id"), feature["properties"].get("q2vt_label_anchor")))
    assert len({id_ for id_, _ in seen}) == len(POINTS) and all(anchor for _, anchor in seen), seen
