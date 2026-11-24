"""Publish window behaviours from the bug and usability review: closing with
settings that cannot be saved asks first; Cancel in the import question
imports nothing; the layer list follows the project; the basemap's settings
are off without a basemap; the layer extent mode without its layer is the
map view (and asks before the export like it)."""

import os
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
    from q2vt_plugin.src.gui.detail_scale import SCALES, zoom_for_scale  # pylint: disable=import-error,import-outside-toplevel
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
    page.auto.setChecked(False)                      # the slider: a map scale
    page.zoom.setValue(len(SCALES) - 1)
    assert dialog.e_max_zoom.value() == zoom_for_scale(page._factor(), SCALES[-1])  # pylint: disable=protected-access
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
    monkeypatch.setattr(QMessageBox, "open", lambda box: (asked.append(box.text()), box.done(0)))
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


def test_the_simple_view_recommends_a_scale_from_the_layers(plugin, monkeypatch, tmp_path):
    """Automatic detail: the features' size sets the scale (small parcels: a
    detailed scale), a layer shown only when zoomed in needs its scale; the
    choice is kept with the project; a preview of the map at that scale."""
    from q2vt_plugin.src.gui.detail_scale import recommend, scale_of_zoom  # pylint: disable=import-error,import-outside-toplevel
    from qgis.core import QgsRectangle  # pylint: disable=import-outside-toplevel
    dialog, parcels = _dialog(plugin, monkeypatch, tmp_path)
    page = dialog.simple
    dialog.profile.view.extent = [2119000, 6019000, 2123000, 6023000]
    dialog.profile.view.extent_mode = "fixed"
    factor = page._factor()  # pylint: disable=protected-access
    box = QgsRectangle(*dialog.profile.view.extent)
    scale, reasons = recommend(dialog.project, [parcels], box, factor, 0)
    assert scale == 50000 and reasons and "676 m across" in reasons[0]   # 1 km Mercator squares at 47.4°N
    parcels.setScaleBasedVisibility(True)
    parcels.setMinimumScale(1000.0)                   # shown from 1:1 000 on: needs 1:500
    assert recommend(dialog.project, [parcels], box, factor, 0)[0] <= 500
    parcels.setScaleBasedVisibility(False)
    dialog.show()
    dialog.set_simple_view(True, remember=False)
    assert page.auto.isChecked()                      # new settings: automatic
    page.auto.setChecked(False)
    assert not dialog.project.readBoolEntry("QWebMap", "simple/autoDetail", True)[0]
    page.auto.setChecked(True)
    assert page.busy.isVisible()                      # measured in the background
    page.wait_for_preview()
    assert not page.busy.isVisible()
    assert abs(scale_of_zoom(factor, dialog.e_max_zoom.value())) <= scale * 1.01
    assert dialog.project.readBoolEntry("QWebMap", "simple/autoDetail", False)[0]
    page.wait_for_preview()
    assert page.preview.pixmap() is not None and not page.preview.pixmap().isNull()
    dialog.close()


def test_the_review_lists_the_feature_labels_and_their_fields(plugin, monkeypatch, tmp_path):
    """Each feature's display-expression label is published in the feature
    lookup (deep links, on by default): the review says so, with its fields."""
    dialog, parcels = _dialog(plugin, monkeypatch, tmp_path)
    config = dialog.profile.layer(parcels.id())
    config.included, config.popup_fields, config.deep_links = True, [], True
    expression = "\"note\" || ' ' || \"hrsz\""
    if dialog.current_layer_id == parcels.id():
        dialog.i_display.setText(expression)
        dialog.i_links.setChecked(True)
    else:
        config.display_expression = expression
    dialog.refresh_review()
    text = dialog.review.toPlainText()
    assert f"display expression {expression}), public; fields used: hrsz, note" in text
    dialog.close()


def test_a_relative_or_home_output_folder_is_the_same_for_the_export_and_the_window(plugin, monkeypatch, tmp_path):
    """"web_maps" is in the project's folder (not QGIS's working folder), "~"
    is the home folder: where the export writes and Preview looks."""
    import os  # pylint: disable=import-outside-toplevel
    from q2vt_plugin.src.publishing.controller import output_folder, publication_dirs  # pylint: disable=import-error
    dialog, _ = _dialog(plugin, monkeypatch, tmp_path)
    assert output_folder("~/x") == os.path.join(os.path.expanduser("~"), "x")
    assert output_folder("web_maps") == os.path.join(str(tmp_path), "web_maps")
    dialog.o_dir.setText("web_maps")
    profile = dialog.collect()
    folder, _ = publication_dirs(profile)
    assert folder == os.path.join(str(tmp_path), "web_maps", profile.slug)
    os.makedirs(folder)
    open(os.path.join(folder, "index.html"), "w", encoding="utf-8").close()
    assert dialog._existing_map_dir() == folder  # pylint: disable=protected-access


def test_showing_the_simple_view_never_replaces_zooms_set_elsewhere(plugin, monkeypatch, tmp_path):
    """Automatic detail is on for new settings, but zooms set in the advanced
    view stay when the simple view is shown (it shows "Choose automatically"
    unticked then); saved settings reopened in the simple view are not
    changed by showing them; the views cannot be switched while exporting."""
    dialog, _ = _dialog(plugin, monkeypatch, tmp_path)
    dialog.profile.view.extent = [2119000, 6019000, 2123000, 6023000]
    dialog.profile.view.extent_mode = "fixed"
    dialog.e_min_zoom.setValue(5)
    dialog.e_max_zoom.setValue(19)
    before = dialog._profile_json()  # pylint: disable=protected-access
    dialog.set_simple_view(True, remember=False)
    dialog.set_simple_view(False, remember=False)
    assert (dialog.e_min_zoom.value(), dialog.e_max_zoom.value()) == (5, 19)
    assert dialog._profile_json() == before  # pylint: disable=protected-access
    assert not dialog.simple.auto.isChecked() and dialog.simple.zoom.isEnabled()
    dialog._busy(True)  # pylint: disable=protected-access
    assert not dialog.btn_simple.isEnabled() and not dialog.btn_advanced.isEnabled()
    dialog._busy(False)  # pylint: disable=protected-access
    assert dialog.btn_simple.isEnabled()
    dialog.simple.auto.setChecked(True)               # ticked again: the automatic choice
    dialog.simple.wait_for_preview()
    assert (dialog.e_min_zoom.value(), dialog.e_max_zoom.value()) != (5, 19)
    dialog.e_min_zoom.setValue(5)
    dialog.e_max_zoom.setValue(19)
    assert dialog.save_settings()
    dialog.close()
    from qgis.core import QgsSettings  # pylint: disable=import-outside-toplevel
    from q2vt_plugin.src.gui.publish_dialog import PublishDialog  # pylint: disable=import-error,import-outside-toplevel
    QgsSettings().setValue(PublishDialog.VIEW_KEY, "simple")
    try:
        again = PublishDialog(iface=None)                # saved, automatic detail on, opened simple
    finally:
        QgsSettings().remove(PublishDialog.VIEW_KEY)
    assert again.is_simple_view()
    assert (again.e_min_zoom.value(), again.e_max_zoom.value()) == (5, 19)
    assert again._profile_json() == again._saved_json  # pylint: disable=protected-access
    again.close()


def test_imported_settings_keep_their_zooms_in_the_simple_view(plugin, monkeypatch, tmp_path):
    """New settings (automatic detail pending), then a settings file imported:
    its zooms are kept when the simple view is shown, "Choose automatically"
    unticked, even when they equal the window's first zooms."""
    dialog, _ = _dialog(plugin, monkeypatch, tmp_path)
    assert dialog.new_settings
    zooms = (dialog.e_min_zoom.value(), dialog.e_max_zoom.value())
    path = tmp_path / "s.q2vt.json"
    assert dialog.export_settings_file(str(path))
    assert dialog.import_settings_file(str(path), same_map=True)
    calls = []
    monkeypatch.setattr(dialog.simple, "apply_auto", lambda: calls.append(1))
    dialog.set_simple_view(True, remember=False)
    assert not calls and not dialog.simple.auto.isChecked()
    assert (dialog.e_min_zoom.value(), dialog.e_max_zoom.value()) == zooms
    dialog.close()


def test_a_zip_that_cannot_be_made_is_said(plugin, monkeypatch, tmp_path):
    """Make a ZIP to send: a disk or file error is said, no half-written ZIP."""
    import shutil  # pylint: disable=import-outside-toplevel
    dialog, _ = _dialog(plugin, monkeypatch, tmp_path)
    folder = tmp_path / "web_maps" / "terv"
    folder.mkdir(parents=True)
    monkeypatch.setattr(dialog, "_local_map_dir", lambda: str(folder))
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warned.append(a[2]))

    def full(base, *args, **kwargs):
        open(base + ".zip", "wb").close()
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(shutil, "make_archive", full)
    assert dialog.simple.make_zip() == ""
    assert warned and "No space left" in warned[0] and "No space left" in dialog.status.text()
    assert not (tmp_path / "web_maps" / "terv.zip").exists()
    dialog.close()


def test_a_zip_of_a_file_dated_before_1980_is_said(plugin, monkeypatch, tmp_path):
    """A file with an old or zero date (copies from some shares): ZIP cannot
    store it; said, no half-written ZIP."""
    dialog, _ = _dialog(plugin, monkeypatch, tmp_path)
    folder = tmp_path / "web_maps" / "terv"
    folder.mkdir(parents=True)
    old = folder / "index.html"
    old.write_text("<html></html>", encoding="utf-8")
    os.utime(old, (0, 0))
    monkeypatch.setattr(dialog, "_local_map_dir", lambda: str(folder))
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warned.append(a[2]))
    assert dialog.simple.make_zip() == ""
    assert warned and "1980" in warned[0]
    assert not (tmp_path / "web_maps" / "terv.zip").exists()
    dialog.close()
