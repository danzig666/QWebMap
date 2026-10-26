"""A web map of raster layers only (QGIS-rendered and live, no vector
layer): no vector tile export, a release without a vector archive (no
vector source in the style or the manifest), which validates as any other;
the layer list, themes and zoom-to-layer still describe the raster layers.
Nothing to publish, or a parcel report without a parcel layer, is still
refused with a clear message."""

import json
import os
import sys

import pytest
from qgis.core import QgsMapThemeCollection, QgsRasterLayer

from publishing.controller import export_local
from publishing.errors import PublishingError
from publishing.models import GroupConfig, LayerConfig, PublicationProfile
from publishing.provenance import layer_logical_id
from publishing.validation import validate_pmtiles, vector_only_violations
from publishing.web_builder import validate_release_dir
from q2vt_fixtures import reset_project

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_publishing_raster import EXTENT, _validate_manifest, make_raster  # noqa: E402  pylint: disable=wrong-import-position

TILES = "https://tiles.example.test/{z}/{x}/{y}.png"


def _model(project):
    from qgis.core import QgsLayerTreeModel  # pylint: disable=import-outside-toplevel
    return QgsLayerTreeModel(project.layerTreeRoot())


def raster_only_project(tmp_path, live=True, local=True):
    """A project of a local raster (in a group) and a live XYZ web layer,
    with a theme showing the web layer only; its profile publishes both."""
    project = reset_project()
    root = project.layerTreeRoot()
    profile = PublicationProfile(title="Ortofotó térkép", slug="ortofoto", locale="hu")
    profile.view.min_zoom, profile.view.max_zoom = 11, 13
    profile.output.local_directory = str(tmp_path / "Kimenet")
    profile.interaction.zoom_to_layer = True
    layers = {}
    if live:
        web = QgsRasterLayer(f"type=xyz&url={TILES}&zmin=0&zmax=19", "Webes térkép", "wms")
        assert web.isValid()
        project.addMapLayer(web, False)
        root.addLayer(web)
        profile.layers.append(LayerConfig(web.id(), initially_visible=False, raster_max_zoom=15))
        layers["web"] = web
    if local:
        ortho = QgsRasterLayer(make_raster(tmp_path / "ortho.tif"), "Ortofotó")
        assert ortho.isValid()
        project.addMapLayer(ortho, False)
        root.addGroup("Légifotók").addLayer(ortho)
        profile.layers.append(LayerConfig(ortho.id(), raster_format="png", raster_max_zoom=14, opacity=0.8))
        profile.groups = [GroupConfig(["Légifotók"])]
        layers["ortho"] = ortho
    if live and local:
        root.findLayer(layers["ortho"].id()).setItemVisibilityChecked(False)
        project.mapThemeCollection().insert("Csak web", QgsMapThemeCollection.createThemeFromCurrentState(
            root, _model(project)))
        root.findLayer(layers["ortho"].id()).setItemVisibilityChecked(True)
        profile.themes.names = ["Csak web"]
    return project, profile, layers


def _read(release, name):
    with open(os.path.join(release, name), encoding="utf-8") as handle:
        return json.load(handle)


def test_raster_only_map_is_published_without_vector_tiles(tmp_path):
    project, profile, layers = raster_only_project(tmp_path)
    result = export_local(project, profile, EXTENT)
    # No vector tile export ran: its work folder holds the raster archives
    # and the raster-only export folder (records, legend) only.
    work = os.path.dirname(result.export_dir)
    assert os.path.basename(result.export_dir) == "raster-only"
    assert sorted(os.listdir(work)) == ["raster-only", "rasters"]
    release = result.release.release_dir
    manifest = _read(release, "manifest.json")
    _validate_manifest(manifest)
    style = _read(release, "style.json")
    ortho, web = layer_logical_id(layers["ortho"].id()), layer_logical_id(layers["web"].id())
    # No vector archive and no vector source: only the ortho's image archive.
    files = {item["path"] for item in result.release.files}
    assert "data/map.pmtiles" not in files and not any(p.startswith("data/tiles/") for p in files)
    assert [s.get("role") for s in manifest["sources"]] == ["raster"]
    assert manifest["sources"][0]["layerId"] == ortho and manifest["sources"][0]["tileType"] == "png"
    validate_pmtiles(os.path.join(release, manifest["sources"][0]["href"]), sample=0, kind="image")
    assert [live["layerId"] for live in manifest["liveRasters"]] == [web]
    assert all(source["type"] == "raster" for source in style["sources"].values())
    assert {layer["source"] for layer in style["layers"]} == set(style["sources"])
    raster_ids = {s["id"] for s in manifest["sources"]} | {s["id"] for s in manifest["liveRasters"]}
    assert not vector_only_violations(style, raster_sources=raster_ids)
    # The web layer is above the ortho in the tree: drawn on top of it.
    order = [layer["metadata"]["q2vt:raster-layer"] for layer in style["layers"]]
    assert order == [ortho, web]
    # The layer list: both layers, the group, zoom-to-layer bounds, the theme.
    by_id = {layer["id"]: layer for layer in manifest["layers"]}
    assert set(by_id) == {ortho, web}
    assert by_id[ortho]["geometry"] == "raster" and by_id[ortho]["opacity"] == 0.8
    assert by_id[ortho]["groupId"] == manifest["groups"][0]["id"] and len(by_id[ortho]["bounds"]) == 4
    assert by_id[web]["live"] == "xyz" and not by_id[web]["initialVisibility"]
    assert {c["role"] for c in manifest["components"]} == {"raster"} and not manifest["rules"]
    (preset,) = manifest["themes"]["presets"]
    assert preset["layers"] == {ortho: False, web: True}
    # No features: no search or feature index, and nothing to count.
    assert manifest["search"] is None and manifest["featureLookup"] is None
    assert result.feature_counts == {} and not result.mbtiles_copy
    assert "https://tiles.example.test" in open(os.path.join(release, "index.html"), encoding="utf-8").read()
    # The release validates as it is (as before an upload).
    validate_release_dir(release, style, None, raster_sources={s["id"]: s["href"] for s in manifest["sources"]},
                         live_sources=[s["id"] for s in manifest["liveRasters"]])
    # Exported again (export cache): the same map.
    again = export_local(project, profile, EXTENT)
    assert [s["sha256"] for s in _read(again.release.release_dir, "manifest.json")["sources"]] == \
        [s["sha256"] for s in manifest["sources"]]


def test_live_layers_alone_make_a_map_without_any_archive(tmp_path):
    project, profile, layers = raster_only_project(tmp_path, local=False)
    profile.output.archive = "both"  # no vector tiles: no MBTiles copy either
    profile.output.local_versions = True
    result = export_local(project, profile, EXTENT)
    release = result.release.release_dir
    manifest = _read(release, "manifest.json")
    _validate_manifest(manifest)
    assert manifest["sources"] == [] and len(manifest["liveRasters"]) == 1
    assert not any(item["path"].startswith("data/") for item in result.release.files)
    assert not result.mbtiles_copy
    assert manifest["view"]["bounds"] and 11 <= manifest["view"]["zoom"] <= 13
    assert os.path.exists(os.path.join(result.publication_dir, "current.json"))


def test_nothing_to_publish_is_refused(tmp_path):
    project, profile, layers = raster_only_project(tmp_path)
    for config in profile.layers:
        config.included, config.initially_visible = False, False
    profile.themes.names = []
    with pytest.raises(PublishingError, match="Select at least one layer") as error:
        export_local(project, profile, EXTENT)
    assert error.value.code == "Q2VT_PUB_PROFILE_INVALID"
    # Only a raster that draws nothing in the extent: an empty map is not published.
    far = QgsRasterLayer(make_raster(tmp_path / "far.tif", origin=(3000000, 7000000)), "Messze")
    project.addMapLayer(far)
    profile.layers = [LayerConfig(far.id(), raster_max_zoom=14)]
    with pytest.raises(PublishingError, match="Nothing to publish") as error:
        export_local(project, profile, EXTENT)
    assert error.value.code == "Q2VT_PUB_EMPTY_ARCHIVE"


def test_parcel_report_without_a_parcel_layer_is_refused(tmp_path):
    from test_publishing_pipeline import _parcels  # pylint: disable=import-outside-toplevel,import-error
    project, profile, layers = raster_only_project(tmp_path)
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    project.addMapLayer(parcels)  # in the project, not published
    info = profile.parcel_info
    info.enabled, info.key_field, info.zoning_code_field = True, "hrsz", "zone"
    info.parcel_layer_id = info.zoning_layer_id = parcels.id()
    with pytest.raises(PublishingError, match="publish the parcel layer") as error:
        export_local(project, profile, EXTENT)
    assert error.value.code == "Q2VT_PUB_PROFILE_INVALID"
    # A raster layer chosen as the parcel layer.
    info.parcel_layer_id = layers["ortho"].id()
    with pytest.raises(PublishingError, match="must be a vector layer") as error:
        export_local(project, profile, EXTENT)
    assert error.value.code == "Q2VT_PUB_PROFILE_INVALID"
