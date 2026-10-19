#!/usr/bin/env bash
# Prepares the official QGIS image for the tests (.github/workflows/tests.yml):
# pytest, an OpenSSH server for the SSH/SFTP publishing tests, and the
# checkout linked into the QGIS profile as the plugin (docs/fidelity/TESTING.md).
set -euo pipefail
trap 'echo "::error title=prepare::line ${LINENO}: ${BASH_COMMAND} (exit $?)"' ERR
# Tools some images lack (the QGIS 4 / Qt6 image: no git, no pip).
missing=()
command -v git >/dev/null || missing+=(git)
command -v pip3 >/dev/null || missing+=(python3-pip)
command -v curl >/dev/null || missing+=(curl)
if [ "${#missing[@]}" -gt 0 ]; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${missing[@]}" >/dev/null
fi
git config --global --add safe.directory "*"
python3 -c "import qgis.core, osgeo.gdal" # fail early: without QGIS the tests are skipped silently
# The version used locally (Ubuntu 24.04). Where pip cannot install into
# the system (the QGIS 4 image), a virtualenv that sees the system's QGIS,
# first on PATH for the later steps (pytest 8 imports the repository's
# __init__.py as a package: the tests need 7.4).
if ! pip3 install --quiet --break-system-packages "pytest==7.4.4"; then
  { apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv >/dev/null; } || true
  python3 -m venv --system-site-packages /opt/q2vt-venv
  /opt/q2vt-venv/bin/pip install --quiet "pytest==7.4.4"
  export PATH="/opt/q2vt-venv/bin:${PATH}"
  [ -z "${GITHUB_PATH:-}" ] || echo "/opt/q2vt-venv/bin" >> "${GITHUB_PATH}"
fi
python3 -m pytest --version
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq openssh-server >/dev/null
profile="$(python3 -c "from qgis.core import QgsApplication; app = QgsApplication([], False); app.initQgis(); print(app.qgisSettingsDirPath())" 2>/dev/null | tail -1)"
mkdir -p "${profile}python/plugins"
ln -sfn "${PWD}" "${profile}python/plugins/QWebMap"
echo "QGIS $(python3 -c 'from qgis.core import Qgis; print(Qgis.QGIS_VERSION)'), Python $(python3 -V), plugin linked in ${profile}"
