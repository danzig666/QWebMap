"""The view bar marks the active view only while the layers shown are the
view's: switching a whole group off left the view marked (groups were not
compared; a view turns every group on)."""

import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(os.path.dirname(os.path.dirname(HERE)), "resources", "web_viewer", "state.mjs")

SCRIPT = """
import { applyPreset, defaults, presetMatches } from %s;
const manifest = { layers: [{ id: "a", groupId: "g" }, { id: "b" }], groups: [{ id: "g" }], rules: [],
  themes: { presets: [{ id: "v", title: "View", layers: { a: true, b: false }, groups: { g: true }, rules: {} }] } };
const preset = manifest.themes.presets[0];
const on = applyPreset(manifest, defaults(manifest), preset);
const out = {
  picked: presetMatches(manifest, on, preset),
  layerOff: presetMatches(manifest, { ...on, layers: { ...on.layers, a: false } }, preset),
  groupOff: presetMatches(manifest, { ...on, groups: { ...on.groups, g: false } }, preset),
  groupBackOn: presetMatches(manifest, { ...on, groups: { ...on.groups, g: true } }, preset),
};
console.log(JSON.stringify(out));
"""


def test_switching_a_group_off_unmarks_the_view():
    url = "file://" + STATE.replace(os.sep, "/")
    run = subprocess.run(["node", "--input-type=module", "-e", SCRIPT % json.dumps(url)],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr[-2000:]
    out = json.loads(run.stdout.strip().splitlines()[-1])
    assert out == {"picked": True, "layerOff": False, "groupOff": False, "groupBackOn": True}, out
