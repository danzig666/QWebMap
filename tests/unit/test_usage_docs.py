"""The user guide (docs/USAGE.md, published as docs/usage.html on GitHub
Pages) documents every option of the Publish window, and the HTML is built
from the current Markdown. A new checkbox, button, group or form row
without a line in the guide fails here: document it in docs/USAGE.md, then
run python3 tools/build_usage.py."""

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIALOGS = ["publish_dialog.py", "zoom_load_dialog.py", "scale_range.py", "r2_guide.py"]
WIDGETS = re.compile(r'(QCheckBox|QPushButton|QGroupBox|QRadioButton|addRow|QToolButton|addTab)'
                     r'\((?:[^()]*\(\)[^()]*,\s*)?\s*tr\(\s*"((?:[^"\\]|\\.)*)"')
# Plain dialog buttons, no option of their own.
GENERIC = {"Cancel", "Close", "Remove", "Browse…", "OK", "Apply"}


def _labels():
    labels = set()
    for name in DIALOGS:
        path = os.path.join(ROOT, "src", "gui", name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as handle:
            for match in WIDGETS.finditer(handle.read()):
                # A label split over lines: its first part; no trailing colon.
                label = match.group(2).replace('\\"', '"').strip().rstrip(":").strip()
                if label and label not in GENERIC:
                    labels.add(label)
    return labels


def _guide():
    with open(os.path.join(ROOT, "docs", "USAGE.md"), encoding="utf-8") as handle:
        return re.sub(r"\s+", " ", handle.read())


def test_every_publish_window_option_is_documented():
    guide = _guide()
    missing = sorted(label for label in _labels() if re.sub(r"\s+", " ", label) not in guide)
    assert not missing, "Not in docs/USAGE.md (add them, then run tools/build_usage.py):\n" + "\n".join(missing)


def test_the_html_guide_is_built_from_the_markdown():
    run = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_usage.py"), "--check"],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
