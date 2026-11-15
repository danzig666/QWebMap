"""
gdal_tools.py

GDAL's command-line tools (ogr2ogr) of the QGIS that runs the plugin.

The first ``ogr2ogr`` on PATH is not always QGIS's own: QGIS started
without its launcher (no OSGeo4W environment), or another GDAL earlier on
PATH (an older OSGeo4W, conda, PostgreSQL's bin) ran instead, with another
GDAL version or none of the MVT driver. The tools are looked for next to
QGIS first (its prefix, its Python, the macOS application bundle), then
on PATH; each candidate is run once (``--version``) and used only if it
answers. The child process gets GDAL_DATA / PROJ_DATA as QGIS's own GDAL
uses them.
"""

import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

_FOUND: Dict[str, Tuple[str, str]] = {}  # tool -> (path, version line)


class GdalToolNotFound(RuntimeError):
    """No working GDAL tool: the message lists where it was looked for."""


def _exe(name: str) -> str:
    return f"{name}.exe" if os.name == "nt" else name


def candidate_dirs() -> List[str]:
    """Folders that may hold QGIS's GDAL tools, most likely first."""
    dirs = []
    try:
        from qgis.core import QgsApplication  # pylint: disable=import-outside-toplevel
        prefix = QgsApplication.prefixPath()
    except Exception:  # noqa: BLE001 - outside QGIS
        prefix = ""
    if prefix:
        dirs += [os.path.join(prefix, "bin"), os.path.join(prefix, "..", "..", "bin"),
                 os.path.join(prefix, "..", "bin")]
        # macOS: <QGIS.app>/Contents/MacOS (prefix) and its bin, Frameworks.
        contents = os.path.dirname(prefix.rstrip("/\\"))
        if contents.endswith("Contents"):
            dirs += [os.path.join(contents, "MacOS", "bin"), os.path.join(contents, "MacOS"),
                     os.path.join(contents, "Frameworks", "bin")]
    python_dir = os.path.dirname(sys.executable or "")
    if python_dir:
        dirs += [python_dir, os.path.join(python_dir, "..", "bin"), os.path.join(python_dir, "..", "..", "bin")]
    seen, out = set(), []
    for folder in dirs:
        norm = os.path.normcase(os.path.abspath(folder))
        if norm not in seen:
            seen.add(norm)
            out.append(os.path.abspath(folder))
    return out


def _popen_options() -> dict:
    if os.name != "nt":
        return {}
    return {"creationflags": 0x08000000}  # CREATE_NO_WINDOW


def tool_env(base: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """``base`` (os.environ) with GDAL_DATA and PROJ_DATA / PROJ_LIB as the
    GDAL inside QGIS uses them, where the environment does not set them."""
    env = dict(os.environ if base is None else base)
    if not env.get("GDAL_DATA"):
        try:
            from osgeo import gdal  # pylint: disable=import-outside-toplevel
            data = gdal.GetConfigOption("GDAL_DATA")
            if data and os.path.isdir(data):
                env["GDAL_DATA"] = data
        except Exception:  # noqa: BLE001
            pass
    if not env.get("PROJ_DATA") and not env.get("PROJ_LIB"):
        try:
            from osgeo import osr  # pylint: disable=import-outside-toplevel
            paths = osr.GetPROJSearchPaths() if hasattr(osr, "GetPROJSearchPaths") else []
            folder = next((p for p in paths or [] if os.path.isfile(os.path.join(p, "proj.db"))), None)
            if folder:
                env["PROJ_DATA"] = env["PROJ_LIB"] = folder
        except Exception:  # noqa: BLE001
            pass
    return env


def _answers(path: str) -> Optional[str]:
    """The tool's version line, or None when it does not run."""
    try:
        result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=20,
                                env=tool_env(), errors="replace", check=False, **_popen_options())
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    line = (result.stdout or "").strip().splitlines()
    return line[0] if result.returncode == 0 and line else None


def find_tool(name: str = "ogr2ogr") -> str:
    """Path of a working ``name`` (cached per QGIS session); raises
    GdalToolNotFound with the folders searched."""
    if name in _FOUND:
        return _FOUND[name][0]
    looked = []
    candidates = [os.path.join(folder, _exe(name)) for folder in candidate_dirs()]
    on_path = shutil.which(name)
    if on_path:
        candidates.append(on_path)
    seen = set()
    for path in candidates:
        key = os.path.normcase(os.path.abspath(path))
        if key in seen:
            continue
        seen.add(key)
        looked.append(path)
        if not os.path.isfile(path):
            continue
        version = _answers(path)
        if version:
            _FOUND[name] = (path, version)
            return path
    raise GdalToolNotFound(
        f"{name} (GDAL) was not found or does not run. Looked in: " + "; ".join(looked)
        + ("; PATH" if not on_path else "")
        + ". It comes with QGIS (OSGeo4W / the standalone installer, the macOS app): "
          "start QGIS from its own shortcut, or reinstall QGIS.")


def describe(name: str = "ogr2ogr") -> str:
    """"<path> (<version>)" of the tool find_tool chose, "" before."""
    found = _FOUND.get(name)
    return f"{found[0]} ({found[1]})" if found else ""
