"""Publish window behaviours from the bug and usability review: closing with
settings that cannot be saved asks first; Cancel in the import question
imports nothing; the layer list follows the project; the basemap's settings
are off without a basemap; the layer extent mode without its layer is the
map view (and asks before the export like it)."""

import json
import time

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QMessageBox

from q2vt_fixtures import reset_project


def _dialog(plugin, monkeypatch, tmp_path):  # pylint: disable=unused-argument
    import os  # pylint: disable=import-outside-toplevel
    import sys  # pylint: disable=import-outside-toplevel
    for name in ("warning", "information", "critical"):
        monkeypatch.setattr(QMessageBox, name, lambda *a, **k: None)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from test_publishing_pipeline import _parcels  # pylint: disable=import-error,import-outside-toplevel
    project = reset_project()
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    project.addMapLayer(parcels)
    project.setFileName(str(tmp_path / "terv.qgz"))
    from q2vt_plugin.src.gui.publish_dialog import PublishDialog  # pylint: disable=import-error
    return PublishDialog(iface=None), parcels


def _settle(seconds=0.5):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QCoreApplication.processEvents()
        time.sleep(0.02)


def test_closing_with_settings_that_cannot_be_saved_asks(plugin, monkeypatch, tmp_path):
    dialog, _ = _dialog(plugin, monkeypatch, tmp_path)
    dialog.show()
    dialog.e_min_zoom.setValue(dialog.e_max_zoom.value())
    dialog.e_title.setText("")                      # a title is needed: cannot be saved
    asked = []

    def answer(button):
        def ask(*args, **_kwargs):
            asked.append(args[1])
            return button
        monkeypatch.setattr(QMessageBox, "question", ask)
    answer(QMessageBox.StandardButton.No)
    dialog.close()
    assert asked == ["Close without saving?"] and dialog.isVisible()   # back to the settings
    answer(QMessageBox.StandardButton.Yes)
    dialog.close()
    assert len(asked) == 2 and not dialog.isVisible()


def test_cancel_in_the_import_question_imports_nothing(plugin, monkeypatch, tmp_path):
    dialog, _ = _dialog(plugin, monkeypatch, tmp_path)
    path = tmp_path / "s.q2vt.json"
    dialog.e_title.setText("Fájlból")
    dialog.export_settings_file(str(path))
    assert json.loads(path.read_text(encoding="utf-8"))
    dialog.e_title.setText("Ez marad")
    for button in (QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Escape):
        monkeypatch.setattr(QMessageBox, "question", lambda *a, _b=button, **k: _b)
        assert not dialog.import_settings_file(str(path))
        assert dialog.e_title.text() == "Ez marad"
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    assert dialog.import_settings_file(str(path)) is not False
    assert dialog.e_title.text() == "Fájlból"
    dialog.close()


def test_the_layer_list_follows_the_project(plugin, monkeypatch, tmp_path):
    from test_publishing_pipeline import _parcels  # pylint: disable=import-error,import-outside-toplevel
    dialog, parcels = _dialog(plugin, monkeypatch, tmp_path)

    def names():
        return sorted(item.text(0) for item in dialog._tree_items())  # pylint: disable=protected-access
    before = names()
    other = _parcels(str(tmp_path / "other.gpkg"))
    other.setName("Új réteg")
    QgsProject.instance().addMapLayer(other)
    _settle()
    assert names() == sorted(before + ["Új réteg"])
    QgsProject.instance().removeMapLayer(other.id())
    _settle()
    assert names() == before
    parcels.setName("Átnevezve")
    QgsProject.instance().layerTreeRoot().findLayer(parcels.id()).setName("Átnevezve")
    _settle()
    assert "Átnevezve" in names()
    dialog.close()


def test_basemap_settings_are_off_without_a_basemap(plugin, monkeypatch, tmp_path):
    dialog, _ = _dialog(plugin, monkeypatch, tmp_path)
    dialog.b_kind.setCurrentIndex(dialog.b_kind.findData("protomaps"))
    assert dialog.b_max.isEnabled() and dialog.b_source.isEnabled()
    def initial():
        return [dialog.b_initial.itemData(i) for i in range(dialog.b_initial.count())]
    assert any(data in dialog.b_flavors for data in initial())  # its styles can be the first shown
    dialog.b_kind.setCurrentIndex(dialog.b_kind.findData("none"))
    assert not dialog.b_max.isEnabled() and not dialog.b_source.isEnabled()
    assert not any(box.isEnabled() for box in dialog.b_flavors.values())
    assert "none" in initial() and not any(data in dialog.b_flavors for data in initial())
    dialog.close()


def test_the_layer_extent_mode_without_its_layer_is_the_map_view(plugin, monkeypatch, tmp_path):
    dialog, parcels = _dialog(plugin, monkeypatch, tmp_path)
    view = dialog.profile.view
    view.extent_mode, view.extent_layer = "layer", parcels.id()
    assert not dialog._extent_is_canvas()  # pylint: disable=protected-access
    QgsProject.instance().removeMapLayer(parcels.id())
    assert dialog._extent_is_canvas()  # pylint: disable=protected-access
    view.extent_layer = ""
    assert dialog._extent_is_canvas()  # pylint: disable=protected-access
    view.extent_mode = "fixed"
    assert not dialog._extent_is_canvas()  # pylint: disable=protected-access
    dialog.close()


def test_choosing_the_map_view_again_asks_again(plugin, monkeypatch, tmp_path):
    """After “Don't ask again”, choosing “Current map view” in the list again
    brings the question before the export back."""
    dialog, _ = _dialog(plugin, monkeypatch, tmp_path)
    dialog.profile.view.confirm_canvas_extent = False
    index = dialog.e_extent_mode.findData("canvas")
    dialog.e_extent_mode.setCurrentIndex(index)
    assert not dialog.profile.view.confirm_canvas_extent   # (set by the program: unchanged)
    dialog.e_extent_mode.activated.emit(index)             # chosen by the user
    assert dialog.profile.view.confirm_canvas_extent
    dialog.close()


def test_a_world_layer_extent_is_cut_to_web_mercator(plugin, monkeypatch, tmp_path):
    from qgis.core import QgsFeature, QgsGeometry, QgsVectorLayer  # pylint: disable=import-outside-toplevel
    dialog, _ = _dialog(plugin, monkeypatch, tmp_path)
    world = QgsVectorLayer("Polygon?crs=EPSG:4326", "Világ", "memory")
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromWkt("POLYGON((-180 -90, 180 -90, 180 90, -180 90, -180 -90))"))
    world.dataProvider().addFeatures([feature])
    world.updateExtents()
    x0, y0, x1, y1 = dialog._layer_extent_3857(world)  # pylint: disable=protected-access
    half = 20037508.342789244
    assert -half - 1 <= x0 < x1 <= half + 1 and -half - 1 <= y0 < y1 <= half + 1
    assert y1 > 0.99 * half                              # not cut short either
    dialog.close()


def test_local_only_shows_no_upload_fields_cost_or_approval(plugin, monkeypatch, tmp_path):
    dialog, _ = _dialog(plugin, monkeypatch, tmp_path)
    dialog.show()
    dialog.d_kind.setCurrentIndex(dialog.d_kind.findData("r2"))
    assert not dialog.d_bucket.isHidden() and not dialog.d_public.isHidden() and not dialog.d_test.isHidden()
    dialog.refresh_review()
    assert "Cost:" in dialog.review.toPlainText() and not dialog.approve.isHidden()
    dialog.d_kind.setCurrentIndex(dialog.d_kind.findData("local"))
    assert all(w.isHidden() for w in (dialog.d_bucket, dialog.d_prefix, dialog.d_public, dialog.d_address,
                                           dialog.d_retention, dialog.d_session_row, dialog.d_test,
                                           dialog.d_cors, dialog.d_history))
    dialog.refresh_review()
    text = dialog.review.toPlainText()
    assert "Cost:" not in text and "no approval is needed" in text and dialog.approve.isHidden()
    dialog.close()
