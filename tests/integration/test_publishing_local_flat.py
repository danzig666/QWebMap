"""Local export without versions (the default): the site goes straight into
<folder>/<slug>/, the next export replaces it (removing only files the
previous export wrote), and "keep versions" still builds releases/<id>/."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_publishing_pipeline import EXTENT, _parcels, _profile  # noqa: E402  pylint: disable=wrong-import-position


def test_local_export_is_one_site_replaced_each_time(tmp_path):
    from publishing.controller import FLAT_STATE, export_local
    from q2vt_fixtures import reset_project
    project = reset_project()
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    project.addMapLayer(parcels)
    profile = _profile(parcels, tmp_path)
    assert not profile.output.local_versions  # the default
    first = export_local(project, profile, EXTENT)
    folder = first.publication_dir
    assert first.release.release_dir == folder and first.entry_path == os.path.join(folder, "index.html")
    assert not os.path.exists(os.path.join(folder, "releases"))
    assert not [n for n in os.listdir(folder) if n.startswith("bootstrap.")]
    manifest = json.load(open(os.path.join(folder, "manifest.json"), encoding="utf-8"))
    assert manifest["releaseId"] == first.release.release_id
    listed = json.load(open(os.path.join(folder, FLAT_STATE), encoding="utf-8"))["files"]
    assert "index.html" in listed and "data/map.pmtiles" in listed
    # A file of the previous export that the next one does not write is
    # removed; the user's own file stays.
    stale = os.path.join(folder, "assets", "old-export-file.js")
    open(stale, "w", encoding="utf-8").write("x")
    state = json.load(open(os.path.join(folder, FLAT_STATE), encoding="utf-8"))
    state["files"].append("assets/old-export-file.js")
    json.dump(state, open(os.path.join(folder, FLAT_STATE), "w", encoding="utf-8"))
    mine = os.path.join(folder, "notes.txt")
    open(mine, "w", encoding="utf-8").write("mine")
    second = export_local(project, profile, EXTENT)
    assert second.release.release_id != first.release.release_id
    assert not os.path.exists(stale) and os.path.exists(mine)
    manifest = json.load(open(os.path.join(folder, "manifest.json"), encoding="utf-8"))
    assert manifest["releaseId"] == second.release.release_id


def test_keep_versions_builds_releases(tmp_path):
    from publishing.controller import export_local
    from q2vt_fixtures import reset_project
    project = reset_project()
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    project.addMapLayer(parcels)
    profile = _profile(parcels, tmp_path)
    profile.output.local_versions = True
    result = export_local(project, profile, EXTENT)
    assert os.path.isdir(os.path.join(result.publication_dir, "releases", result.release.release_id))
    assert os.path.exists(os.path.join(result.publication_dir, "current.json"))


def test_mbtiles_and_zip_are_one_file_each_next_to_the_site(tmp_path):
    """"MBTiles only" writes an MBTiles (and the site, for the preview); each
    export replaces the MBTiles and the ZIP instead of adding new ones."""
    from publishing.controller import export_local
    from q2vt_fixtures import reset_project
    project = reset_project()
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    project.addMapLayer(parcels)
    profile = _profile(parcels, tmp_path)
    profile.output.archive, profile.output.zip = "mbtiles", True
    profile.description = "Data source:\nCity survey 2024"  # no "C:\\n" path in manifest.json
    first = export_local(project, profile, EXTENT)
    base = os.path.dirname(first.publication_dir)
    assert first.mbtiles_copy == os.path.join(base, "arlo-teszt.mbtiles") and os.path.isfile(first.mbtiles_copy)
    assert first.zip_path == os.path.join(base, "arlo-teszt.zip") and os.path.isfile(first.zip_path)
    profile.output.archive = "both"
    export_local(project, profile, EXTENT)
    assert sorted(n for n in os.listdir(base) if n.endswith((".mbtiles", ".zip"))) == \
        ["arlo-teszt.mbtiles", "arlo-teszt.zip"]


def test_a_running_export_of_the_folder_stops_the_next_at_plan(tmp_path, monkeypatch):
    """The folder is locked from PLAN: a second export fails before tiling;
    a lock left by a QGIS that has ended does not block."""
    import platform
    import subprocess
    from publishing import controller
    from publishing.errors import PublishingError
    from q2vt_fixtures import reset_project
    project = reset_project()
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    project.addMapLayer(parcels)
    profile = _profile(parcels, tmp_path)
    folder, _ = controller.publication_dirs(profile)
    os.makedirs(folder)
    lock = os.path.join(folder, ".q2vt-lock")
    with open(lock, "w", encoding="utf-8") as handle:
        handle.write(f"{os.getppid()} 0 {platform.node()}")  # a live process
    tiled = []
    monkeypatch.setattr(controller, "_plan_rasters", lambda *a: tiled.append(1) or [])
    try:
        controller.export_local(project, profile, EXTENT)
        raise AssertionError("not locked")
    except PublishingError as error:
        assert error.code == "Q2VT_PUB_DESTINATION" and lock in error.detail
    assert not tiled and os.path.exists(lock)
    monkeypatch.undo()
    ended = subprocess.Popen([sys.executable, "-c", "pass"])
    ended.wait()
    with open(lock, "w", encoding="utf-8") as handle:
        handle.write(f"{ended.pid} 0 {platform.node()}")  # QGIS closed during an export
    result = controller.export_local(project, profile, EXTENT)
    assert os.path.isfile(result.entry_path) and not os.path.exists(lock)


def test_a_site_move_that_fails_part_way_is_repaired_by_the_next_export(tmp_path, monkeypatch):
    """Unversioned output: the files are listed before they are moved, the
    release left behind (without its release.json) is removed by recover()."""
    from publishing import controller
    from publishing.models import PublicationProfile
    from publishing.web_builder import build_release, recover
    from publishing_fixtures import fixture_bundle
    bundle = fixture_bundle(str(tmp_path / "export"))
    profile = PublicationProfile(title="Teszt", slug="teszt")
    pub = str(tmp_path / "web" / "teszt")
    first = build_release(bundle, profile, pub, activate=False, stable_entry=False)
    controller.flatten_release(first, pub)
    old = set(controller._flat_state(os.path.join(pub, controller.FLAT_STATE)))  # pylint: disable=protected-access
    second = build_release(bundle, profile, pub, activate=False, stable_entry=False)
    moves = []
    real = controller._replace  # pylint: disable=protected-access

    def failing(source, target):
        moves.append(source)
        if len(moves) == 3:
            raise PermissionError("in use")
        real(source, target)

    monkeypatch.setattr(controller, "_replace", failing)
    with pytest.raises(PermissionError):
        controller.flatten_release(second, pub)
    assert os.path.basename(moves[0]) == "release.json"
    listed = controller._flat_state(os.path.join(pub, controller.FLAT_STATE))  # pylint: disable=protected-access
    assert old <= listed and "index.html" in listed
    assert recover(pub) == [f"releases/{second.release_id}"]
    monkeypatch.undo()
    third = build_release(bundle, profile, pub, activate=False, stable_entry=False)
    controller.flatten_release(third, pub)
    assert not os.path.exists(os.path.join(pub, "releases"))
    assert json.load(open(os.path.join(pub, "manifest.json"), encoding="utf-8"))["releaseId"] == third.release_id


def test_a_file_in_use_is_replaced_when_it_is_free_again(tmp_path, monkeypatch):
    from publishing import controller
    calls = []
    real = os.replace

    def busy(source, target):
        calls.append(source)
        if len(calls) < 3:
            raise PermissionError("in use")
        real(source, target)

    (tmp_path / "a").write_text("x")
    monkeypatch.setattr(controller.os, "replace", busy)
    controller._replace(str(tmp_path / "a"), str(tmp_path / "b"), waits=(0, 0, 0))  # pylint: disable=protected-access
    monkeypatch.undo()
    assert len(calls) == 3 and (tmp_path / "b").read_text() == "x"


def test_a_local_path_in_the_description_stops_the_export_at_plan(tmp_path):
    from publishing.controller import export_local
    from publishing.errors import PublishingError
    from q2vt_fixtures import reset_project
    project = reset_project()
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    project.addMapLayer(parcels)
    profile = _profile(parcels, tmp_path)
    profile.description = "Source: D:/GIS/plan.qgz"
    with pytest.raises(PublishingError) as error:
        export_local(project, profile, EXTENT)
    assert error.value.code == "Q2VT_PUB_SECRET_LEAK" and "Description" in error.value.message
    assert not os.path.exists(os.path.join(profile.output.local_directory, "arlo-teszt"))
