"""Horizontal polygon labels where QGIS puts them (pal's candidate costs:
room from the polygon's and the map's edges, then nearness to the
centroid), not at the roomiest point: on a long, slightly tapering strip
QGIS labels the middle; the viewer labelled the wide end."""

import json
import math
import os
import subprocess

import pytest
from qgis.core import (Qgis, QgsCoordinateReferenceSystem, QgsFeature, QgsFillSymbol, QgsGeometry,
                       QgsMapRendererSequentialJob, QgsMapSettings, QgsPalLayerSettings, QgsPointXY,
                       QgsProject, QgsRectangle, QgsSingleSymbolRenderer, QgsTextFormat, QgsVectorLayer,
                       QgsVectorLayerSimpleLabeling)
from qgis.PyQt.QtCore import QSize

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.join(os.path.dirname(os.path.dirname(HERE)), "resources", "ml_viewer", "visible_labels.mjs")
WORLD = 2 * math.pi * 6378137
X0, Y0 = 2119000.0, 6020000.0
W, H = 900, 700

SCRIPT = """
import { polygonSpot, roomiestPoint } from %s;
const { rings, view, perPx } = JSON.parse(process.argv[1]);
const spot = polygonSpot(rings, view, perPx);
console.log(JSON.stringify({ spot: spot && spot.point, pole: roomiestPoint(rings, perPx).point }));
"""


def _strip(name, ring):
    layer = QgsVectorLayer("Polygon?crs=EPSG:3857&field=t:string", name, "memory")
    feature = QgsFeature(layer.fields())
    feature.setAttributes(["ld. a Tm-3Sz"])
    feature.setGeometry(QgsGeometry.fromPolygonXY([[QgsPointXY(x, y) for x, y in ring]]))
    layer.dataProvider().addFeatures([feature])
    layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "255,255,255"})))
    settings = QgsPalLayerSettings()
    settings.fieldName = "t"
    settings.placement = Qgis.LabelPlacement.Horizontal
    text = QgsTextFormat()
    text.setSize(40)
    text.setSizeUnit(Qgis.RenderUnit.MapUnits)
    settings.setFormat(text)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)
    return layer


@pytest.mark.parametrize("zoom", [15, 15.5])
def test_horizontal_label_spot_is_qgis(zoom):
    # 1300 m long, 300 m wide at the left end, 340 m at the right end.
    ring = [(X0, Y0), (X0 + 1300, Y0 - 20), (X0 + 1300, Y0 + 320), (X0, Y0 + 300), (X0, Y0)]
    layer = _strip("Strip", ring)
    QgsProject.instance().addMapLayer(layer)
    try:
        mpp = WORLD / (512 * 2 ** zoom)
        cx, cy = X0 + 650, Y0 + 150
        extent = QgsRectangle(cx - W / 2 * mpp, cy - H / 2 * mpp, cx + W / 2 * mpp, cy + H / 2 * mpp)
        settings = QgsMapSettings()
        settings.setLayers([layer])
        settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
        settings.setOutputSize(QSize(W, H))
        settings.setExtent(extent)
        job = QgsMapRendererSequentialJob(settings)
        job.start()
        job.waitForFinished()
        labels = job.takeLabelingResults().allLabels()
        assert labels
        qgis = labels[0].labelRect.center()
        world = lambda x, y: [x / WORLD + 0.5, 0.5 - y / WORLD]
        data = {"rings": [[world(x, y) for x, y in ring[:-1]]],
                "view": world(extent.xMinimum(), extent.yMaximum()) + world(extent.xMaximum(), extent.yMinimum()),
                "perPx": 1 / (512 * 2 ** zoom)}
        url = "file://" + MODULE.replace(os.sep, "/")
        run = subprocess.run(["node", "--input-type=module", "-e", SCRIPT % json.dumps(url), json.dumps(data)],
                             capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stderr[-2000:]
        out = json.loads(run.stdout.strip().splitlines()[-1])
        px = lambda p: ((p[0] - data["view"][0]) * 512 * 2 ** zoom, (p[1] - data["view"][1]) * 512 * 2 ** zoom)
        target = ((qgis.x() - extent.xMinimum()) / mpp, (extent.yMaximum() - qgis.y()) / mpp)
        spot, pole = px(out["spot"]), px(out["pole"])
        assert math.dist(spot, target) <= 13, (spot, target)  # QGIS's candidate (24 px grid)
        assert math.dist(pole, target) > 100, (pole, target)  # the roomiest point: the wide end
    finally:
        QgsProject.instance().removeMapLayer(layer.id())
