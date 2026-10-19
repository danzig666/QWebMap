#!/usr/bin/env bash
# Runs each test file given in its own pytest process (used by
# .github/workflows/tests.yml): a crash of QGIS in one file fails that file
# only, the others still run. JUnit reports go to test-reports/<title>/, a summary to
# the job summary. Exit 1 if any file failed.
set -u
title="$1"
shift
reports="test-reports/$(echo "${title}" | tr -c 'A-Za-z0-9\n' '-' | tr 'A-Z' 'a-z')"
mkdir -p "${reports}"
failed=()
passed=0
for file in "$@"; do
  name="$(echo "${file%.py}" | tr '/' '_')"
  echo "::group::${file}"
  start=$SECONDS
  python3 -m pytest -q -rfE -p no:cacheprovider --junitxml="${reports}/${name}.xml" "${file}"
  code=$?
  echo "::endgroup::"
  echo "${file}: exit ${code} in $((SECONDS - start)) s"
  case "${code}" in
    0|5) passed=$((passed + 1)) ;;  # 5: no tests collected (all skipped by conftest)
    *)
      failed+=("${file} (exit ${code}$([ "${code}" -ge 128 ] && echo ", crashed: signal $((code - 128))"))")
      ;;
  esac
done
# One annotation with every failed test and its first error line (the
# annotations stay readable through the API; the log is long).
report="$(REPORTS="${reports}" python3 - <<'PY'
import glob, os
import xml.etree.ElementTree as ET
lines = []
for path in sorted(glob.glob(os.environ["REPORTS"] + "/*.xml")):
    for case in ET.parse(path).getroot().iter("testcase"):
        for kind in ("failure", "error"):
            node = case.find(kind)
            if node is not None:
                first = (node.get("message") or node.text or "").strip().splitlines()
                # Where it failed: the last "path:line: Error" of the traceback.
                import re
                where = re.findall(r"^([\w./-]+\.py):(\d+): \w+", node.text or "", re.M)
                at = f" @ {where[-1][0].split('QWebMap/')[-1]}:{where[-1][1]}" if where else ""
                lines.append(f"{case.get('classname')}::{case.get('name')}: {first[0][:160] if first else kind}{at}")
print("\n".join(lines))
PY
)"
counts="$(REPORTS="${reports}" python3 - <<'PY'
import glob, os
import xml.etree.ElementTree as ET
total = {"tests": 0, "skipped": 0, "failures": 0, "errors": 0}
for path in glob.glob(os.environ["REPORTS"] + "/*.xml"):
    for suite in ET.parse(path).getroot().iter("testsuite"):
        for key in total:
            total[key] += int(suite.get(key, 0))
passed = total["tests"] - total["skipped"] - total["failures"] - total["errors"]
print(f"{passed} passed, {total['skipped']} skipped, {total['failures'] + total['errors']} failed")
PY
)"
echo "::notice title=${title}::${counts} (${passed} of $# files passed)"
{
  echo "### ${title}"
  echo "${passed} of $# test files passed: ${counts}."
  for item in "${failed[@]}"; do echo "- ❌ ${item}"; done
  [ -z "${report}" ] || { echo '```'; echo "${report}"; echo '```'; }
} >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
if [ ${#failed[@]} -gt 0 ]; then
  message="$(printf '%s\n' "${failed[@]}"; [ -z "${report}" ] || printf 'Failed tests:\n%s\n' "${report}")"
  message="${message:0:60000}"
  message="${message//'%'/'%25'}"
  message="${message//$'\n'/'%0A'}"
  echo "::error title=${title}: ${#failed[@]} of $# test files failed::${message}"
fi
# Annotations are cut at a few KB: the distinct errors (with a count and the
# first test that hit each) in several short ones, readable through the API.
if [ -n "${report}" ]; then
  REPORT="${report}" python3 - <<'PY' | while IFS= read -r chunk; do echo "::error title=${title} errors::${chunk}"; done
import os
groups = {}
for line in os.environ["REPORT"].splitlines():
    test, _, error = line.partition(": ")
    groups.setdefault(error[:200], []).append(test)
lines = [f"{len(tests)}x {error} [{tests[0]}]" for error, tests in
         sorted(groups.items(), key=lambda item: -len(item[1]))]
chunks, current = [], ""
for line in lines:
    if len(current) + len(line) > 3000:
        chunks.append(current)
        current = ""
    current += line + "\n"
if current:
    chunks.append(current)
for chunk in chunks[:8]:
    print(chunk.replace("%", "%25").replace("\n", "%0A"))
PY
fi
[ ${#failed[@]} -eq 0 ]
