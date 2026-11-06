"""style_control.mjs: the attribute filters drawn by MapLibre (filterPredicate)
and the ones the popups and labels use (matchesFilters) agree, NULL and
missing values included (MapLibre's to-number/to-string turn NULL into 0 /
"", which used to keep NULL features drawn under a range filter)."""

import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODULE = os.path.join(ROOT, "resources", "web_viewer", "style_control.mjs")
SPEC = os.path.join(ROOT, "tests", "browser", "node_modules", "@maplibre", "maplibre-gl-style-spec",
                    "dist", "index.mjs")

pytestmark = pytest.mark.skipif(shutil.which("node") is None or not os.path.exists(SPEC),
                                reason="needs Node and the MapLibre style spec")

FILTERS = [
    {"area": {"max": 100}},
    {"area": {"min": 0}},
    {"area": {"min": 10, "max": 50}},
    {"area": {"min": None, "max": None}},
    {"kind": {"values": [""]}},
    {"kind": {"values": ["a", "5"]}},
    {"kind": {"values": ["a"], "nulls": True}},
    {"kind": {"values": [], "nulls": True}},
    {"name": {"text": "ab"}},
]
FEATURES = [{}, {"area": None, "kind": None}, {"area": 0, "kind": ""}, {"area": 20, "kind": "a"},
            {"area": 200, "kind": 5}, {"area": "x", "kind": "b", "name": "Abc"}, {"area": "30"}]


def test_drawn_and_popup_filters_agree():
    script = f"""
import * as s from {json.dumps('file://' + MODULE)};
import {{ featureFilter }} from {json.dumps('file://' + SPEC)};
const layer = {{ id: "L", filterFields: [
  {{ field: "area", kind: "range" }}, {{ field: "kind", kind: "values" }}, {{ field: "name", kind: "text" }}] }};
const out = [];
for (const filter of {json.dumps(FILTERS)}) {{
  const predicate = s.filterPredicate(layer, {{ L: filter }});
  const drawn = predicate ? featureFilter(predicate, "layers[0].filter") : null;
  for (const properties of {json.dumps(FEATURES)}) {{
    const map = drawn ? drawn.filter({{ zoom: 10 }}, {{ type: 1, properties }}) : true;
    out.push({{ filter, properties, map, popup: s.matchesFilters(layer, filter, properties) }});
  }}
}}
console.log(JSON.stringify(out));
"""
    run = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, check=True)
    differ = [row for row in json.loads(run.stdout) if row["map"] != row["popup"]]
    assert not differ
