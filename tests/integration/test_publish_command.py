"""The "Publish web map" Processing algorithm (publishing.headless): the web
map of the project's saved publication settings, exported locally or
published to their destination without the Publish window, so
``qgis_process`` runs it from a command line (Windows: qgis_process-qgis.bat)."""

import json
import os
import shutil
import subprocess
import sys

import pytest
from qgis.core import QgsApplication, QgsProcessingContext, QgsProcessingFeedback, QgsProject

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from q2vt_fixtures import reset_project  # noqa: E402  pylint: disable=wrong-import-position

ALG = "QGIS2VectorTilesFork:publish_web_map"
EXTENT_3857 = [2119000, 6019000, 2123000, 6023000]
_PROVIDERS = []  # kept referenced (see test_publishing_export)


def _algorithm():
    registry = QgsApplication.processingRegistry()
    alg = registry.algorithmById(ALG)
    if alg is None:
        from q2vt_plugin.src.processing.provider import QGIS2VectorTilesPorvider  # pylint: disable=import-error
        _PROVIDERS.append(QGIS2VectorTilesPorvider())
        registry.addProvider(_PROVIDERS[-1])
        alg = registry.algorithmById(ALG)
    assert alg is not None
    return alg


def _run(params, project=None):
    context = QgsProcessingContext()
    context.setProject(project or QgsProject.instance())
    feedback = QgsProcessingFeedback()
    results, ok = _algorithm().run(params, context, feedback)
    return (results if ok else None), "" if ok else feedback.textLog()  # the error is logged


def _saved_settings(tmp_path, title="Arló szabályozási terv", slug="arlo-terv", kind="local", **view):
    """A project with parcels and publication settings saved in it, as the
    Publish window saves them."""
    from test_publishing_pipeline import _parcels  # pylint: disable=import-error
    from q2vt_plugin.src.gui import publication_profiles as store  # pylint: disable=import-error
    from q2vt_plugin.src.publishing.models import (LayerConfig, PopupField,  # pylint: disable=import-error
                                                   PublicationProfile)
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    project = reset_project(parcels)
    profile = PublicationProfile(title=title, slug=slug, locale="hu")
    profile.view.min_zoom, profile.view.max_zoom = 11, 12
    profile.view.extent_mode = view.get("extent_mode", "canvas")
    profile.view.extent = view.get("extent", list(EXTENT_3857))
    profile.view.extent_layer = parcels.id() if profile.view.extent_mode == "layer" else ""
    profile.output.local_directory = str(tmp_path / "web")
    profile.layers = [LayerConfig(parcels.id(), popup_fields=[PopupField("hrsz", "Helyrajzi szám")],
                                  search_fields=["hrsz"], key_fields=["hrsz"])]
    profile.destination.kind = kind
    store.save_profile(project, profile)
    return project, parcels, profile


def test_exports_the_saved_settings_locally(plugin, tmp_path):
    project, _, profile = _saved_settings(tmp_path)
    results, error = _run({"ACTION": 1}, project)  # export locally only
    assert results, error
    entry = results["ENTRY"]
    assert entry == os.path.join(results["OUTPUT_FOLDER"], "index.html") and os.path.exists(entry)
    assert results["OUTPUT_FOLDER"].startswith(str(tmp_path / "web")) and profile.slug in results["OUTPUT_FOLDER"]
    assert not results["PUBLISHED"] and results["URL"] == ""
    # The local destination: "Publish" is the same export, as in the window.
    results, error = _run({"OUTPUT_DIR": str(tmp_path / "elsewhere")}, project)
    assert results, error
    assert results["OUTPUT_FOLDER"].startswith(str(tmp_path / "elsewhere")) and os.path.exists(results["ENTRY"])


def test_settings_are_found_by_title_or_address(plugin, tmp_path):
    project, _, _ = _saved_settings(tmp_path)
    from q2vt_plugin.src.gui import publication_profiles as store  # pylint: disable=import-error
    second, _ = store.active_profile(project)
    second = store.as_new_publication(second)
    second.title, second.slug = "Második térkép", "masodik"
    store.save_profile(project, second)
    from q2vt_plugin.src.publishing import headless  # pylint: disable=import-error
    assert headless.find_profile(project).slug == "masodik"  # the active (last saved) ones
    assert headless.find_profile(project, "arlo-terv").title == "Arló szabályozási terv"
    assert headless.find_profile(project, "  ARLÓ SZABÁLYOZÁSI TERV ").slug == "arlo-terv"
    results, error = _run({"SETTINGS": "nincs ilyen", "ACTION": 1}, project)
    assert results is None and "nincs ilyen" in error and "arlo-terv" in error and "masodik" in error


def test_without_saved_settings_it_says_what_to_do(plugin, tmp_path):
    reset_project()
    results, error = _run({"ACTION": 1})
    assert results is None and "Publish Web Map" in error


def test_extent_follows_the_settings_or_the_parameter(plugin, tmp_path):
    from q2vt_plugin.src.publishing import headless  # pylint: disable=import-error
    from qgis.core import QgsCoordinateReferenceSystem, QgsRectangle
    project, parcels, profile = _saved_settings(tmp_path, extent_mode="layer", extent=[0, 0, 1, 1])
    box = headless.extent_3857(project, profile)
    layer = parcels.extent()
    assert box == pytest.approx([layer.xMinimum(), layer.yMinimum(), layer.xMaximum(), layer.yMaximum()])
    wgs84 = QgsRectangle(19.0, 47.4, 19.1, 47.5)
    box = headless.extent_3857(project, profile, wgs84, QgsCoordinateReferenceSystem("EPSG:4326"))
    assert box[0] == pytest.approx(2115070, abs=5) and box[3] == pytest.approx(6024072, abs=5)
    profile.view.extent_mode, profile.view.extent_layer, profile.view.extent = "canvas", "", []
    with pytest.raises(Exception, match="EXTENT"):  # never exported: no map view to take
        headless.extent_3857(project, profile)


def test_publishes_to_the_destination_after_approval(plugin, tmp_path, monkeypatch):
    """R2 with credentials from the environment: refused until approved
    (nothing uploaded), then uploaded, verified and activated; the approval
    is saved into the project file on request, never the credentials."""
    from publishing_fake_s3 import FakeS3Client  # pylint: disable=import-error
    from q2vt_plugin.src.publishing import providers  # pylint: disable=import-error
    from q2vt_plugin.src.publishing.preview_server import PreviewServer  # pylint: disable=import-error
    from q2vt_plugin.src.publishing.providers.r2 import R2Provider  # pylint: disable=import-error
    project, _, profile = _saved_settings(tmp_path, kind="r2")
    root = tmp_path / "bucket"
    client = FakeS3Client(str(root))
    public = PreviewServer(str(root / "maps")).start()
    from q2vt_plugin.src.gui import publication_profiles as store  # pylint: disable=import-error
    profile.destination.account_id, profile.destination.bucket = "abc123", "maps"
    profile.destination.public_base_url = public.url("").rstrip("/")
    store.save_profile(project, profile)
    project_file = str(tmp_path / "terv.qgz")
    assert project.write(project_file)
    used = []

    def provider_for(destination, credentials, prefix, **kwargs):
        used.append(credentials)
        return R2Provider(destination, credentials, prefix, client=client, sleep=lambda s: None)
    monkeypatch.setattr(providers, "provider_for", provider_for)
    monkeypatch.setenv("QWEBMAP_ACCESS_KEY_ID", "AKIATEST")
    monkeypatch.setenv("QWEBMAP_SECRET_ACCESS_KEY", "env-secret-value")
    try:
        results, error = _run({}, project)
        assert results is None and "Q2VT_PUB_REVIEW_NEEDED" in error and not client.keys()
        results, error = _run({"APPROVE": True, "SAVE_PROJECT": True}, project)
        assert results, error
        assert results["PUBLISHED"] and results["URL"].endswith("/maps/arlo-terv/index.html")
        assert used[-1].access_key_id == "AKIATEST" and used[-1].secret_access_key == "env-secret-value"
        assert client.keys() and all(k.startswith("maps/arlo-terv/") for k in client.keys())
        pointer = json.loads(open(root / "maps" / "maps" / "arlo-terv" / "current.json").read())
        assert pointer["releaseId"]
        saved = open(project_file, "rb").read()  # a zip: the secret is in no member
        import zipfile  # pylint: disable=import-outside-toplevel
        with zipfile.ZipFile(project_file) as archive:
            text = b"".join(archive.read(n) for n in archive.namelist())
        assert saved and b"env-secret-value" not in text and b"AKIATEST" not in text
        again = QgsProject()
        assert again.read(project_file)
        reloaded, _ = store.active_profile(again)
        assert reloaded.approval.fingerprint  # approved once: the next run needs no APPROVE
        results, error = _run({}, again)
        assert results and results["PUBLISHED"], error
    finally:
        public.stop()


def test_qgis_process_runs_it(plugin, tmp_path):
    """The real command line: qgis_process with a profile that has the
    plugin installed and enabled."""
    qgis_process = shutil.which("qgis_process")
    if qgis_process is None:
        pytest.skip("qgis_process is not installed")
    project, _, _ = _saved_settings(tmp_path)
    project_file = str(tmp_path / "terv.qgz")
    assert project.write(project_file)
    config = tmp_path / "config"
    plugins = config / "profiles" / "default" / "python" / "plugins"
    plugins.mkdir(parents=True)
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.symlink(repo, plugins / "QWebMap")
    env = {**os.environ, "QGIS_CUSTOM_CONFIG_PATH": str(config), "QT_QPA_PLATFORM": "offscreen"}
    enable = subprocess.run([qgis_process, "plugins", "enable", "QWebMap"], env=env,
                            capture_output=True, text=True, timeout=300)
    assert enable.returncode == 0, enable.stdout[-2000:] + enable.stderr[-2000:]
    run = subprocess.run([qgis_process, "--json", "run", ALG, f"--PROJECT_PATH={project_file}",
                          "--ACTION=1", f"--OUTPUT_DIR={tmp_path / 'cli'}"],
                         env=env, capture_output=True, text=True, timeout=900, cwd=str(tmp_path))
    assert run.returncode == 0, run.stdout[-3000:] + run.stderr[-3000:]
    results = json.loads(run.stdout[run.stdout.index("{"):])["results"]
    assert os.path.exists(results["ENTRY"]) and results["ENTRY"].startswith(str(tmp_path / "cli"))


def test_raster_only_settings_are_exported_and_published(plugin, tmp_path, monkeypatch):
    """Settings of raster layers only (a rendered image and a live web
    layer, no vector layer): exported locally, then uploaded, verified
    (ranges of the image archive) and activated."""
    from publishing_fake_s3 import FakeS3Client  # pylint: disable=import-error
    from test_publishing_raster_only import raster_only_project  # pylint: disable=import-error
    from q2vt_plugin.src.gui import publication_profiles as store  # pylint: disable=import-error
    from q2vt_plugin.src.publishing import providers  # pylint: disable=import-error
    from q2vt_plugin.src.publishing.preview_server import PreviewServer  # pylint: disable=import-error
    from q2vt_plugin.src.publishing.providers.r2 import R2Provider  # pylint: disable=import-error
    project, profile, _ = raster_only_project(tmp_path)
    profile.view.extent_mode, profile.view.extent = "fixed", list(EXTENT_3857)
    store.save_profile(project, profile)
    results, error = _run({"ACTION": 1}, project)  # export locally only
    assert results, error
    with open(os.path.join(results["OUTPUT_FOLDER"], "manifest.json"), encoding="utf-8") as handle:
        manifest = json.load(handle)
    assert [s.get("role") for s in manifest["sources"]] == ["raster"] and manifest["liveRasters"]
    root = tmp_path / "bucket"
    client = FakeS3Client(str(root))
    public = PreviewServer(str(root / "maps")).start()
    profile.destination.kind = "r2"
    profile.destination.account_id, profile.destination.bucket = "abc123", "maps"
    profile.destination.public_base_url = public.url("").rstrip("/")
    store.save_profile(project, profile)
    monkeypatch.setattr(providers, "provider_for", lambda destination, credentials, prefix, **kwargs: R2Provider(
        destination, credentials, prefix, client=client, sleep=lambda s: None))
    monkeypatch.setenv("QWEBMAP_ACCESS_KEY_ID", "AKIATEST")
    monkeypatch.setenv("QWEBMAP_SECRET_ACCESS_KEY", "env-secret-value")
    try:
        results, error = _run({"APPROVE": True}, project)
        assert results and results["PUBLISHED"], error
        keys = client.keys()
        assert any("/data/raster-" in k and k.endswith(".pmtiles") for k in keys)
        assert not any(k.endswith("/data/map.pmtiles") for k in keys)
        with open(root / "maps" / "maps" / "ortofoto" / "current.json", encoding="utf-8") as handle:
            assert json.load(handle)["releaseId"]
    finally:
        public.stop()
