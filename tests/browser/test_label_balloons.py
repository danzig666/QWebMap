"""Balloon callouts in the browser (idea of QGIS2VectorTiles 4.2): the
label's icon stretched to its text keeps its wedge on the point for short
and long texts alike, and its box around the text."""

import os
import sys

import pytest

from publishing.controller import export_local
from publishing.preview_server import PreviewServer

HERE = os.path.dirname(os.path.abspath(__file__))
FILL = (255, 255, 0)


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "integration"))
    from test_publishing_pipeline import EXTENT  # pylint: disable=import-error
    from publishing.models import LayerConfig, PublicationProfile
    from q2vt_fixtures import reset_project, to_geopackage
    from qgis.core import (QgsBalloonCallout, QgsFeature, QgsFillSymbol, QgsGeometry, QgsMarkerSymbol,
                           QgsPalLayerSettings, QgsSingleSymbolRenderer, QgsTextFormat, QgsVectorLayer,
                           QgsVectorLayerSimpleLabeling, Qgis)
    base = tmp_path_factory.mktemp("balloons")
    project = reset_project()
    layer = QgsVectorLayer("Point?crs=EPSG:3857&field=name:string", "Kutak", "memory")
    for x, name in ((2120300, "Kút"), (2121300, "Nagyon hosszú kút neve")):
        feature = QgsFeature(layer.fields())
        feature.setAttributes([name])
        feature.setGeometry(QgsGeometry.fromWkt(f"POINT({x} 6021000)"))
        layer.dataProvider().addFeatures([feature])
    layer = to_geopackage(layer, str(base / "kutak.gpkg"))
    layer.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple({"size": "0.01"})))
    settings = QgsPalLayerSettings()
    settings.fieldName, settings.placement = "name", Qgis.LabelPlacement.OverPoint
    settings.quadOffset = Qgis.LabelQuadrantPosition.AboveRight
    settings.xOffset, settings.yOffset, settings.offsetUnits = 5, -5, Qgis.RenderUnit.Millimeters
    text_format = QgsTextFormat()
    text_format.setSize(11)
    settings.setFormat(text_format)
    balloon = QgsBalloonCallout()
    balloon.setFillSymbol(QgsFillSymbol.createSimple({"color": "255,255,0", "outline_style": "no"}))
    balloon.setEnabled(True)
    settings.setCallout(balloon)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)
    project.addMapLayer(layer)
    profile = PublicationProfile(title="Kutak", slug="kutak", locale="en")
    profile.view.min_zoom, profile.view.max_zoom = 13, 15
    profile.view.extent = [EXTENT.xMinimum(), EXTENT.yMinimum(), EXTENT.xMaximum(), EXTENT.yMaximum()]
    profile.output.local_directory = str(base / "out")
    profile.layers = [LayerConfig(layer.id(), initially_visible=True)]
    profile.interaction.panel_closed = True
    result = export_local(project, profile, EXTENT)
    with PreviewServer(os.path.dirname(result.publication_dir)) as server:
        yield server.url(f"{profile.slug}/index.html")


POINTS = """const m = q2vtViewer.map;
  const lngLat = ([x, y]) => [x / 20037508.342789244 * 180,
    Math.atan(Math.sinh(y / 20037508.342789244 * Math.PI)) * 180 / Math.PI];
  m.jumpTo({ center: lngLat([2120800, 6021000]), zoom: 14 });
  await new Promise((r) => setTimeout(r, 2500));
  return [[2120300, 6021000], [2121300, 6021000]].map((xy) => {
    const p = m.project(lngLat(xy));
    return [p.x, p.y];
  });"""


def test_balloon_wedges_stay_on_their_points(site, tmp_path):
    sys.path.insert(0, HERE)
    from test_web_viewer_views import _run  # pylint: disable=import-error
    from PIL import Image
    shot = tmp_path / "balloons.png"
    (points,) = [r for r in _run(site, [{"eval": POINTS}, {"screenshot": str(shot)}], tmp_path,
                                 width=900, height=500) if r is not None][:1]
    image = Image.open(shot).convert("RGB")

    def yellow(x, y):
        r, g, b = image.getpixel((int(round(x)), int(round(y))))
        return r > 200 and g > 200 and b < 120
    for x, y in points:
        # The wedge reaches the point (QGIS: the tip on it), the box is up and right.
        near_tip = any(yellow(x + dx, y + dy) for dx in range(0, 4) for dy in range(-3, 1))
        assert near_tip, (x, y)
        assert yellow(x + 25, y - 22), (x, y)  # inside the balloon above right
        assert not yellow(x - 6, y + 6), (x, y)  # nothing below left of the point
