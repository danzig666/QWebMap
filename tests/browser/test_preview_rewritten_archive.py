"""A preview page left open while the map is exported again (the export
rewrites data/map.pmtiles in place) draws the new archive whole.

It read the new file at the old file's offsets: tiles of a zoom or an area
went missing (parcel outlines vanished at one zoom and came back further in).
The preview server now sends a strong ETag, so the PMTiles reader sees the
change and reloads the archive's header."""

import json
import math
import os
import shutil
import subprocess
import threading
import time

import numpy as np
import pytest
from PIL import Image
from qgis.core import (QgsFeature, QgsFillSymbol, QgsGeometry, QgsRectangle, QgsSingleSymbolRenderer,
                       QgsVectorLayer)

from publishing.controller import export_local
from publishing.models import LayerConfig, PublicationProfile
from publishing.preview_server import PreviewServer
from q2vt_fixtures import reset_project

HERE = os.path.dirname(os.path.abspath(__file__))
X0, Y0, CELL, N = 2119000.0, 6019000.0, 40.0, 60  # 2.4 km of 40 m parcels
CENTRE = (math.degrees((X0 + 1000) / 6378137),  # inside both exports
          math.degrees(math.atan(math.sinh((Y0 + 1200) / 6378137))))
ZOOMS = [15, 16, 17]


def _parcels():
    layer = QgsVectorLayer("Polygon?crs=EPSG:3857&field=hrsz:string", "Parcels", "memory")
    features = []
    for i in range(N):
        for j in range(N):
            feature = QgsFeature(layer.fields())
            feature.setAttributes([f"{i}/{j}"])
            x, y = X0 + i * CELL, Y0 + j * CELL
            feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(x, y, x + CELL * 0.9, y + CELL * 0.9)))
            features.append(feature)
    layer.dataProvider().addFeatures(features)
    layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple(
        {"color": "0,0,0,0", "outline_color": "0,0,0", "outline_width": "0.6"})))
    return layer


@pytest.fixture(scope="module")
def exports(tmp_path_factory):
    base = tmp_path_factory.mktemp("rewritten")
    project = reset_project()
    layer = _parcels()
    project.addMapLayer(layer)
    full = QgsRectangle(X0, Y0, X0 + N * CELL, Y0 + N * CELL)
    smaller = QgsRectangle(X0, Y0, X0 + N * CELL * 0.7, Y0 + N * CELL)  # other tiles, other offsets
    out = []
    for name, extent in (("old", full), ("new", smaller)):
        profile = PublicationProfile(title="Parcels", slug="parcels", locale="en")
        profile.view.min_zoom, profile.view.max_zoom = 12, 17
        profile.output.local_directory = str(base / name)
        profile.layers = [LayerConfig(layer.id())]
        out.append(export_local(project, profile, extent).publication_dir)
    return out


def _run(folder, tmp_path, tag, swap_from=None):
    actions = [{"eval": f"q2vtViewer.map.jumpTo({{center:[{CENTRE[0]},{CENTRE[1]}],zoom:13}}); return 1;"},
               {"idle": True}, {"wait": 3000 if swap_from else 0}]
    for zoom in ZOOMS:
        actions += [{"eval": f"q2vtViewer.map.jumpTo({{center:[{CENTRE[0]},{CENTRE[1]}],zoom:{zoom}}}); return 1;"},
                    {"idle": True}, {"wait": 400}, {"screenshot": str(tmp_path / f"{tag}_{zoom}.png")}]
    path = tmp_path / f"{tag}.json"
    path.write_text(json.dumps(actions))
    with PreviewServer(folder) as server:
        if swap_from:
            def swap():  # the map exported again while the page is open
                time.sleep(1.5)
                shutil.copyfile(os.path.join(swap_from, "data", "map.pmtiles"),
                                os.path.join(folder, "data", "map.pmtiles"))
            threading.Thread(target=swap, daemon=True).start()
        run = subprocess.run(["node", "interact.mjs", server.url("index.html") + "?embed", str(path), "800", "600"],
                             capture_output=True, text=True, cwd=HERE, timeout=300)
    assert run.returncode == 0, run.stderr[-3000:]
    return json.loads(run.stdout.strip().splitlines()[-1])


def test_open_preview_reads_the_rewritten_archive_whole(exports, tmp_path):
    old, new = exports
    reference = _run(new, tmp_path, "fresh")
    assert not reference["pageErrors"] and not reference["console"], reference
    swapped = _run(old, tmp_path, "swapped", swap_from=new)
    assert not swapped["pageErrors"], swapped
    assert not [m for m in swapped["console"] if "416" in m], swapped["console"]
    for zoom in ZOOMS:
        a, b = (np.asarray(Image.open(tmp_path / f"{tag}_{zoom}.png").convert("L"), np.int16)
                for tag in ("fresh", "swapped"))
        lines = (a < 128).sum()
        assert lines > 2000, (zoom, lines)  # parcel outlines drawn
        assert np.abs(a - b).mean() < 1.0, zoom  # the same map as a fresh page of the new export
