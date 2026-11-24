"""Polygon labels: the parts of each feature are dissolved before the label
point is placed. Shapes snapped to a coarse zoom's grid can be invalid (a
ring touching itself): GEOS failed the dissolve ("The algorithm returned no
output") and every label of the layer was lost."""

import pytest
from qgis.core import QgsProcessingException


@pytest.fixture
def exporter(plugin):
    from q2vt_plugin.src.core.rules_exporter import RulesExporter  # pylint: disable=import-error
    return RulesExporter.__new__(RulesExporter)


def test_a_failed_dissolve_is_repaired_and_redone(exporter, monkeypatch):
    calls = []

    def run(algorithm, algorithm_type="native", **params):
        calls.append((algorithm, params.get("INPUT")))
        if algorithm == "dissolve" and len(calls) == 1:
            raise QgsProcessingException("The algorithm returned no output.")
        return f"{algorithm}-out"
    monkeypatch.setattr(exporter, "_run_alg_safe", run)
    assert exporter._dissolve_parts("in") == "dissolve-out"  # pylint: disable=protected-access
    assert calls == [("dissolve", "in"), ("fixgeometries", "in"), ("dissolve", "fixgeometries-out")]


def test_parts_are_collected_when_even_the_repaired_dissolve_fails(exporter, monkeypatch):
    calls = []

    def run(algorithm, algorithm_type="native", **params):
        calls.append(algorithm)
        if algorithm == "dissolve":
            raise QgsProcessingException("TopologyException")
        return f"{algorithm}-out"
    monkeypatch.setattr(exporter, "_run_alg_safe", run)
    assert exporter._dissolve_parts("in") == "collect-out"  # pylint: disable=protected-access
    assert calls == ["dissolve", "fixgeometries", "dissolve", "collect"]


def test_repaired_invalid_polygons_dissolve(plugin):
    """The real algorithms: a self-touching ring that fails the dissolve is
    repaired by fixgeometries (structure method) and then dissolves."""
    import processing  # pylint: disable=import-outside-toplevel,import-error
    from qgis.core import (QgsFeature, QgsFeatureRequest, QgsGeometry,  # pylint: disable=import-outside-toplevel
                           QgsProcessingContext, QgsVectorLayer)
    layer = QgsVectorLayer("Polygon?crs=EPSG:3857&field=q2vt_orig_id:integer", "parts", "memory")
    shapes = ["POLYGON((0 0,10 0,10 10,0 10,0 0),(2 2,8 2,8 8,2 8,2 2),(5 2,6 5,5 8,4 5,5 2))",
              "POLYGON((0 0,10 10,10 0,0 10,0 0))", "POLYGON((20 0,30 0,30 10,20 10,20 0))"]
    features = []
    for wkt in shapes:
        feature = QgsFeature(layer.fields())
        feature.setAttributes([1])
        feature.setGeometry(QgsGeometry.fromWkt(wkt))
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    context = QgsProcessingContext()
    context.setInvalidGeometryCheck(QgsFeatureRequest.InvalidGeometryCheck.GeometryNoCheck)
    fixed = processing.run("native:fixgeometries", {"INPUT": layer, "METHOD": 1, "OUTPUT": "memory:"},
                           context=context)["OUTPUT"]
    out = processing.run("native:dissolve", {"INPUT": fixed, "FIELD": ["q2vt_orig_id"], "OUTPUT": "memory:"},
                         context=context)["OUTPUT"]
    assert out.featureCount() == 1 and not next(out.getFeatures()).geometry().isEmpty()
