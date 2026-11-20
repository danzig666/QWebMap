"""
Download the official go-pmtiles CLI for *tests only* (independent PMTiles reader).

    python3 tools/publishing/fetch_pmtiles_cli.py   # prints the binary path
    Q2VT_PMTILES_CLI=<path> pytest tests/unit/test_publishing_pmtiles.py

The plugin never downloads or runs this tool; it is a developer/CI dependency.
Each download is checked against its pinned SHA-256 before it is unpacked.
"""

import hashlib
import io
import os
import platform
import sys
import tarfile
import urllib.request
import zipfile

VERSION = "1.28.0"
ASSETS = {
    ("Linux", "x86_64"): f"go-pmtiles_{VERSION}_Linux_x86_64.tar.gz",
    ("Darwin", "arm64"): f"go-pmtiles-{VERSION}_Darwin_arm64.zip",
    ("Darwin", "x86_64"): f"go-pmtiles-{VERSION}_Darwin_x86_64.zip",
    ("Windows", "AMD64"): f"go-pmtiles_{VERSION}_Windows_x86_64.zip",
}
SHA256 = {  # of the release assets of VERSION
    f"go-pmtiles_{VERSION}_Linux_x86_64.tar.gz": "35c33b3881fabf2669f85455bd38e8102d76acd58802d7f310164e2bab1a5e23",
    f"go-pmtiles-{VERSION}_Darwin_arm64.zip": "cea173f68ceb41ccedb67378e87f82386e9f7f5326d042b4bcacacae189a56f1",
    f"go-pmtiles-{VERSION}_Darwin_x86_64.zip": "b3a211247caaac2f44d5499a9a2cd78fd707c2cbe457e30c4623bcd15476c8d5",
    f"go-pmtiles_{VERSION}_Windows_x86_64.zip": "a9170c68814347c397541772bfe4217c417597b450093a091959e8be8e7e40c7",
}


def main() -> int:
    asset = ASSETS.get((platform.system(), platform.machine()))
    if asset is None:
        print("No go-pmtiles build known for this platform.", file=sys.stderr)
        return 1
    cache = os.path.join(os.path.expanduser("~"), ".cache", "q2vt", f"go-pmtiles-{VERSION}")
    binary = os.path.join(cache, "pmtiles.exe" if os.name == "nt" else "pmtiles")
    if not os.path.exists(binary):
        url = f"https://github.com/protomaps/go-pmtiles/releases/download/v{VERSION}/{asset}"
        data = urllib.request.urlopen(url, timeout=120).read()
        digest = hashlib.sha256(data).hexdigest()
        if digest != SHA256[asset]:
            print(f"{asset}: SHA-256 {digest} != pinned {SHA256[asset]}", file=sys.stderr)
            return 1
        os.makedirs(cache, exist_ok=True)
        if asset.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                archive.extract(os.path.basename(binary), cache)
        else:
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                archive.extract("pmtiles", cache)
        os.chmod(binary, 0o755)
    print(binary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
