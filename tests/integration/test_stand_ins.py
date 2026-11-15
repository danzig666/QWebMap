"""No blank map on a fast zoom-in: a layer first appearing at zoom N is also
in the tiles of N - 1 (stand-in data), its published style layers parsed
from them but invisible below N (core.fidelity.zoom.stand_in_zooms,
publishing.zoom_bridge)."""

import json
import os
import sys

from qgis.core import QgsRectangle

from publishing.controller import export_local
from publishing.validation import open_pmtiles
from q2vt_fixtures import reset_project

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_publishing_pipeline import _parcels, _profile  # noqa: E402  pylint: disable=wrong-import-position

EXTENT = QgsRectangle(2119000, 6019000, 2123000, 6023000)


def _export(tmp_path, zoomed_out=None):
    from publishing import mvt
    from publishing.models import LayerConfig
    from fidelity.zoom import zoom_to_scale
    os.makedirs(tmp_path, exist_ok=True)
    project = reset_project()
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    buildings = _parcels(str(tmp_path / "buildings.gpkg"))
    buildings.setName("Épületek")
    buildings.setScaleBasedVisibility(True)
    buildings.setMinimumScale(zoom_to_scale(13))      # from zoom 13 on
    buildings.setMaximumScale(1.0)
    for layer in (parcels, buildings):
        project.addMapLayer(layer)
    profile = _profile(parcels, tmp_path)               # zooms 11-13
    profile.layers.append(LayerConfig(buildings.id()))
    if zoomed_out:
        profile.layers[1].zoomed_out, profile.layers[1].zoomed_out_below = zoomed_out, 13
    result = export_local(project, profile, EXTENT)
    release = result.release.release_dir
    style = json.load(open(os.path.join(release, "style.json"), encoding="utf-8"))
    manifest = json.load(open(os.path.join(release, "manifest.json"), encoding="utf-8"))
    names = {}
    path = os.path.join(release, "data", "map.pmtiles")
    with open_pmtiles(path) as archive:
        for (z, _x, _y), data in archive.tiles():
            for name in mvt.decode(data):
                names.setdefault(z, set()).add(name)
    owned = {i: c["layerId"] for c in manifest["components"] for i in c["styleLayerIds"]}
    by_layer = {}
    for layer_def in style["layers"]:
        if layer_def["id"] in owned and layer_def.get("source-layer"):
            by_layer.setdefault(owned[layer_def["id"]], []).append(layer_def)
    title = {l["id"]: l.get("title") for l in manifest["layers"]}
    first, later = (next(defs for lid, defs in by_layer.items() if title[lid] != "Épületek"),
                    next(defs for lid, defs in by_layer.items() if title[lid] == "Épületek"))
    return first, later, names, os.path.getsize(path)


def test_a_layer_first_appearing_at_a_zoom_has_stand_ins_one_zoom_below(plugin, tmp_path):
    parcels, buildings, names, size = _export(tmp_path)
    # (Its polygon labels are placed by the viewer itself: none.)
    placed = [l for l in buildings if "q2vt:visible-polygons" in l.get("metadata", {})]
    buildings = [l for l in buildings if l not in placed]
    sources = {l["source-layer"] for l in buildings}
    assert sources and sources <= names[13] and sources <= names[12] and not sources & names[11]
    assert all(l["minzoom"] == 13 and l["source-layer"] not in names[12] for l in placed)
    for layer_def in buildings:
        assert layer_def["minzoom"] == 12 and layer_def["metadata"]["q2vt:hidden-below"] == 13
        assert layer_def["metadata"]["q2vt:zooms"][0] == 13
        props = {"fill": ["fill-opacity"], "line": ["line-opacity"],
                 "symbol": ["text-opacity", "icon-opacity"]}.get(layer_def["type"], [])
        for prop in props:
            value = layer_def["paint"][prop]
            assert value[:4] in (["step", ["zoom"], 0, 13], ["interpolate", value[1], ["zoom"], 12.999]), value
    # The layer of the first zoom: as it was.
    assert all("q2vt:hidden-below" not in l.get("metadata", {}) for l in parcels)
    print("ARCHIVE", size)


def test_no_stand_ins_for_a_layer_drawn_as_images_zoomed_out(plugin, tmp_path):
    """"image": the layer's features are left out of the lower tiles on purpose."""
    _parcels_layers, buildings, names, _ = _export(tmp_path, zoomed_out="image")
    sources = {l["source-layer"] for l in buildings if l["type"] != "symbol"}
    assert sources and not sources & names.get(12, set())
    assert all("q2vt:hidden-below" not in l.get("metadata", {}) for l in buildings if l["type"] != "symbol")
