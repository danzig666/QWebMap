"""Launchers and placeholders of the local tile server (ServerInitializer):
only an earlier tile server is stopped, Windows paths with & ( ), the macOS
Python, and the style's values left as they are."""

import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time

import pytest
from qgis.core import QgsRectangle

EXTENT = QgsRectangle(2119000, 6019000, 2123000, 6023000)


@pytest.fixture
def server_initializer(plugin):
    from q2vt_plugin.src.core import server_initializer as module  # pylint: disable=import-error
    return module


def _free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _listener(folder, name, port):
    """A process listening on ``port`` whose command line names ``name``."""
    script = folder / name
    script.write_text("import socket, sys, time\n"
                      "s = socket.socket(); s.bind(('127.0.0.1', int(sys.argv[1]))); s.listen()\n"
                      "print('up', flush=True); time.sleep(120)\n", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, str(script), str(port)], stdout=subprocess.PIPE)
    assert proc.stdout.readline().strip() == b"up"
    return proc


@pytest.mark.skipif(platform.system() == "Windows" or not shutil.which("lsof"),
                    reason="the bash launcher, with lsof")
def test_launcher_stops_only_an_earlier_tile_server(server_initializer, tmp_path):
    """The launcher killed whatever listened on port 9000 (MinIO, PHP-FPM...)."""
    script = server_initializer.ServerInitializer.LINUX_ACTIVATOR
    start, end = script.index("for pid in"), script.index("done") + len("done")
    for name, stopped in (("minio_server.py", False), ("tiles_server.py", True)):
        port = _free_port()
        proc = _listener(tmp_path, name, port)
        try:
            subprocess.run(["bash", "-c", script[start:end].replace("18111991", str(port))],
                           check=False, timeout=60)
            for _ in range(50):
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
            assert (proc.poll() is not None) is stopped, name
        finally:
            proc.kill()
            proc.wait()


def test_windows_launcher_survives_special_characters_and_does_not_wait(server_initializer):
    """cmd /c "<path>" lost its quotes for a folder with & ( ) ^ @ (the server
    never started); the hidden batch file ended with pause (an orphan cmd.exe
    per export, holding the export folder)."""
    init = server_initializer.ServerInitializer
    [line] = [l for l in init.WINDOWS_WRAPPER.splitlines() if "WshShell.Run" in l]
    base = "C:\\Maps & Data (2)\\"
    # The VBScript expression: string literals ("" is one quote) joined by &.
    parts = re.findall(r'"((?:[^"]|"")*)"|\bbase\b', line.split("Run", 1)[1].rsplit(",", 1)[0])
    command = "".join(p.replace('""', '"') if p else base for p in parts)
    assert command == 'cmd /c ""C:\\Maps & Data (2)\\utils\\activate_server.bat""', command
    batch = init.WINDOWS_ACTIVATOR
    assert not re.search(r"^\s*pause\b", batch, re.MULTILINE | re.IGNORECASE), batch
    # Only a process whose command line is the tile server is stopped.
    assert "*tiles_server.py*" in batch
    # The fallback without PowerShell too: taskkill only after the check.
    for line in batch.splitlines():
        if "taskkill" in line:
            assert 'findstr /c:"tiles_server.py" >nul && taskkill' in line, line


def test_macos_python_is_found_in_bin(server_initializer, tmp_path, monkeypatch):
    """<prefix>/python3 does not exist on macOS (QGIS.app, Homebrew, conda):
    the viewer never started."""
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "python3").write_text("", encoding="utf-8")
    monkeypatch.setattr(server_initializer.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(server_initializer, "prefix", str(tmp_path))
    found = server_initializer.ServerInitializer._get_python_exe()  # pylint: disable=protected-access
    assert found == os.path.join(str(tmp_path), "bin", "python3") and os.path.isfile(found)


def test_placeholders_leave_the_styles_values(server_initializer, tmp_path, monkeypatch):
    """The cache-busting token was replaced in the whole style.json: a
    category value 10031993 became "1" and its features vanished."""
    monkeypatch.setattr(server_initializer.platform, "system", lambda: "Linux")
    init = server_initializer.ServerInitializer(EXTENT, 10, 0, str(tmp_path), 11)
    utils = tmp_path / "utils"
    utils.mkdir()
    (tmp_path / "style").mkdir()
    style = {"sources": {"tiles": {"tiles": ["http://localhost:9000/tiles/tiles/{z}/{x}/{y}.pbf?v=10031993"]}},
             "layers": [{"id": "a", "filter": ["match", ["get", "date"], [10031993, 110031993], True, False]},
                        {"id": "b", "layout": {"text-field": "18111991 10031993"}}]}
    (tmp_path / "style" / "style.json").write_text(json.dumps(style), encoding="utf-8")
    activator, wrapper = init._write_server_files(str(tmp_path), str(utils))  # pylint: disable=protected-access
    init._configure_server_placeholders(str(tmp_path), str(utils), activator, wrapper,  # pylint: disable=protected-access
                                        "[1.0, 2.0]", "/usr/bin/python3")
    out = json.loads((tmp_path / "style" / "style.json").read_text(encoding="utf-8"))
    assert out["sources"]["tiles"]["tiles"] == ["http://localhost:9000/tiles/tiles/{z}/{x}/{y}.pbf?v=1"]
    assert out["layers"] == style["layers"]
    viewer = (utils / "viewer" / "viewer.html").read_text(encoding="utf-8")
    assert "18111991" not in viewer and "_Q2VT_" not in viewer
