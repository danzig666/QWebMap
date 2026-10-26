"""Raster layers on the web map as sharp as QGIS draws them (bilinear
resampling, transparent white, WebP 85): a plan-like image of one-pixel
coloured lines and specks, compared with QGIS's own render of the same view
by mean edge contrast. It was 70-85 % of QGIS's: the tiles stopped at the
image's resolution (enlarged twice beyond it: two bilinear passes), MapLibre
loaded tiles enlarged up to 1.41x between zoom levels and on scaled screens,
and drew shrunk tiles from half-size mipmaps."""

import json
import math
import os
import subprocess
import sys

import numpy as np
import pytest
from osgeo import gdal, osr
from PIL import Image
from qgis.core import (QgsBilinearRasterResampler, QgsCoordinateReferenceSystem, QgsFeature, QgsGeometry,
                       QgsMapRendererParallelJob, QgsMapSettings, QgsRasterLayer, QgsRasterTransparency,
                       QgsRectangle, QgsVectorLayer)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor

from publishing.controller import export_local
from publishing.models import LayerConfig, PublicationProfile
from publishing.preview_server import PreviewServer

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGIN = (2119000.0, 6023000.0)
PIXEL = 0.5   # Web Mercator m: 0.34 ground m at 47.5° N
SIZE = 1600
W, H = 600, 400


def _plan_image(path):
    rng = np.random.default_rng(1)
    img = np.full((SIZE, SIZE, 3), 255, np.uint8)
    for i, (width, colour) in enumerate([(1, (220, 0, 0)), (2, (0, 90, 220)), (3, (0, 150, 0)),
                                         (1, (0, 0, 0))] * 12):
        x = 30 + i * 32
        img[:, x:x + width] = colour
        img[x:x + width, :] = colour
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    img[((xx + yy) % 23) == 0] = (120, 0, 140)
    for _ in range(4000):  # text-like specks
        y, x = rng.integers(0, SIZE - 3, 2)
        img[y:y + 2, x:x + rng.integers(1, 4)] = (0, 0, 0)
    ds = gdal.GetDriverByName("GTiff").Create(str(path), SIZE, SIZE, 3, gdal.GDT_Byte)
    ds.SetGeoTransform([ORIGIN[0], PIXEL, 0, ORIGIN[1], 0, -PIXEL])
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3857)
    ds.SetProjection(srs.ExportToWkt())
    for band in range(3):
        ds.GetRasterBand(band + 1).WriteArray(img[..., band])
    ds = None
    return str(path)


def _edges(pixels):
    grey = np.asarray(Image.fromarray(pixels).convert("L"), np.float32)
    return float(np.abs(np.diff(grey, axis=0)).mean() + np.abs(np.diff(grey, axis=1)).mean())


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "integration"))
    from q2vt_fixtures import reset_project  # pylint: disable=import-error
    base = tmp_path_factory.mktemp("sharp")
    project = reset_project()
    plan = QgsRasterLayer(_plan_image(base / "plan.tif"), "Terv")
    white = QgsRasterTransparency.TransparentThreeValuePixel()
    white.red = white.green = white.blue = 255
    white.percentTransparent = 100
    transparency = QgsRasterTransparency()
    transparency.setTransparentThreeValuePixelList([white])
    plan.renderer().setRasterTransparency(transparency)
    plan.resampleFilter().setZoomedInResampler(QgsBilinearRasterResampler())
    plan.resampleFilter().setZoomedOutResampler(QgsBilinearRasterResampler())
    marks = QgsVectorLayer("Point?crs=EPSG:3857&field=n:integer", "Jelek", "memory")
    feature = QgsFeature(marks.fields())
    feature.setAttributes([1])
    feature.setGeometry(QgsGeometry.fromWkt(f"POINT({ORIGIN[0] + 5} {ORIGIN[1] - 5})"))
    marks.dataProvider().addFeatures([feature])
    project.addMapLayer(plan)
    project.addMapLayer(marks)
    profile = PublicationProfile(title="Terv", slug="terv", locale="hu")
    profile.view.min_zoom, profile.view.max_zoom = 14, 19
    profile.output.local_directory = str(base / "out")
    profile.layers = [LayerConfig(plan.id()), LayerConfig(marks.id(), initially_visible=False)]
    extent = QgsRectangle(ORIGIN[0], ORIGIN[1] - SIZE * PIXEL, ORIGIN[0] + SIZE * PIXEL, ORIGIN[1])
    result = export_local(project, profile, extent)
    with PreviewServer(os.path.dirname(result.publication_dir)) as server:
        yield {"url": server.url("terv/index.html") + "?embed", "layer": plan, "centre": extent.center(),
               "base": base}


def _compare(site, zoom, ratio, tmp_path):
    cx, cy = site["centre"].x(), site["centre"].y()
    lon = cx / 6378137 * 180 / math.pi
    lat = math.degrees(math.atan(math.sinh(cy / 6378137)))
    shot = str(tmp_path / f"web_{zoom}_{ratio}.png")
    actions = [{"eval": "const m = q2vtViewer.map; "
                        f"m.jumpTo({{ center: [{lon}, {lat}], zoom: {zoom} }}); "
                        "for (const l of m.getStyle().layers) if (l.type === 'background') "
                        "m.setPaintProperty(l.id, 'background-color', '#ffffff'); "
                        "const s = Object.values(m.getStyle().sources).filter((s) => s.type === 'raster'); "
                        "return s.map((x) => [x.tileSize, x.maxzoom]);"},
               {"idle": True}, {"wait": 800}, {"screenshot": shot}]
    path = tmp_path / f"actions_{zoom}_{ratio}.json"
    path.write_text(json.dumps(actions))
    run = subprocess.run(["node", "interact.mjs", site["url"], str(path), str(W), str(H)], capture_output=True,
                         text=True, cwd=HERE, timeout=300, env={**os.environ, "Q2VT_DSF": str(ratio)})
    assert run.returncode == 0, run.stderr[-3000:]
    out = json.loads(run.stdout.strip().splitlines()[-1])
    assert not out["pageErrors"], out
    metres = 2 * math.pi * 6378137 / (512 * 2 ** zoom)
    settings = QgsMapSettings()
    settings.setLayers([site["layer"]])
    settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
    settings.setOutputSize(QSize(W, H))
    settings.setDevicePixelRatio(ratio)
    settings.setBackgroundColor(QColor(255, 255, 255))
    settings.setExtent(QgsRectangle(cx - W / 2 * metres, cy - H / 2 * metres, cx + W / 2 * metres, cy + H / 2 * metres))
    job = QgsMapRendererParallelJob(settings)
    job.start()
    job.waitForFinished()
    qgis = str(tmp_path / f"qgis_{zoom}_{ratio}.png")
    job.renderedImage().save(qgis)
    web, ref = (np.asarray(Image.open(p).convert("RGB")) for p in (shot, qgis))
    half = int(120 * ratio)  # the middle of the map (no controls)
    y, x = min(web.shape[0], ref.shape[0]) // 2, min(web.shape[1], ref.shape[1]) // 2
    crop = (slice(y - half, y + half), slice(x - half, x + half))
    return _edges(web[crop]) / _edges(ref[crop]), out["results"][0]


@pytest.mark.parametrize("zoom,ratio", [(17.5, 1), (18.5, 1), (19.5, 1), (17.25, 1.25), (19, 1.25), (18.5, 2)])
def test_raster_as_sharp_as_qgis(site, tmp_path, zoom, ratio):
    sharpness, sources = _compare(site, zoom, ratio, tmp_path)
    (tile_size, max_zoom), = sources
    # "Like the image": one zoom finer than the image (0.34 m: zoom 19), and
    # tiles loaded finer than the screen (never enlarged).
    assert max_zoom == 20 and tile_size == math.floor(256 / (ratio * 1.4))
    assert sharpness >= 0.85, sharpness
