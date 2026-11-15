"""ogr2ogr of the QGIS that runs the plugin: looked for next to QGIS first,
then on PATH; a candidate that does not run is passed over; none found:
an error saying where it looked."""

import os
import stat

import pytest


def _script(path, body):
    path.write_text("#!/bin/sh\n" + body + "\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


@pytest.mark.skipif(os.name == "nt", reason="shell scripts as stand-in tools")
def test_tools_next_to_qgis_first_and_only_ones_that_run(plugin, tmp_path, monkeypatch):  # pylint: disable=unused-argument
    from q2vt_plugin.src.utils import gdal_tools  # pylint: disable=import-error
    broken, good, path_dir = tmp_path / "broken", tmp_path / "good", tmp_path / "path"
    for folder in (broken, good, path_dir):
        folder.mkdir()
    _script(broken / "ogr2ogr", "exit 1")
    _script(good / "ogr2ogr", 'echo "GDAL 3.99.0, released 2026/11/15"')
    _script(path_dir / "ogr2ogr", 'echo "GDAL 2.0 elsewhere"')
    monkeypatch.setattr(gdal_tools, "_FOUND", {})
    monkeypatch.setattr(gdal_tools, "candidate_dirs", lambda: [str(broken), str(good)])
    monkeypatch.setattr(gdal_tools.shutil, "which", lambda name: str(path_dir / name))
    assert gdal_tools.find_tool("ogr2ogr") == str(good / "ogr2ogr")
    assert "GDAL 3.99.0" in gdal_tools.describe("ogr2ogr")
    # Nothing next to QGIS: PATH.
    monkeypatch.setattr(gdal_tools, "_FOUND", {})
    monkeypatch.setattr(gdal_tools, "candidate_dirs", lambda: [str(broken)])
    assert gdal_tools.find_tool("ogr2ogr") == str(path_dir / "ogr2ogr")
    # Nothing that runs: where it looked.
    monkeypatch.setattr(gdal_tools, "_FOUND", {})
    monkeypatch.setattr(gdal_tools.shutil, "which", lambda name: None)
    with pytest.raises(gdal_tools.GdalToolNotFound) as error:
        gdal_tools.find_tool("ogr2ogr")
    assert str(broken) in str(error.value) and "PATH" in str(error.value)


def test_qgis_own_ogr2ogr_is_found_with_its_data(plugin, monkeypatch):  # pylint: disable=unused-argument
    from q2vt_plugin.src.utils import gdal_tools  # pylint: disable=import-error
    monkeypatch.setattr(gdal_tools, "_FOUND", {})
    path = gdal_tools.find_tool("ogr2ogr")
    assert os.path.isfile(path) and gdal_tools.describe("ogr2ogr").startswith(path)
    env = gdal_tools.tool_env({})
    assert env.get("GDAL_DATA") is None or os.path.isdir(env["GDAL_DATA"])
    assert env.get("PROJ_DATA") is None or os.path.isfile(os.path.join(env["PROJ_DATA"], "proj.db"))
