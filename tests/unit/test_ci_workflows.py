"""The GitHub workflows and development tools around the tests and releases:
the nightly's backup slot and change detection, the CI's QGIS version and
test tools, the per-file timeout, the release zip check, pinned downloads
and the tools' --out folders."""

import configparser
import os
import re
import subprocess
import sys
import zipfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKFLOWS = os.path.join(ROOT, ".github", "workflows")
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "publishing"))
sys.path.insert(0, os.path.join(ROOT, "tools", "gallery"))
import build_release  # noqa: E402  pylint: disable=wrong-import-position,import-error


def _workflow(name):
    # Imported here, not skipped at module level: the tests without YAML
    # still run, and with Q2VT_REQUIRE_TOOLS a missing PyYAML fails.
    try:
        import yaml  # pylint: disable=import-outside-toplevel
    except ImportError:
        from q2vt_support import missing_tool  # pylint: disable=import-outside-toplevel,import-error
        missing_tool("needs PyYAML")
    with open(os.path.join(WORKFLOWS, name), encoding="utf-8") as handle:
        doc = yaml.safe_load(handle)
    doc["on"] = doc.pop(True, doc.get("on"))  # YAML 1.1 reads the key `on` as True
    return doc


def _step(job, name):
    return next(step for step in job["steps"] if step.get("name") == name)


def _tested_paths():
    with open(os.path.join(ROOT, "tools", "ci", "tested_paths"), encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip() and not line.startswith("#")]


def test_backup_slot_guard_names_a_real_schedule():
    """The guard compared with '13 4 * * *', a cron that was not scheduled:
    it never ran and the backup slot always ran a second time."""
    doc = _workflow("tests.yml")
    crons = [entry["cron"] for entry in doc["on"]["schedule"]]
    step = _step(doc["jobs"]["plan"], "Skip the backup slot if tonight's run already started")
    named = re.findall(r"github\.event\.schedule == '([^']+)'", step["if"])
    assert named and named[0] in crons and named[0] != crons[0], (named, crons)
    # A skipped backup run must not count as a tested success.
    assert "gh run cancel" in step["run"]


def test_nightly_change_detection_covers_the_plugin_and_its_workflows():
    """The plugin's root __init__.py, LICENSE, icons and qt6.yml were not in
    the nightly's paths: commits changing only them were never tested."""
    paths = _tested_paths()
    for item in build_release.CONTENT:
        assert item in paths, item
    doc = _workflow("tests.yml")
    for job in doc["jobs"].values():
        if str(job.get("uses", "")).startswith("./"):
            assert job["uses"][2:] in paths, job["uses"]
    assert ".github/workflows/tests.yml" in paths and "tools" in paths
    decide = _step(doc["jobs"]["plan"], "Decide whether to run the tests")["run"]
    assert "tools/ci/tested_paths" in decide
    # A variant branch counts main's merged changes too (its preset and
    # add-on run on main's hooks): no filter to the variant's own files.
    assert "origin/main...HEAD" not in decide


def test_ci_tests_the_minimum_qgis():
    """CI ran 3.34, which cannot install the plugin, and 4.2: the minimum
    (3.44, Qt5) was not tested."""
    metadata = configparser.ConfigParser()
    metadata.read(os.path.join(ROOT, "metadata.txt"), encoding="utf-8")
    minimum = tuple(int(part) for part in metadata["general"]["qgisMinimumVersion"].split("."))
    versions = []
    for name in ("tests.yml", "qt6.yml"):
        for job in _workflow(name)["jobs"].values():
            image = job.get("container", {}).get("image", "")
            if image:
                found = re.match(r"qgis/qgis:(\d+)\.(\d+)", image)
                assert found, image
                versions.append(tuple(int(part) for part in found.groups()))
    assert versions and min(versions) >= minimum, versions
    assert min(versions)[:2] == minimum[:2], "the oldest CI image is the declared minimum"


def test_unit_jobs_have_the_parity_test_tools():
    """Node/MapLibre, moto and go-pmtiles were only in the browser job: the
    parity and real-SDK tests skipped, and skipped counted as passed."""
    for name in ("tests.yml", "qt6.yml"):
        job = _workflow(name)["jobs"]["qgis-tests"]
        assert job["env"].get("Q2VT_REQUIRE_TOOLS") == "1", name
        uses = [step.get("uses", "") for step in job["steps"]]
        runs = [step.get("run", "") for step in job["steps"]]
        assert any(use.startswith("actions/setup-node") for use in uses), name
        assert "tools/ci/prepare_test_tools.sh" in runs, name


def test_missing_tool_fails_when_required(monkeypatch):
    from q2vt_support import missing_tool  # pylint: disable=import-outside-toplevel,import-error
    monkeypatch.setenv("Q2VT_REQUIRE_TOOLS", "1")
    with pytest.raises(pytest.fail.Exception):
        missing_tool("needs Node")
    monkeypatch.delenv("Q2VT_REQUIRE_TOOLS")
    with pytest.raises(pytest.skip.Exception):
        missing_tool("needs Node")


@pytest.mark.skipif(os.name == "nt", reason="bash script")
def test_a_hanging_test_file_times_out_and_the_rest_still_run(tmp_path):
    (tmp_path / "test_hang.py").write_text("import time\n\ndef test_hang():\n    time.sleep(600)\n")
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    summary = tmp_path / "summary.md"
    run = subprocess.run(["bash", os.path.join(ROOT, "tools", "ci", "run_test_files.sh"), "Hang",
                          "test_hang.py", "test_ok.py"], cwd=tmp_path, capture_output=True, text=True,
                         timeout=300, env={**os.environ, "Q2VT_FILE_TIMEOUT": "3",
                                           "GITHUB_STEP_SUMMARY": str(summary)})
    assert run.returncode == 1, run.stdout + run.stderr
    text = summary.read_text()
    assert "test_hang.py (timed out after 3 s)" in text and "1 of 2 test files passed" in text, text


def _zip_entries(path):
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def test_release_zip_is_compared_with_the_commit(tmp_path):
    """Only the zipped metadata.txt was compared before a release: a zip
    built before the last code commit would have been published."""
    built = tmp_path / "built.zip"
    assert build_release.main(["--out", str(built)]) == 0
    assert build_release.main(["--compare", str(built)]) == 0
    stale = tmp_path / "stale.zip"
    with zipfile.ZipFile(stale, "w") as archive:
        for name, data in _zip_entries(built).items():
            archive.writestr(name, data + b"# old\n" if name == "QWebMap/__init__.py" else data)
    assert build_release.main(["--compare", str(stale)]) == 1
    workflow = _step(_workflow("release.yml")["jobs"]["release"], "Resolve the variant, zip and notes")["run"]
    assert 'tools/build_release.py --compare "${ZIP}"' in workflow
    assert "tools/ci/tested_paths" in workflow  # the code must have passed the tests


def test_release_zip_refuses_uncommitted_plugin_files(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "metadata.txt").write_text("[general]\nname=QWebMap\nversion=9.9.9\n")
    (repo / "__init__.py").write_text("x = 1\n")
    (repo / "releases").mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.org"}
    for command in (["init", "-q"], ["add", "."], ["commit", "-q", "-m", "x"]):
        subprocess.run(["git", *command], cwd=repo, check=True, env=env, capture_output=True)
    monkeypatch.setattr(build_release, "ROOT", str(repo))
    assert build_release.main(["--variant", ""]) == 0
    assert (repo / "releases" / "QWebMap-9.9.9.zip").exists()
    (repo / "__init__.py").write_text("x = 2\n")
    with pytest.raises(SystemExit, match="uncommitted"):
        build_release.main(["--variant", ""])
    # A scratch build (--out) of the working tree stays possible.
    assert build_release.main(["--variant", "", "--out", str(tmp_path / "scratch.zip")]) == 0


def test_release_replace_never_deletes_the_published_release():
    workflow = open(os.path.join(WORKFLOWS, "release.yml"), encoding="utf-8").read()
    assert "gh release delete" not in workflow
    assert "--clobber" in workflow


def test_variant_sync_runs_one_at_a_time():
    job = _workflow("sync-variants.yml")["jobs"]["sync"]
    assert "matrix.branch" in job["concurrency"]["group"]
    assert job["concurrency"]["cancel-in-progress"] is False


def test_vendored_wheels_are_all_pinned(tmp_path, monkeypatch):
    """A wheel in WHEELS without a pinned hash was vendored unchecked; and
    the vendored SDK was deleted before the downloads."""
    import vendor_s3  # pylint: disable=import-outside-toplevel,import-error
    pinned = vendor_s3.pinned_hashes()
    assert set(vendor_s3.WHEELS) <= set(pinned)
    target = tmp_path / "s3"
    target.mkdir()
    (target / "kept.py").write_text("")
    monkeypatch.setattr(vendor_s3, "TARGET", str(target))

    def offline(*_args, **_kwargs):
        raise OSError("offline")
    monkeypatch.setattr(vendor_s3.urllib.request, "urlopen", offline)
    monkeypatch.setattr(vendor_s3, "WHEELS", {**vendor_s3.WHEELS, "new-1.0-py3-none-any.whl": None})
    with pytest.raises(SystemExit, match="No pinned SHA-256"):
        vendor_s3.main([])
    monkeypatch.setattr(vendor_s3, "WHEELS", {name: None for name in pinned})
    monkeypatch.setattr(vendor_s3, "_pypi_url", lambda name: name)
    with pytest.raises(OSError):
        vendor_s3.main([])
    assert (target / "kept.py").exists()


def test_vendor_record_still_checks_the_pinned_wheels(tmp_path, monkeypatch):
    """--record rewrote every pin from the downloads: adding one wheel
    re-trusted (and re-pinned) a changed payload of a pinned one."""
    import hashlib  # pylint: disable=import-outside-toplevel
    import io  # pylint: disable=import-outside-toplevel
    import vendor_s3  # pylint: disable=import-outside-toplevel,import-error
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as wheel:
        wheel.writestr("pkg/__init__.py", "")
    payload = buffer.getvalue()
    pins = tmp_path / "pins.sha256"
    old = f"{hashlib.sha256(payload).hexdigest()}  old-1.0-py3-none-any.whl\n"
    pins.write_text(old)
    monkeypatch.setattr(vendor_s3, "HASHES_FILE", str(pins))
    monkeypatch.setattr(vendor_s3, "TARGET", str(tmp_path / "s3"))
    monkeypatch.setattr(vendor_s3, "WHEELS", {"old-1.0-py3-none-any.whl": None,
                                              "new-1.0-py3-none-any.whl": None})
    monkeypatch.setattr(vendor_s3, "_pypi_url", lambda name: name)
    served = {"old-1.0-py3-none-any.whl": payload + b"x", "new-1.0-py3-none-any.whl": payload}

    class Response:  # pylint: disable=too-few-public-methods
        def __init__(self, data):
            self.data = data

        def read(self):
            return self.data
    monkeypatch.setattr(vendor_s3.urllib.request, "urlopen", lambda url, timeout: Response(served[url]))
    with pytest.raises(SystemExit, match="old-1.0.*!= pinned"):
        vendor_s3.main(["--record"])
    assert pins.read_text() == old and not (tmp_path / "s3").exists()
    served["old-1.0-py3-none-any.whl"] = payload
    assert vendor_s3.main(["--record"]) == 0
    assert pins.read_text() == old + f"{hashlib.sha256(payload).hexdigest()}  new-1.0-py3-none-any.whl\n"


def test_pmtiles_cli_downloads_are_pinned():
    import fetch_pmtiles_cli  # pylint: disable=import-outside-toplevel,import-error
    assert set(fetch_pmtiles_cli.ASSETS.values()) <= set(fetch_pmtiles_cli.SHA256)


def test_tools_refuse_to_wipe_a_folder_they_did_not_make(tmp_path):
    import build_gallery  # pylint: disable=import-outside-toplevel,import-error
    work = tmp_path / "work"
    work.mkdir()
    (work / "thesis.txt").write_text("keep me")
    with pytest.raises(SystemExit, match="not made by this tool.*older than this check"):
        build_gallery.fresh_out_dir(str(work))
    assert (work / "thesis.txt").read_text() == "keep me"
    out = build_gallery.fresh_out_dir(str(tmp_path / "out"))
    (tmp_path / "out" / "old.png").write_text("")
    assert build_gallery.fresh_out_dir(out) == out  # its own folder: emptied
    assert os.listdir(out) == [build_gallery.OUT_MARKER]
    with pytest.raises(SystemExit):
        build_gallery.fresh_out_dir(ROOT)


def test_ci_jobs_do_not_download_the_release_zips():
    """blob:none alone still downloads every file at HEAD (all release zips,
    hundreds of MB) for the nightly plan, every sync and every release."""
    def checkout(job):
        return next(step for step in job["steps"] if str(step.get("uses", "")).startswith("actions/checkout"))
    plan = checkout(_workflow("tests.yml")["jobs"]["plan"])["with"]
    assert plan["sparse-checkout"].split() == ["tools/ci"]
    assert plan.get("sparse-checkout-cone-mode", True) is True
    decide = _step(_workflow("tests.yml")["jobs"]["plan"], "Decide whether to run the tests")["run"]
    assert "tools/ci/tested_paths" in decide and "git diff --name-only" in decide
    for name, job in (("sync-variants.yml", "sync"), ("release.yml", "release")):
        options = checkout(_workflow(name)["jobs"][job])["with"]
        assert "!/releases/" in options["sparse-checkout"].split(), name
        assert options["sparse-checkout-cone-mode"] is False, name
    resolve = _step(_workflow("release.yml")["jobs"]["release"], "Resolve the variant, zip and notes")["run"]
    added = resolve.index('git sparse-checkout add "/${ZIP}" "/${NOTES}"')
    assert added < resolve.index('[ -f "${NOTES}" ]') < resolve.index("--compare")
