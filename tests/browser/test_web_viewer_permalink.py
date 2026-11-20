"""permalink.mjs: a near-full drawing plus much other state (many switched
layers) is still a valid link (the whole link used to be dropped over 24000
characters, the drawing with it); an oversized state loses its longest
lists, not the camera."""

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


def test_oversized_state_drops_its_longest_lists_not_the_whole_link():
    # 3000 switched layers (about 33000 characters): the layer list is left
    # out; the camera and the drawing stay (the default view opened before).
    out = _run(3000, 10)
    assert out == {"length": out["length"], "drawing": 10, "layers": 0, "zoom": 10}


def test_many_switched_rules_keep_camera_selection_and_short_lists():
    script = f"""
import * as p from {json.dumps('file://' + MODULE)};
const manifest = {{ layers: [{{ id: "parcels" }}, {{ id: "roads" }}], groups: [],
  rules: Array.from({{ length: 1100 }}, (_, i) => ({{ id: "rule-" + String(i).padStart(20, "0") }})) }};
const defaults = {{ layers: {{ parcels: true, roads: true }}, groups: {{}},
  rules: Object.fromEntries(manifest.rules.map((r) => [r.id, true])), opacity: {{}}, basemap: null }};
const value = {{ layers: {{ parcels: true, roads: false }}, groups: {{}},
  rules: Object.fromEntries(manifest.rules.map((r) => [r.id, false])), opacity: {{}}, labels: true,
  selected: {{ layerId: "parcels", key: "12/3" }} }};
const hash = p.encodeState(manifest, value, {{ zoom: 15, lat: 47.5, lng: 19.05 }}, defaults);
const out = p.decodeState(manifest, "#" + hash);
console.log(JSON.stringify({{ length: hash.length, camera: out.camera, selected: out.selected,
  layers: out.layers, rules: Object.keys(out.rules).length }}));
"""
    run = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, check=True)
    out = json.loads(run.stdout)
    assert out["length"] > 24000
    assert out["camera"] == {"zoom": 15, "lat": 47.5, "lng": 19.05}
    assert out["selected"] == {"layerId": "parcels", "key": "12/3"}
    assert out["layers"] == {"roads": False} and out["rules"] == 0


def test_shared_filter_with_more_than_200_values_opens_as_it_was():
    state = os.path.join(ROOT, "resources", "web_viewer", "state.mjs")
    script = f"""
import * as p from {json.dumps('file://' + MODULE)};
import {{ sanitizeFilters }} from {json.dumps('file://' + state)};
const values = Array.from({{ length: 300 }}, (_, i) => "value " + i);
const manifest = {{ layers: [{{ id: "parcels", filterFields: [{{ field: "use", kind: "values",
  values: values.map((v) => [v, 1]) }}] }}], groups: [], rules: [] }};
const defaults = {{ layers: {{ parcels: true }}, groups: {{}}, rules: {{}}, opacity: {{}}, basemap: null }};
const value = {{ layers: {{ parcels: true }}, groups: {{}}, rules: {{}}, opacity: {{}}, labels: true,
  filters: {{ parcels: {{ use: {{ values, nulls: false }} }} }} }};
const out = p.decodeState(manifest, "#" + p.encodeState(manifest, value, null, defaults));
console.log(JSON.stringify(sanitizeFilters(manifest, out.filters).parcels.use.values.length));
"""
    run = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, check=True)
    assert json.loads(run.stdout) == 300
