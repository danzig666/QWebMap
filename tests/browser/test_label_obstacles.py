"""Point symbols as label obstacles in the published viewer (MapLibre's own
placement): the labels of one point layer, at the same places as the stars
of another layer whose labeling makes its features obstacles (here an
obstacle-only labeling, QGIS "blocking"), are kept off the stars: every
spot round their tiny dots is on a star. With "Features act as obstacles"
off, they are drawn. A layer's own labels are never kept off its own
symbols (QGIS: a feature is no obstacle to its own label)."""

import json
import os
import subprocess
import sys

from qgis.core import (QgsFeature, QgsField, QgsGeometry, QgsMarkerSymbol, QgsPalLayerSettings,
                       QgsRectangle, QgsSingleSymbolRenderer, QgsTextFormat, QgsVectorLayer,
                       QgsVectorLayerSimpleLabeling)
from qgis.PyQt.QtCore import QVariant

from publishing.controller import export_local
from publishing.models import LayerConfig, PublicationProfile
from publishing.preview_server import PreviewServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from q2vt_fixtures import reset_project, to_geopackage  # noqa: E402  pylint: disable=wrong-import-position

EXTENT = QgsRectangle(2119000, 6019000, 2123000, 6023000)
PLACES = [(2119500 + 1000 * i, 6019500 + 1000 * j) for i in range(4) for j in range(4)]
STAR = {"name": "star", "color": "200,0,0", "size": "9"}
DOT = {"name": "circle", "color": "0,0,200", "size": "0.4", "outline_style": "no"}


def _points(path, name, symbol_props, obstacle, draw_labels=True):
    layer = QgsVectorLayer("Point?crs=EPSG:3857", name, "memory")
    layer.dataProvider().addAttributes([QgsField("name", QVariant.String)])
    layer.updateFields()
    features = []
    for i, (x, y) in enumerate(PLACES):
        feature = QgsFeature(layer.fields())
        feature.setAttributes([f"{name[0].upper()}{i}"])
        feature.setGeometry(QgsGeometry.fromWkt(f"POINT({x} {y})"))
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    layer = to_geopackage(layer, path)
    layer.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple(symbol_props)))
    settings = QgsPalLayerSettings()
    settings.fieldName = "name"
    text = QgsTextFormat()
    text.setSize(9)
    settings.setFormat(text)
    settings.obstacleSettings().setIsObstacle(obstacle)
    settings.drawLabels = draw_labels
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)
    return layer


def _drawn_labels(base, slug, layers):
    project = reset_project(*layers)
    profile = PublicationProfile(title="Obstacles", slug=slug, locale="en")
    profile.view.min_zoom, profile.view.max_zoom = 13, 14
    profile.output.local_directory = str(base / "out")
    profile.layers = [LayerConfig(layer.id(), initially_visible=True) for layer in layers]
    result = export_local(project, profile, EXTENT)
    actions = [{"eval": """
      const map = q2vtViewer.map;
      map.jumpTo({zoom: 14.5});
      await new Promise((r) => { map.once('idle', r); map.triggerRepaint(); setTimeout(r, 8000); });
      const ids = map.getStyle().layers.filter((l) => l.type === 'symbol' && l.layout && l.layout['text-field'])
        .map((l) => l.id);
      const names = map.queryRenderedFeatures({layers: ids}).map((f) => String(f.properties.q2vt_label));
      const obstacles = map.getStyle().layers.filter((l) => (l.metadata || {})['q2vt:obstacle-of']).length;
      return {names: [...new Set(names)], obstacles};"""}]
    path = base / "actions.json"
    path.write_text(json.dumps(actions))
    with PreviewServer(os.path.dirname(result.publication_dir)) as server:
        run = subprocess.run(["node", "interact.mjs", server.url(f"{slug}/index.html"), str(path), "1000", "1000"],
                             capture_output=True, text=True, cwd=HERE, timeout=300)
    assert run.returncode == 0, run.stderr[-3000:]
    out = json.loads(run.stdout.strip().splitlines()[-1])
    assert not out["pageErrors"], out
    return out["results"][0]


def test_labels_keep_off_the_symbols_of_an_obstacle_layer(tmp_path):
    seen = {}
    for obstacle in (True, False):
        base = tmp_path / f"o{int(obstacle)}"
        base.mkdir()
        stars = _points(str(base / "stars.gpkg"), "stars", STAR, obstacle, draw_labels=False)
        dots = _points(str(base / "dots.gpkg"), "dots", DOT, False)
        seen[obstacle] = _drawn_labels(base, f"obstacles-{int(obstacle)}", [dots, stars])
    shown = {o: {n for n in seen[o]["names"] if n.startswith("D")} for o in seen}
    assert seen[True]["obstacles"] and not seen[False]["obstacles"], seen
    assert len(shown[False]) == len(PLACES) and len(shown[True]) < len(PLACES) / 2, seen


def test_a_layers_own_labels_are_not_kept_off_its_symbols(tmp_path):
    stars = _points(str(tmp_path / "stars.gpkg"), "stars", STAR, True)
    seen = _drawn_labels(tmp_path, "own-labels", [stars])
    assert seen["obstacles"] and len([n for n in seen["names"] if n.startswith("S")]) == len(PLACES), seen
