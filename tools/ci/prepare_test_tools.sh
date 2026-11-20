#!/usr/bin/env bash
# Tools the unit tests compare against (.github/workflows/tests.yml, qt6.yml),
# after prepare_qgis_container.sh and setup-node: MapLibre's readable build
# (tools/maplibre, the label-angle port's parity test), a moto S3 server for
# the real vendored boto3 (test_publishing_s3_moto.py) and the official
# go-pmtiles CLI (test_publishing_pmtiles.py). With Q2VT_REQUIRE_TOOLS=1 the
# tests fail instead of skipping when one of them is missing.
set -euo pipefail
trap 'echo "::error title=test tools::line ${LINENO}: ${BASH_COMMAND} (exit $?)"' ERR
node --version
(cd tools/maplibre && npm ci --no-audit --no-fund --ignore-scripts)
# Its own folder: moto brings its own boto3, which must not shadow the
# vendored one in the test process (only the server sees this path).
python3 -m pip install --quiet --break-system-packages --target /opt/q2vt-moto "moto[server]==5.2.5"
pmtiles="$(python3 tools/publishing/fetch_pmtiles_cli.py)"
{
  echo "Q2VT_MOTO_PATH=/opt/q2vt-moto"
  echo "Q2VT_PMTILES_CLI=${pmtiles}"
} >> "${GITHUB_ENV:-/dev/null}"
