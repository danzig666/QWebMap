"""Publish window behaviours from the bug and usability review: closing with
settings that cannot be saved asks first; Cancel in the import question
imports nothing; the layer list follows the project; the basemap's settings
are off without a basemap; the layer extent mode without its layer is the
map view (and asks before the export like it)."""

import json
import time

from qgis.core import QgsProject, QgsRectangle
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


def test_web_zoom_scales_become_the_projects_scale_list(plugin, monkeypatch, tmp_path):
    """The button sets the project's scales to the web zooms' (for its CRS:
    an EOV project gets other numbers than Web Mercator), asking before it
    replaces a list of the project's own; each is read back as its zoom."""
    from qgis.core import QgsCoordinateReferenceSystem  # pylint: disable=import-outside-toplevel
    from q2vt_plugin.src.core.fidelity import zoom as zm  # pylint: disable=import-error,import-outside-toplevel
    from q2vt_plugin.src.publishing.zoom_load import zoom_scale_factor  # pylint: disable=import-error,import-outside-toplevel
    dialog, _ = _dialog(plugin, monkeypatch, tmp_path)
    project = QgsProject.instance()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:23700"))
    dialog.profile.view.extent_mode, dialog.profile.view.extent = "fixed", [2119000, 6019000, 2123000, 6023000]
    settings = project.viewSettings()
    settings.setMapScales([1000.0, 5000.0])
    settings.setUseProjectScales(True)
    asked = []
    monkeypatch.setattr(QMessageBox, "question",
                        lambda *a, **k: asked.append(a[2]) or QMessageBox.StandardButton.No)
    assert not dialog.use_web_zoom_scales()
    assert asked and sorted(settings.mapScales()) == [1000.0, 5000.0]
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    assert dialog.use_web_zoom_scales() and settings.useProjectScales()
    scales = sorted(settings.mapScales(), reverse=True)
    assert len(scales) == 23
    factor = zoom_scale_factor(project, QgsRectangle(*dialog.profile.view.extent))
    assert abs(scales[0] - factor) <= 0.5 and scales[0] < zm.WEB_MERCATOR_TOP_SCALE  # EOV at ~47.5°
    zm.configure(factor)
    try:
        assert [zm.interval_from_scales(s, 0).min_zoom for s in scales] == list(range(23))
    finally:
        zm.configure(zm.WEB_MERCATOR_TOP_SCALE)
    dialog.close()


def test_the_simple_view_shows_and_edits_the_same_settings(plugin, monkeypatch, tmp_path):
    """The simple view writes into the advanced view's controls: switching
    either way changes nothing; its layers, information, area, zoom,
    background and folder are the window's settings."""
    from q2vt_plugin.src.gui.simple_page import ZOOM_STOPS  # pylint: disable=import-error,import-outside-toplevel
    from qgis.PyQt.QtCore import Qt as QtCore_Qt  # pylint: disable=import-outside-toplevel
    dialog, parcels = _dialog(plugin, monkeypatch, tmp_path)
    before = dialog._profile_json()  # pylint: disable=protected-access
    dialog.set_simple_view(True, remember=False)
    dialog.set_simple_view(False, remember=False)
    dialog.set_simple_view(True, remember=False)
    assert dialog._profile_json() == before  # pylint: disable=protected-access
    page = dialog.simple
    assert page.title.text() == dialog.e_title.text()
    page.title.setText("Egyszerű térkép")
    page._title_edited("Egyszerű térkép")  # pylint: disable=protected-access
    assert dialog.e_title.text() == "Egyszerű térkép"
    row = next(r for r in range(page.layers.rowCount())
               if page.layers.item(r, 0).data(QtCore_Qt.ItemDataRole.UserRole) == parcels.id())
    page.layers.item(row, 1).setCheckState(QtCore_Qt.CheckState.Unchecked)
    assert parcels.id() not in [c.layer_id for c in dialog.collect().layers if c.included]
    page.layers.item(row, 2).setCheckState(QtCore_Qt.CheckState.Checked)   # information: on the map too
    profile = dialog.collect()
    config = next(c for c in profile.layers if c.layer_id == parcels.id())
    assert config.included and config.popup_fields
    assert not any(p.field.lower() in ("fid", "id") for p in config.popup_fields)
    page.layers.item(row, 2).setCheckState(QtCore_Qt.CheckState.Unchecked)
    assert not next(c for c in dialog.collect().layers if c.layer_id == parcels.id()).popup_fields
    page.zoom.setValue(len(ZOOM_STOPS) - 1)
    assert dialog.e_max_zoom.value() == ZOOM_STOPS[-1][1]
    page.area.setCurrentIndex(page.area.findData("layer"))
    page.area_layer.setCurrentIndex(page.area_layer.findData(parcels.id()))
    profile = dialog.collect()
    assert profile.view.extent_mode == "layer" and profile.view.extent_layer == parcels.id()
    assert profile.view.min_zoom <= profile.view.max_zoom
    page.bg_osm.setChecked(True)
    assert dialog.collect().basemap.kind == "protomaps"
    page.bg_none.setChecked(True)
    assert dialog.collect().basemap.kind == "none"
    page.folder.setText(str(tmp_path / "maps"))
    page._folder_edited(str(tmp_path / "maps"))  # pylint: disable=protected-access
    assert dialog.collect().output.local_directory == str(tmp_path / "maps")
    assert not dialog.btn_publish.isVisible() and page.isVisibleTo(dialog)
    dialog.close()


def test_the_simple_view_exports_locally_whatever_the_destination(plugin, monkeypatch, tmp_path):
    """Make web map: a local export (no upload), no "Published area?" question."""
    dialog, _ = _dialog(plugin, monkeypatch, tmp_path)
    dialog.d_kind.setCurrentIndex(dialog.d_kind.findData("r2"))
    dialog.set_simple_view(True, remember=False)
    assert dialog._confirm_extent()  # pylint: disable=protected-access
    calls = []
    monkeypatch.setattr(dialog, "export_locally", lambda: calls.append("local") or True)
    monkeypatch.setattr(dialog, "publish", lambda: calls.append("publish"))
    dialog.simple.make_map()
    assert calls == ["local"]
    assert "online destination" in dialog.simple.advanced_note.text()
    dialog.close()


def test_the_first_view_question_only_for_new_users(plugin, monkeypatch, tmp_path):
    from qgis.core import QgsSettings  # pylint: disable=import-outside-toplevel
    dialog, _ = _dialog(plugin, monkeypatch, tmp_path)
    settings = QgsSettings()
    asked = []
    monkeypatch.setattr(QMessageBox, "exec", lambda box: asked.append(box.text()))
    monkeypatch.setattr(QMessageBox, "clickedButton",
                        lambda box: next(b for b in box.buttons() if b.text() == "Simple"))
    try:
        settings.remove(dialog.VIEW_KEY)
        settings.setValue(dialog.GEOMETRY_KEY, dialog.saveGeometry())   # used the window before
        dialog.ask_first_view()
        assert not asked and settings.value(dialog.VIEW_KEY) == "advanced" and not dialog.is_simple_view()
        settings.remove(dialog.VIEW_KEY)
        settings.remove(dialog.GEOMETRY_KEY)                            # a new user
        dialog.ask_first_view()
        assert asked and settings.value(dialog.VIEW_KEY) == "simple" and dialog.is_simple_view()
        dialog.ask_first_view()
        assert len(asked) == 1                                          # once
    finally:
        settings.remove(dialog.VIEW_KEY)
    dialog.close()
