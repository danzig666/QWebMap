"""No blank map on a fast zoom-in: a layer first appearing at zoom 13 is
drawn at once on a jump to 13.x, from the zoom-12 tiles MapLibre shows while
those of 13 load (stand-in data), and is not drawn below 13."""

import json
import math
import os
import subprocess

import pytest
from qgis.core import QgsFeature, QgsFillSymbol, QgsGeometry, QgsRectangle, QgsSingleSymbolRenderer, QgsVectorLayer
from qgis.PyQt.QtGui import QColor

from publishing.controller import export_local
from publishing.models import LayerConfig, PublicationProfile
from publishing.preview_server import PreviewServer

HERE = os.path.dirname(os.path.abspath(__file__))
# Large: the start view (fitted to it) is at zoom 11, no tile of 13 loaded before the jump.
EXTENT = QgsRectangle(2090000, 5990000, 2150000, 6050000)
SQUARE = QgsRectangle(2120500, 6020500, 2121500, 6021500)
R = 6378137.0


def _lnglat(x, y):
    return [math.degrees(x / R), math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2)]


def _layer(name, rect, color, from_zoom=None):
    from fidelity.zoom import zoom_to_scale
    layer = QgsVectorLayer("Polygon?crs=EPSG:3857", name, "memory")
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromRect(rect))
    layer.dataProvider().addFeatures([feature])
    layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": color, "outline_style": "no"})))
    if from_zoom is not None:
        layer.setScaleBasedVisibility(True)
        layer.setMinimumScale(zoom_to_scale(from_zoom))
        layer.setMaximumScale(1.0)
    return layer


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    from q2vt_fixtures import reset_project
    base = tmp_path_factory.mktemp("standins")
    # A small layer from the first zoom on (the archive starts at 11), the square from 13.
    corner = _layer("Corner", QgsRectangle(2119100, 6019100, 2119200, 6019200), "0,255,0,255")
    square = _layer("Square", SQUARE, "0,0,255,255", from_zoom=13)
    project = reset_project(corner, square)
    project.setBackgroundColor(QColor(255, 255, 0))
    profile = PublicationProfile(title="Stand-ins", slug="standins", locale="en")
    profile.view.min_zoom, profile.view.max_zoom = 11, 15
    profile.output.local_directory = str(base / "out")
    profile.layers = [LayerConfig(corner.id(), initially_visible=True),
                      LayerConfig(square.id(), initially_visible=True)]
    result = export_local(project, profile, EXTENT)
    with PreviewServer(os.path.dirname(result.publication_dir)) as server:
        yield {"url": server.url(f"{profile.slug}/index.html")}


def _run(url, actions, tmp_path):
    path = tmp_path / "actions.json"
    path.write_text(json.dumps(actions))
    run = subprocess.run(["node", "interact.mjs", url, str(path), "800", "600"],
                         capture_output=True, text=True, cwd=HERE, timeout=600)
    assert run.returncode == 0, run.stderr[-3000:]
    out = json.loads(run.stdout.strip().splitlines()[-1])
    assert not out["pageErrors"], out
    return out["results"]


# The centre pixel, drawn now (before any tile still loading has arrived).
PIXEL = """const m = q2vtViewer.map; m.redraw();
  const gl = m.getCanvas().getContext('webgl2') || m.getCanvas().getContext('webgl');
  const px = new Uint8Array(4);
  gl.readPixels(gl.drawingBufferWidth >> 1, gl.drawingBufferHeight >> 1, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
  return { zoom: m.getZoom(), px: Array.from(px),
           loaded: Object.values(m.style.tileManagers || m.style.sourceCaches).flatMap((c) => c.getRenderableIds().map((id) => c.getTileByID(id).tileID.canonical.z)) };"""


def test_a_layer_starting_at_13_is_drawn_from_the_tiles_of_12_on_a_jump(site, tmp_path):
    centre = json.dumps(_lnglat(SQUARE.center().x(), SQUARE.center().y()))
    actions = [
        {"eval": f"q2vtViewer.map.jumpTo({{center: {centre}, zoom: 12.5}}); return 1;"}, {"idle": True},
        {"eval": PIXEL},                                    # 12.5: not yet (QGIS: from 13)
        {"eval": f"q2vtViewer.map.jumpTo({{center: {centre}, zoom: 13.4}}); " + PIXEL},
        {"idle": True}, {"eval": PIXEL},                    # 13.4 with its own tiles
    ]
    below, jumped, settled = [r for r in _run(site["url"], actions, tmp_path) if r != 1]
    assert below["px"] == [255, 255, 0, 255], below
    # Right after the jump only the tiles of 12 are there, and they draw it.
    assert 13 not in jumped["loaded"] and jumped["px"] == [0, 0, 255, 255], jumped
    assert settled["px"] == [0, 0, 255, 255] and 13 in settled["loaded"], settled


def test_stand_in_styles_are_valid_maplibre_styles(tmp_path):
    """Stepped opacities (numbers, data, zoom curves) and the stepped label
    placement pass MapLibre's style validator."""
    from publishing.zoom_bridge import bridge_zoom_bands

    def layer(name, kind, **extra):
        return {"id": name, "type": kind, "source": "q2vt_tiles", "source-layer": name,
                "minzoom": 13, "maxzoom": 18, "metadata": {"q2vt:tiles": [12, 18]}, **extra}
    style = {"version": 8, "glyphs": "glyphs/{fontstack}/{range}.pbf",
             "sources": {"q2vt_tiles": {"type": "vector", "tiles": ["x/{z}/{x}/{y}"]}},
             "metadata": {"q2vt:tiles-max-zoom": 18},
             "layers": [
                 layer("fill", "fill", paint={"fill-color": "#f00", "fill-opacity": 0.5}),
                 layer("line", "line", paint={"line-opacity": ["interpolate", ["linear"], ["zoom"], 12, 0.2, 14, 1]}),
                 layer("circle", "circle", paint={"circle-opacity": ["get", "a"]}),
                 layer("label", "symbol", layout={"text-field": "x", "text-font": ["Noto Sans Regular"]},
                       paint={"text-opacity": ["step", ["zoom"], 0.3, 12.5, 0.6, 15, 1]}),
                 layer("icons", "symbol", layout={"icon-image": "a", "icon-allow-overlap": True},
                       paint={"icon-opacity": ["coalesce", ["get", "o"], 1]})]}
    bridge_zoom_bands(style)
    assert all(l["minzoom"] == 12 for l in style["layers"])
    path = tmp_path / "style.json"
    path.write_text(json.dumps(style))
    run = subprocess.run(["node", "validate_style.mjs", str(path)], capture_output=True, text=True, cwd=HERE)
    assert run.returncode == 0, run.stdout + run.stderr
