"""
Build the installable plugin zip: releases/QWebMap-<version>.zip.

The zip holds the plugin files tracked by git (no tests, tools, docs or
caches) in a ``QWebMap`` folder (the plugin's id in QGIS). Up to 4.8.1 the
folder was ``QGIS2VectorTilesFork``; the plugin warns when that old copy is
still installed.

Usage::

    python3 tools/build_release.py          # version from metadata.txt
    python3 tools/build_release.py --out /tmp/plugin.zip
    python3 tools/build_release.py --variant variant.json
    python3 tools/build_release.py --compare releases/QWebMap-4.4.1.zip

The files are read from the working tree, so a zip written into releases/
(the one that is committed and released) needs the plugin files committed:
with uncommitted changes in them it is refused. ``--compare`` builds the zip
of this checkout in a temporary folder and fails when the given zip's files
differ (the release workflow checks the committed zip with it).

A variant branch (e.g. hu-hesz, see docs/BRANCHES.md) has a ``variant.json``
at the repository root: ``{"suffix": "hu", "name": "QWebMap HÉSZ"}``.
Its zip is ``QWebMap-<version>-<suffix>.zip`` and the ``name`` in
the zipped metadata.txt is replaced; the folder and the version stay the same
(installing one replaces the other).
"""

import configparser
import json
import os
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDER = "QWebMap"
CONTENT = ["__init__.py", "metadata.txt", "LICENSE", "icon.png", "icon.svg", "resources", "src"]


def read_variant(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        variant = json.load(handle)
    if not str(variant.get("suffix", "")).replace("-", "").isalnum():
        raise SystemExit(f"{path}: 'suffix' must be letters/digits")
    return variant


def zip_differences(built, given):
    """Entries whose bytes differ between two plugin zips (dates ignored)."""
    with zipfile.ZipFile(built) as one, zipfile.ZipFile(given) as other:
        names, others = set(one.namelist()), set(other.namelist())
        differ = [f"only in the built zip: {name}" for name in sorted(names - others)]
        differ += [f"not in this commit: {name}" for name in sorted(others - names)]
        differ += [f"differs: {name}" for name in sorted(names & others)
                   if one.read(name) != other.read(name)]
    return differ


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    options = dict(zip(argv[::2], argv[1::2]))
    if "--compare" in options:
        given = os.path.abspath(options.pop("--compare"))
        with tempfile.TemporaryDirectory() as folder:
            built = os.path.join(folder, "check.zip")
            main([*sum(options.items(), ()), "--out", built])
            differ = zip_differences(built, given)
        if differ:
            print(f"{given} is not this commit's plugin ({len(differ)} files):", file=sys.stderr)
            print("\n".join(differ[:50]), file=sys.stderr)
            return 1
        print(f"{given}: the same files as this commit")
        return 0
    metadata = configparser.ConfigParser()
    metadata.read(os.path.join(ROOT, "metadata.txt"), encoding="utf-8")
    version = metadata["general"]["version"]
    variant = read_variant(options.get("--variant", os.path.join(ROOT, "variant.json")))
    if variant:
        version = f"{version}-{variant['suffix']}"
    files = subprocess.run(["git", "ls-files", "-z", *CONTENT], cwd=ROOT, capture_output=True,
                           text=True, check=True).stdout.split("\0")
    files = [path for path in files if path]
    out = os.path.abspath(options["--out"]) if "--out" in options else \
        os.path.join(ROOT, "releases", f"{FOLDER}-{version}.zip")
    if "--out" not in options:
        # The released zip must be the commit's files: uncommitted edits
        # would ship under a tag whose code differs.
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no", "--", *CONTENT],
                               cwd=ROOT, capture_output=True, text=True, check=True).stdout
        if dirty.strip():
            raise SystemExit(f"Commit the plugin files first (uncommitted changes):\n{dirty}")
    folders = set()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo(f"{FOLDER}/"), "")
        for path in sorted(files):
            parts = path.split("/")[:-1]
            for depth in range(1, len(parts) + 1):
                folder = f"{FOLDER}/{'/'.join(parts[:depth])}/"
                if folder not in folders:
                    folders.add(folder)
                    archive.writestr(zipfile.ZipInfo(folder), "")
            if path == "metadata.txt" and variant and variant.get("name"):
                with open(os.path.join(ROOT, path), encoding="utf-8") as handle:
                    text = handle.read()
                text = "\n".join(f"name={variant['name']}" if line.startswith("name=") else line
                                  for line in text.split("\n"))
                archive.writestr(f"{FOLDER}/{path}", text)
                continue
            archive.write(os.path.join(ROOT, path), f"{FOLDER}/{path}")
    print(f"{out}: {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
