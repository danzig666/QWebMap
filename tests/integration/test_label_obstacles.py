"""Point symbols as label obstacles: a point layer whose labeling has
"Features act as obstacles" (the QGIS default) keeps the other labels off
its symbols. The web map gets an invisible copy of each such symbol above
all labels (MapLibre places symbol layers top down: the copy is placed
first, the labels below keep clear of it); without labels, with obstacles
off, or with labels over their own point, none."""

import json
import os
import sys

from qgis.core import (Qgis, QgsFeature, QgsField, QgsGeometry, QgsMarkerSymbol,
                       QgsPalLayerSettings, QgsSingleSymbolRenderer, QgsTextFormat, QgsVectorLayer,
                       QgsVectorLayerSimpleLabeling)
from qgis.PyQt.QtCore import QVariant

from q2vt_fixtures import reset_project, to_geopackage, zoning_layer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_end_to_end import export  # noqa: E402,F401  pylint: disable=wrong-import-position,unused-import


def _points(path, symbol_props, labels=True, obstacle=True, placement=None):
    layer = QgsVectorLayer("Point?crs=EPSG:3857", "pois", "memory")
    layer.dataProvider().addAttributes([QgsField("name", QVariant.String)])
    layer.updateFields()
    features = []
    for i, (x, y) in enumerate([(2120500, 6020500), (2121500, 6021500)]):
        feature = QgsFeature(layer.fields())
        feature.setAttributes([f"P{i}"])
        feature.setGeometry(QgsGeometry.fromWkt(f"POINT({x} {y})"))
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    layer.updateExtents()
    layer = to_geopackage(layer, path)
    layer.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple(symbol_props)))
    if labels:
        settings = QgsPalLayerSettings()
        settings.fieldName = "name"
        settings.setFormat(QgsTextFormat())
        settings.obstacleSettings().setIsObstacle(obstacle)
        if placement is not None:
            settings.placement = placement
        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.setLabelsEnabled(True)
    return layer


def _style(result):
    with open(os.path.join(result, "style", "style.json"), encoding="utf-8") as handle:
        return json.load(handle)


def _labelled_zones(path):
    zones = zoning_layer(path=path)
    settings = QgsPalLayerSettings()
    settings.fieldName = "zone"
    settings.setFormat(QgsTextFormat())
    zones.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    zones.setLabelsEnabled(True)
    return zones


STAR = {"name": "star", "color": "200,0,0", "size": "4"}
DOT = {"name": "circle", "color": "0,0,200", "size": "3", "outline_style": "no"}


def test_point_symbols_of_an_obstacle_layer_get_a_copy_above_the_labels(export, tmp_path):  # noqa: F811
    points = _points(str(tmp_path / "pois.gpkg"), STAR)
    zones = _labelled_zones(str(tmp_path / "zones.gpkg"))
    reset_project(zones, points)
    _, result = export(points, keep_project=True)
    layers = _style(result)["layers"]
    obstacles = [l for l in layers if (l.get("metadata") or {}).get("q2vt:obstacle-of")]
    assert obstacles, [l["id"] for l in layers]
    ids = [l["id"] for l in layers]
    labels = [i for i, l in enumerate(layers) if l["type"] == "symbol" and "text-field" in l.get("layout", {})]
    layer_of = lambda i: ids[i][:3]  # noqa: E731 - "l00": the QGIS layer's number
    own = [i for i in labels if layer_of(i) == obstacles[0]["metadata"]["q2vt:obstacle-of"][:3]]
    others = [i for i in labels if i not in own]
    at = [ids.index(o["id"]) for o in obstacles]
    # Under the layer's own labels (QGIS: no feature is an obstacle to its
    # own label), placed before those of the layers after it.
    assert own and others and max(at) < min(own) and min(at) > max(others), ids
    for obstacle in obstacles:
        source = next(l for l in layers if l["id"] == obstacle["metadata"]["q2vt:obstacle-of"])
        layout = obstacle["layout"]
        assert obstacle["id"].startswith(source["id"]) and obstacle["paint"]["icon-opacity"] == 0
        assert layout["icon-allow-overlap"] is True and layout["icon-ignore-placement"] is False
        assert layout["icon-image"] == source["layout"]["icon-image"]
        assert obstacle.get("source-layer") == source.get("source-layer")
        # The symbol itself still never moves a label.
        assert source["layout"]["icon-ignore-placement"] is True


def test_a_plain_dot_gets_a_clear_square_of_its_size(export, tmp_path):  # noqa: F811
    points = _points(str(tmp_path / "pois.gpkg"), DOT)
    _, result = export(points)
    style = _style(result)
    layers = style["layers"]
    circles = [l for l in layers if l["type"] == "circle"]
    obstacles = [l for l in layers if (l.get("metadata") or {}).get("q2vt:obstacle-of")]
    assert circles and len(obstacles) == len(circles)
    assert obstacles[0]["metadata"]["q2vt:obstacle-of"] == circles[0]["id"]
    assert obstacles[0]["layout"]["icon-size"]


def test_no_obstacles_without_labels_with_obstacles_off_or_labels_over_the_point(export, tmp_path):  # noqa: F811
    for number, kwargs in enumerate([{"labels": False}, {"obstacle": False},
                                     {"placement": Qgis.LabelPlacement.OverPoint}]):
        points = _points(str(tmp_path / f"pois{number}.gpkg"), STAR, **kwargs)
        _, result = export(points)
        layers = _style(result)["layers"]
        assert not [l for l in layers if (l.get("metadata") or {}).get("q2vt:obstacle-of")], kwargs
