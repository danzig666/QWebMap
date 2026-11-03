"""How a dense vector layer is drawn zoomed out (LayerConfig.zoomed_out):
"image" - rendered by QGIS below a zoom, its features tiled from that zoom
on, its labels kept; "merged" - its fills joined per tile below the zoom."""

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


def _export(tmp_path, mode):
    from publishing import mvt
    os.makedirs(tmp_path, exist_ok=True)
    project = reset_project()
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    project.addMapLayer(parcels)
    profile = _profile(parcels, tmp_path)  # zooms 11-13, labelled parcels
    profile.layers[0].zoomed_out, profile.layers[0].zoomed_out_below = mode, 13
    result = export_local(project, profile, EXTENT)
    release = result.release.release_dir
    manifest = json.load(open(os.path.join(release, "manifest.json"), encoding="utf-8"))
    style = json.load(open(os.path.join(release, "style.json"), encoding="utf-8"))
    names = {}
    with open_pmtiles(os.path.join(release, "data", "map.pmtiles")) as archive:
        for (z, _x, _y), data in archive.tiles():
            for name, layer in mvt.decode(data).items():
                names.setdefault(z, {}).setdefault(name, 0)
                names[z][name] += len(layer["features"])
    return manifest, style, names, release


def test_image_mode_draws_qgis_images_below_the_zoom(plugin, tmp_path):
    manifest, style, names, release = _export(tmp_path, "image")
    layer = manifest["layers"][0]
    image = next(c for c in manifest["components"] if c["role"] == "image")
    assert image["id"] in layer["componentIds"] and image["layerId"] == layer["id"]
    source = next(s for s in manifest["sources"] if s["id"] == image["sourceId"])
    assert source["role"] == "raster" and source["maxTileZoom"] == 12
    assert os.path.getsize(os.path.join(release, source["href"])) > 1000
    ids = [l["id"] for l in style["layers"]]
    raster = style["layers"][ids.index(image["styleLayerIds"][0])]
    assert raster["type"] == "raster" and raster["maxzoom"] == 13
    labels = [c for c in manifest["components"] if c["role"] == "label"]
    fills = [c for c in manifest["components"] if c["role"] not in ("label", "image", "callout")]
    # At the layer's place: under its labels.
    assert all(ids.index(raster["id"]) < ids.index(i) for c in labels for i in c["styleLayerIds"] if i in ids)
    # Its features only from zoom 13 on; its labels at every zoom.
    fill_sources = {l.get("source-layer") for l in style["layers"]
                    if l["id"] in {i for c in fills for i in c["styleLayerIds"]}} - {None}
    label_sources = {l.get("source-layer") for l in style["layers"]
                     if l["id"] in {i for c in labels for i in c["styleLayerIds"]}} - {None}
    assert fill_sources and label_sources
    below = {n for z, by in names.items() if z < 13 for n in by}
    assert not fill_sources & below and fill_sources <= set(names[13])
    # The labels as without images (the same datasets at the same zooms).
    _, plain_style, plain, _ = _export(tmp_path / "plain", "full")
    plain_fills = {l.get("source-layer") for l in plain_style["layers"] if l.get("type") == "fill"} - {None}
    assert {n for z, by in plain.items() if z < 13 for n in by} & plain_fills  # drawn below 13 without
    for z in plain:
        assert {n: c for n, c in plain[z].items() if n in label_sources} == \
            {n: c for n, c in names.get(z, {}).items() if n in label_sources}, z


def test_merged_mode_tiles_the_fills_from_merged_copies_below_the_zoom(plugin, tmp_path):
    """Merged (the joining itself: test_export_speed): below the zoom the
    fills come from the merged copies (one feature per style and tile, no
    feature ids), from it on every feature with its id; the layer's labels
    keep a polygon copy of their own (no merged fills to place them on)."""
    from publishing import mvt
    manifest, style, names, release = _export(tmp_path, "merged")
    assert not [c for c in manifest["components"] if c["role"] == "image"]
    fills = {l.get("source-layer") for l in style["layers"] if l.get("type") == "fill"} - {None}
    assert fills
    ids = {}
    with open_pmtiles(os.path.join(release, "data", "map.pmtiles")) as archive:
        for (z, _x, _y), data in archive.tiles():
            for name, layer in mvt.decode(data).items():
                if name in fills:
                    ids.setdefault(z, set()).update("q2vt_orig_id" in f["properties"] for f in layer["features"])
    assert ids[11] == {False} and ids[12] == {False} and ids[13] == {True}
    assert any(name.endswith("_vp") for z in names for name in names[z])
