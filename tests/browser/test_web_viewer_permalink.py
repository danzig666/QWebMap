"""permalink.mjs: a near-full drawing plus much other state (many switched
layers) is still a valid link (the whole link used to be dropped over 24000
characters, the drawing with it); an oversized state is still refused."""

import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODULE = os.path.join(ROOT, "resources", "web_viewer", "permalink.mjs")

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="needs Node")


def _run(layers, drawing):
    script = f"""
import * as p from {json.dumps('file://' + MODULE)};
const manifest = {{ layers: Array.from({{ length: {layers} }}, (_, i) => ({{ id: "layer_" + i }})), groups: [], rules: [] }};
const defaults = {{ layers: Object.fromEntries(manifest.layers.map((l) => [l.id, true])), groups: {{}}, rules: {{}},
  opacity: {{}}, basemap: null }};
const value = {{ layers: Object.fromEntries(manifest.layers.map((l) => [l.id, false])), groups: {{}}, rules: {{}},
  opacity: {{}}, labels: true, drawing: "A".repeat({drawing}) }};
const hash = p.encodeState(manifest, value, {{ zoom: 10, lat: 47, lng: 19 }}, defaults);
const out = p.decodeState(manifest, "#" + hash);
console.log(JSON.stringify({{ length: hash.length, drawing: out && out.drawing.length,
  layers: out && Object.keys(out.layers).length, zoom: out && out.camera.zoom }}));
"""
    run = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, check=True)
    return json.loads(run.stdout)


def test_long_drawing_with_much_state_is_kept():
    out = _run(800, 15900)
    assert out["length"] > 24000
    assert out == {"length": out["length"], "drawing": 15900, "layers": 800, "zoom": 10}


def test_oversized_state_is_refused():
    assert _run(3000, 10)["drawing"] is None
