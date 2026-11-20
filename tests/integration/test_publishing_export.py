"""Exporter hooks for publishing (PUB-02/05): explicit layer selection
(hidden layers included, tree untouched), PMTiles / Both archives, no
result layer when asked, Processing outputs, ExportBundle."""

import os

from qgis.core import (QgsApplication, QgsFillSymbol, QgsProcessingContext, QgsProject,
                       QgsRectangle, QgsSingleSymbolRenderer)

from q2vt_fixtures import reset_project, zoning_layer
from publishing.validation import compare_archives, validate_pmtiles

EXTENT = QgsRectangle(2119000, 6019000, 2123000, 6023000)


def _layers(tmp_path):
    shown = zoning_layer("shown", path=str(tmp_path / "shown.gpkg"))
    hidden = zoning_layer("hidden", path=str(tmp_path / "hidden.gpkg"))
    for layer, color in ((shown, "red"), (hidden, "blue")):
        layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": color})))
    project = reset_project(shown, hidden)
    project.layerTreeRoot().findLayer(hidden.id()).setItemVisibilityChecked(False)
    return project, shown, hidden


def _tree_state(project):
    return [(node.layer().id(), node.isVisible()) for node in project.layerTreeRoot().findLayers()]


def _exporter(plugin, tmp_path, **kwargs):
    from q2vt_plugin.src.qgis2vectortiles import QGIS2VectorTiles  # pylint: disable=import-error
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    return QGIS2VectorTiles(min_zoom=10, max_zoom=12, extent=EXTENT, output_dir=str(out),
                            serve=False, **kwargs)


def test_selected_layers_include_hidden_ones_without_touching_the_tree(plugin, tmp_path):
    project, shown, hidden = _layers(tmp_path)
    before = _tree_state(project)
    layer_count = len(project.mapLayers())
    exporter = _exporter(plugin, tmp_path, layer_ids=[hidden.id()], archive_format="both",
                         add_result_layer=False)
    result = exporter.convert_project_to_vector_tiles()
    assert result
    assert _tree_state(project) == before  # A22: visibility unchanged
    assert len(project.mapLayers()) == layer_count  # no "Vector Tiles" layer added
    owners = {rule.layer.id() for rule in exporter.rules}
    assert owners == {hidden.id()}  # only the selected (hidden) layer
    assert os.path.exists(os.path.join(result, "tiles.mbtiles"))
    compare_archives(os.path.join(result, "tiles.mbtiles"), os.path.join(result, "tiles.pmtiles"))
    validate_pmtiles(os.path.join(result, "tiles.pmtiles"), sample=0)
    bundle = exporter.export_bundle("d7671cb1-c2e2-4c1a-8f54-111111111111")
    assert bundle.mbtiles_path.endswith("tiles.mbtiles") and bundle.style["layers"]
    west, south, east, north = bundle.bounds_wgs84
    assert 19 < west < east < 20 and 47 < south < north < 48
    assert bundle.tile_zooms == (10, 12)


def test_legacy_default_exports_visible_layers_only(plugin, tmp_path):
    _, shown, _ = _layers(tmp_path)
    exporter = _exporter(plugin, tmp_path)
    assert exporter.convert_project_to_vector_tiles()
    assert {rule.layer.id() for rule in exporter.rules} == {shown.id()}
    assert exporter.archive_format == "mbtiles" and exporter.pmtiles is None
    assert not os.path.exists(os.path.join(exporter.output_path, "tiles.pmtiles"))


def test_pmtiles_only_keeps_no_mbtiles_and_adds_no_layer(plugin, tmp_path):
    project, shown, _ = _layers(tmp_path)
    count = len(project.mapLayers())
    exporter = _exporter(plugin, tmp_path, archive_format="pmtiles")
    result = exporter.convert_project_to_vector_tiles()
    assert os.path.exists(os.path.join(result, "tiles.pmtiles"))
    assert not os.path.exists(os.path.join(result, "tiles.mbtiles"))
    assert len(project.mapLayers()) == count


_PROVIDERS = []


def test_processing_algorithm_returns_archive_outputs(plugin, tmp_path, monkeypatch):
    from qgis.core import QgsProcessingFeedback  # pylint: disable=import-outside-toplevel
    from q2vt_plugin.src.core.server_initializer import ServerInitializer  # noqa  pylint: disable=import-error
    # The algorithm always starts the local tile server (port 9000, used by the browser tests).
    monkeypatch.setattr(ServerInitializer, "_launch_server", lambda *args, **kwargs: None)
    _layers(tmp_path)
    provider_id = "QGIS2VectorTilesFork"
    registry = QgsApplication.processingRegistry()
    alg = registry.algorithmById(f"{provider_id}:QGIS2VectorTiles_action")
    if alg is None:
        from q2vt_plugin.src.processing.provider import QGIS2VectorTilesPorvider  # noqa  pylint: disable=import-error
        # Kept referenced: a garbage-collected Python provider stays registered
        # as an empty one (id "", no algorithms).
        _PROVIDERS.append(QGIS2VectorTilesPorvider())
        registry.addProvider(_PROVIDERS[-1])
        alg = registry.algorithmById(f"{provider_id}:QGIS2VectorTiles_action")
    out = tmp_path / "proc"
    params = {"MIN_ZOOM": 10, "MAX_ZOOM": 11, "EXTENT": "2119000,2123000,6019000,6023000 [EPSG:3857]",
              "CPU_PERCENT": 50, "FIELDS_INCLUDED": 0, "BACKGROUND_TYPE": 2, "VIEWER": 0,
              "FIDELITY_MODE": 0, "OVERZOOM": 0, "STATIC_PACKAGE": False,
              "TILE_ARCHIVE_FORMAT": 2, "OUTPUT_DIR": str(out)}
    context = QgsProcessingContext()
    context.setProject(QgsProject.instance())
    results, ok = alg.run(params, context, QgsProcessingFeedback())
    assert ok, results
    assert os.path.exists(results["PMTILES"]) and os.path.exists(results["MBTILES"])
    # Old parameter sets (no TILE_ARCHIVE_FORMAT) keep the MBTiles-only output.
    del params["TILE_ARCHIVE_FORMAT"]
    params["OUTPUT_DIR"] = str(tmp_path / "proc_old")
    results, ok = alg.run(params, context, QgsProcessingFeedback())
    assert ok and "PMTILES" not in results and os.path.exists(results["MBTILES"])


def _fake_algorithm(monkeypatch):
    """The Processing algorithm with the exporter replaced: what it is given."""
    from q2vt_plugin.src.processing import algorithms  # pylint: disable=import-error
    seen = {}

    class Exporter:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        def convert_project_to_vector_tiles(self):
            return seen["output_dir"]
    monkeypatch.setattr(algorithms, "QGIS2VectorTiles", Exporter)
    algorithm = algorithms.QGIS2VectorTilesAlgorithm()
    algorithm.initAlgorithm()
    return algorithm, seen


def test_processing_extent_without_crs_is_in_the_project_crs(plugin, tmp_path, monkeypatch):
    """An extent without [EPSG:...] was used as Web Mercator (an EOV box
    landed in the Gulf of Guinea); QGIS reads it in the project CRS."""
    import pytest  # pylint: disable=import-outside-toplevel
    from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransform,  # pylint: disable=import-outside-toplevel
                           QgsProcessingException, QgsProcessingFeedback)
    algorithm, seen = _fake_algorithm(monkeypatch)
    project = reset_project()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:23700"))
    context = QgsProcessingContext()
    context.setProject(project)
    eov = QgsRectangle(640000, 230000, 660000, 250000)
    expected = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:23700"),
                                      QgsCoordinateReferenceSystem("EPSG:3857"), project).transformBoundingBox(eov)
    params = {"MIN_ZOOM": 10, "MAX_ZOOM": 11, "OUTPUT_DIR": str(tmp_path / "out")}
    for value in ("640000,660000,230000,250000", "640000,660000,230000,250000 [EPSG:23700]"):
        seen.clear()
        algorithm.processAlgorithm(dict(params, EXTENT=value), context, QgsProcessingFeedback())
        box = seen["extent"]
        for got, want in zip((box.xMinimum(), box.yMinimum(), box.xMaximum(), box.yMaximum()),
                             (expected.xMinimum(), expected.yMinimum(), expected.xMaximum(), expected.yMaximum())):
            assert abs(got - want) < 1.0, (value, box.toString(), expected.toString())
    seen.clear()  # an extent given in Web Mercator stays as it is
    algorithm.processAlgorithm(dict(params, EXTENT="2119000,2123000,6019000,6023000 [EPSG:3857]"),
                               context, QgsProcessingFeedback())
    assert seen["extent"] == EXTENT
    with pytest.raises(QgsProcessingException):  # no extent: not a Null rectangle
        algorithm.processAlgorithm(params, context, QgsProcessingFeedback())


def test_processing_output_definition_is_resolved(plugin, tmp_path, monkeypatch):
    """parameterAsString gave "" for an output definition (TEMPORARY_OUTPUT,
    a model's): the export landed in the swept q2styledtiles_* folder."""
    from qgis.core import QgsProcessingFeedback, QgsProcessingOutputLayerDefinition  # pylint: disable=import-outside-toplevel
    algorithm, seen = _fake_algorithm(monkeypatch)
    context = QgsProcessingContext()
    context.setProject(reset_project())
    for value in (QgsProcessingOutputLayerDefinition("TEMPORARY_OUTPUT"),
                  QgsProcessingOutputLayerDefinition(str(tmp_path / "chosen"))):
        seen.clear()
        results = algorithm.processAlgorithm(
            {"MIN_ZOOM": 10, "MAX_ZOOM": 11, "EXTENT": "2119000,2123000,6019000,6023000 [EPSG:3857]",
             "OUTPUT_DIR": value}, context, QgsProcessingFeedback())
        assert seen["output_dir"] and "q2styledtiles_" not in seen["output_dir"], seen["output_dir"]
        assert results["OUTPUT_DIR"] == seen["output_dir"]
    assert seen["output_dir"] == str(tmp_path / "chosen")
