"""An export removes only the layers it added itself outside the legend:
the project's own layers that are not in the legend (lookup tables of
joins and value relations, added by scripts or plugins) stay."""

from qgis.core import QgsProject, QgsVectorLayer

from q2vt_fixtures import reset_project


def _memory(name):
    return QgsVectorLayer("Point?crs=EPSG:3857", name, "memory")


def test_clear_project_keeps_the_projects_own_layers(plugin):
    from q2vt_plugin.src.qgis2vectortiles import QGIS2VectorTiles  # pylint: disable=import-error
    project = reset_project()
    shown, lookup = _memory("Shown"), _memory("Lookup table")
    project.addMapLayer(shown)
    project.addMapLayer(lookup, False)  # not in the legend
    run = QGIS2VectorTiles.__new__(QGIS2VectorTiles)
    run._clear_project()  # pylint: disable=protected-access  # (not started: nothing removed)
    run._project_layer_ids = set(QgsProject.instance().mapLayers())  # pylint: disable=protected-access
    added = _memory("Work layer")
    project.addMapLayer(added, False)  # one of the run's own
    added_id = added.id()
    run._clear_project()  # pylint: disable=protected-access
    layers = QgsProject.instance().mapLayers()
    assert shown.id() in layers and lookup.id() in layers and added_id not in layers
