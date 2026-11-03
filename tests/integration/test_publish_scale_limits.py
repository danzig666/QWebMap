"""Web-only visible scale range of layers: set in the Publish window's
layer list (one layer, or many at once through a group or the selection),
saved in the profile, and applied by the export (style zoom range, no
tiles where hidden, the viewer model's zoom range) on top of the layer's
own QGIS scale range - without changing the project."""

import json
import os
import sqlite3
import sys

import pytest
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMessageBox

from q2vt_fixtures import reset_project

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_publishing_pipeline import EXTENT, _parcels  # noqa: E402  pylint: disable=wrong-import-position


def test_combine_scale_ranges(plugin):
    from q2vt_plugin.src.core.rules_flattener import combine_scale_ranges  # pylint: disable=import-error
    assert combine_scale_ranges(0, 0, 25000, 0) == (25000, 0)
    assert combine_scale_ranges(100000, 1000, 25000, 0) == (25000, 1000)   # the narrower wins
    assert combine_scale_ranges(10000, 0, 25000, 500) == (10000, 500)


def test_scales_column_sets_many_layers_and_is_saved(plugin, monkeypatch, tmp_path):
    for name in ("warning", "information", "critical"):
        monkeypatch.setattr(QMessageBox, name, lambda *a, **k: None)
    project = reset_project()
    group = project.layerTreeRoot().addGroup("Részletek")
    layers = []
    for index in range(2):
        layer = _parcels(str(tmp_path / f"p{index}.gpkg"))
        layer.setName(f"Réteg {index}")
        project.addMapLayer(layer, False)
        group.addLayer(layer)
        layers.append(layer)
    from q2vt_plugin.src.gui.publish_dialog import PublishDialog  # pylint: disable=import-error
    dialog = PublishDialog(iface=None)
    group_item = next(dialog._group_items())  # pylint: disable=protected-access
    group_item.setSelected(True)               # the group: both layers
    assert dialog.edit_scales((25000.0, 0.0))
    texts = [item.text(5) for item in dialog._tree_items()]  # pylint: disable=protected-access
    assert texts == ["1:25 000 –", "1:25 000 –"]
    profile = dialog.collect()
    assert [(c.min_scale, c.max_scale) for c in profile.layers] == [(25000.0, 0.0)] * 2
    from q2vt_plugin.src.publishing.profile import dumps, load_profile  # pylint: disable=import-error
    assert load_profile(dumps(profile)).layers[0].min_scale == 25000.0
    assert not layers[0].hasScaleBasedVisibility()  # the project is not changed
    dialog.close()


def test_export_hides_and_does_not_tile_beyond_the_limit(plugin, tmp_path):
    from publishing.controller import export_local
    from publishing.models import LayerConfig, PopupField, PublicationProfile
    project = reset_project()
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    project.addMapLayer(parcels)
    profile = PublicationProfile(title="Lépték", slug="lepteket", locale="hu")
    profile.view.min_zoom, profile.view.max_zoom = 11, 14
    profile.output.local_directory = str(tmp_path / "out")
    config = LayerConfig(parcels.id(), key_fields=["hrsz"], popup_fields=[PopupField("hrsz")])
    config.min_scale = 40000.0   # hidden when zoomed out beyond 1:40 000 (~zoom 12.9)
    profile.layers = [config]
    result = export_local(project, profile, EXTENT)
    style = json.load(open(os.path.join(result.export_dir, "style", "style.json"), encoding="utf-8"))
    zooms = [layer.get("minzoom") for layer in style["layers"] if layer.get("source-layer")]
    assert zooms and min(zooms) >= 12.5
    with sqlite3.connect(os.path.join(result.export_dir, "tiles.mbtiles")) as conn:
        levels = {z for (z,) in conn.execute("SELECT DISTINCT zoom_level FROM tiles")}
    assert levels and min(levels) >= 12      # no tiles where it is hidden
    assert not parcels.hasScaleBasedVisibility()


def test_legend_column_and_interaction_checkbox_are_one_setting(plugin, monkeypatch, tmp_path):
    for name in ("warning", "information", "critical"):
        monkeypatch.setattr(QMessageBox, name, lambda *a, **k: None)
    project = reset_project()
    group = project.layerTreeRoot().addGroup("Csoport")
    layers = []
    for index in range(2):
        layer = _parcels(str(tmp_path / f"l{index}.gpkg"))
        layer.setName(f"L{index}")
        project.addMapLayer(layer, False)
        group.addLayer(layer)
        layers.append(layer)
    from qgis.PyQt.QtCore import Qt  # pylint: disable=import-outside-toplevel
    from q2vt_plugin.src.gui.publish_dialog import PublishDialog  # pylint: disable=import-error
    dialog = PublishDialog(iface=None)
    items = list(dialog._tree_items())  # pylint: disable=protected-access
    assert all(item.checkState(4) == Qt.CheckState.Checked for item in items)  # default: shown
    next(dialog._group_items()).setSelected(True)  # pylint: disable=protected-access
    dialog.apply_to_selection(4, False)            # bulk: hide the group's layers from the legend
    assert [c.legend for c in dialog.collect().layers] == [False, False]
    # The Interaction tab shows it, and its checkbox changes the column.
    dialog.tabs.setCurrentIndex(1)
    dialog._fill_interaction_layers()               # pylint: disable=protected-access
    dialog.i_layers.setCurrentRow(0)
    assert not dialog.i_legend.isChecked()
    dialog.i_legend.setChecked(True)
    assert items[0].checkState(4) == Qt.CheckState.Checked
    assert [c.legend for c in dialog.collect().layers] == [True, False]
    dialog.close()


def test_labels_only_limit_keeps_the_features(plugin, tmp_path):
    """Labels hidden when zoomed out beyond 1:40 000 (~zoom 12.9): their
    style layers start there and no tile below it has them; the parcels
    themselves are still drawn and tiled from the first zoom."""
    from publishing import mvt
    from publishing.controller import export_local
    from publishing.models import LayerConfig, PopupField, PublicationProfile
    project = reset_project()
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    project.addMapLayer(parcels)
    profile = PublicationProfile(title="Feliratok", slug="feliratok", locale="hu")
    profile.view.min_zoom, profile.view.max_zoom = 11, 14
    profile.output.local_directory = str(tmp_path / "out")
    config = LayerConfig(parcels.id(), key_fields=["hrsz"], popup_fields=[PopupField("hrsz")])
    config.labels_min_scale = 40000.0
    profile.layers = [config]
    result = export_local(project, profile, EXTENT)
    style = json.load(open(os.path.join(result.export_dir, "style", "style.json"), encoding="utf-8"))
    tiled = [layer for layer in style["layers"] if layer.get("source-layer")]
    labels = [layer for layer in tiled if "text-field" in layer.get("layout", {})]
    features = [layer for layer in tiled if layer["type"] == "fill"]
    assert labels and features
    assert min(layer.get("minzoom", 0) for layer in labels) >= 12.5
    assert max(layer.get("minzoom", 0) for layer in features) < 12
    label_sources = {layer["source-layer"] for layer in labels}
    with sqlite3.connect(os.path.join(result.export_dir, "tiles.mbtiles")) as conn:
        rows = conn.execute("SELECT zoom_level, tile_data FROM tiles").fetchall()
    by_zoom = {}
    for zoom, data in rows:
        by_zoom.setdefault(zoom, set()).update(mvt.layer_names(mvt.payload(bytes(data))))
    assert min(by_zoom) == 11                       # the parcels from the first zoom on
    assert not by_zoom[11] & label_sources          # no labels where they are hidden
    assert by_zoom[max(by_zoom)] & label_sources    # and they are there zoomed in
    assert not parcels.hasScaleBasedVisibility()


def test_zoomed_out_load_suggests_feature_and_label_zooms(plugin, tmp_path):
    """A dense layer of small parcels with labels: zoomed out it is heavy and
    its features are specks, so a feature zoom is suggested; its labels mostly
    cannot be placed until zoomed in further, so a later label zoom is
    suggested. A light layer gets no suggestion."""
    from qgis.core import QgsFeature, QgsField, QgsGeometry, QgsVectorLayer
    from qgis.PyQt.QtCore import QVariant
    from publishing import zoom_load
    from publishing.models import LayerConfig, PublicationProfile
    project = reset_project()
    dense = QgsVectorLayer("Polygon?crs=EPSG:3857", "Sűrű", "memory")
    dense.dataProvider().addAttributes([QgsField("hrsz", QVariant.String)])
    dense.updateFields()
    features = []
    x0, y0, step = 2119000.0, 6019000.0, 20.0     # 200 × 200 parcels of 18 m in 4 × 4 km
    for i in range(200):
        for j in range(200):
            feature = QgsFeature(dense.fields())
            feature.setAttributes([f"{i * 200 + j}/{j % 7}"])
            x, y = x0 + i * step, y0 + j * step
            feature.setGeometry(QgsGeometry.fromWkt(
                f"POLYGON(({x} {y},{x + 18} {y},{x + 18} {y + 18},{x} {y + 18},{x} {y}))"))
            features.append(feature)
    dense.dataProvider().addFeatures(features)
    from qgis.core import (Qgis, QgsPalLayerSettings, QgsTextFormat,  # pylint: disable=import-outside-toplevel
                           QgsVectorLayerSimpleLabeling)
    settings = QgsPalLayerSettings()
    settings.fieldName = "hrsz"
    settings.placement = Qgis.LabelPlacement.OverPoint
    fmt = QgsTextFormat()
    fmt.setSize(9)
    settings.setFormat(fmt)
    dense.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    dense.setLabelsEnabled(True)
    light = _parcels(str(tmp_path / "light.gpkg"))
    project.addMapLayer(dense)
    project.addMapLayer(light)
    profile = PublicationProfile(title="Terhelés", slug="terheles", locale="hu")
    profile.view.min_zoom, profile.view.max_zoom = 8, 18
    profile.layers = [LayerConfig(dense.id()), LayerConfig(light.id())]
    loads, factor = zoom_load.analyse(project, profile, EXTENT)
    by_id = {load.layer_id: load for load in loads}
    assert loads[0].layer_id == dense.id()          # the heaviest first
    load = by_id[dense.id()]
    assert load.features == 40000 and load.labels and load.label_share == 1.0
    assert load.shown_from == 8 and load.heavy(8)
    assert load.tile_features[8] == 40000           # zoomed out: all in one tile
    # 18 m parcels are 2 px wide around zoom 14 (at 47.5° latitude, Web Mercator m).
    assert load.suggested_from is not None and 12 <= load.suggested_from <= 15
    assert load.suggested_labels_from is not None and load.suggested_labels_from > load.suggested_from
    assert by_id[light.id()].suggested_from is None
    assert by_id[light.id()].suggested_labels_from is None  # 4 labels: no load
    # The suggested zoom's scale: rounded so the tiles start at that zoom.
    scale = zoom_load.scale_for_zoom(factor, load.suggested_from)
    assert int(zoom_load.zoom_for_scale(factor, scale)) == load.suggested_from
    # A labels-only limit already set: its labels start there.
    profile.layers[0].labels_min_scale = zoom_load.scale_for_zoom(factor, 17)
    again = {l.layer_id: l for l in zoom_load.analyse(project, profile, EXTENT)[0]}[dense.id()]
    assert again.labels_from == 17 and again.shown_from == 8
    # The speed slider: faster hides the specks and the crowded labels from
    # closer zooms, slower shows more zoomed out; balanced is as above.
    suggested = []
    for speed in range(len(zoom_load.SPEEDS)):
        zoom_load.resuggest(loads, 18, speed)
        suggested.append((by_id[dense.id()].suggested_from, by_id[dense.id()].suggested_labels_from))
    features = [f or 8 for f, _ in suggested]
    assert features == sorted(features) and features[0] < features[-1], suggested
    zoom_load.resuggest(loads, 18, zoom_load.BALANCED)
    assert (by_id[dense.id()].suggested_from, by_id[dense.id()].suggested_labels_from) == \
        suggested[zoom_load.BALANCED]
    # Many labels are slow to draw even when they would fit: past
    # HEAVY_LABELS in a tile, the labels start later.
    crowded = zoom_load.LayerLoad("c", "Feliratok", "point", 50000, 10,
                                  tile_features={z: 50000 // 4 ** (z - 10) for z in range(10, 19)},
                                  labels=True, labels_from=10, label_capacity=1e9)
    zoom_load.resuggest([crowded], 18, zoom_load.BALANCED)
    assert crowded.labels_shown(10) == 1.0 and crowded.labels_heavy(10)
    assert crowded.suggested_labels_from == 13  # 50000 / 4**3 = 781 labels ≤ 1500
    zoom_load.resuggest([crowded], 18, len(zoom_load.SPEEDS) - 1)
    assert crowded.suggested_labels_from == 14  # very fast: at most 300 labels
    # Progress per layer; cancelling returns None.
    seen = []
    assert zoom_load.analyse(project, profile, EXTENT,
                             lambda done, total, name: seen.append((done, total, name))) is not None
    assert [(d, t) for d, t, _ in seen] == [(0, 2), (1, 2)] and seen[0][2] == "Sűrű"
    assert zoom_load.analyse(project, profile, EXTENT, lambda *_: False) is None
    # In the window: the slider suggests again (and is remembered).
    from qgis.core import QgsSettings
    from q2vt_plugin.src.gui.zoom_load_dialog import SPEED_KEY, ZoomLoadDialog  # pylint: disable=import-error
    QgsSettings().remove(SPEED_KEY)
    try:
        window = ZoomLoadDialog(None, loads, factor, (8, 18))
        assert window.speed.value() == zoom_load.BALANCED
        window.speed.setValue(len(zoom_load.SPEEDS) - 1)
        assert window.picks[dense.id()]["features"].spin.value() == suggested[-1][0]
        assert int(QgsSettings().value(SPEED_KEY)) == len(zoom_load.SPEEDS) - 1
    finally:
        QgsSettings().remove(SPEED_KEY)


def test_zoomed_out_load_dialog_applies_the_checked_limits(plugin, monkeypatch, tmp_path):
    for name in ("warning", "information", "critical"):
        monkeypatch.setattr(QMessageBox, name, lambda *a, **k: None)
    project = reset_project()
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    project.addMapLayer(parcels)
    from q2vt_plugin.src.gui.publish_dialog import PublishDialog  # pylint: disable=import-error
    from q2vt_plugin.src.gui.zoom_load_dialog import ZoomLoadDialog, _ZoomPick  # pylint: disable=import-error
    from q2vt_plugin.src.publishing import zoom_load  # pylint: disable=import-error
    dialog = PublishDialog(iface=None)
    dialog.profile.view.extent = [EXTENT.xMinimum(), EXTENT.yMinimum(), EXTENT.xMaximum(), EXTENT.yMaximum()]
    item = next(dialog._tree_items())  # pylint: disable=protected-access
    item.setCheckState(1, Qt.CheckState.Checked)
    # The analysis itself is covered above; here a heavy result is offered.
    load = zoom_load.LayerLoad(parcels.id(), parcels.name(), "polygon", 50000, 11,
                               tile_features={z: 50000 for z in range(11, 17)},
                               tile_bytes={z: 2_000_000 for z in range(11, 17)},
                               suggested_from=13, labels=True, labels_from=11,
                               label_bytes={z: 900_000 for z in range(11, 17)},
                               suggested_labels_from=15)
    monkeypatch.setattr(zoom_load, "analyse", lambda *a: ([load], 1.1e8))
    seen = {}

    def accept(window):
        seen["window"] = window
        assert isinstance(window, ZoomLoadDialog)
        assert "(zoom 11, all layers together)" in window.summary.text()
        picks = window.picks[parcels.id()]
        assert isinstance(picks["features"], _ZoomPick) and picks["features"].spin.value() == 13
        picks["labels"].spin.setValue(16)          # the user moves the labels one zoom further
        return True

    assert dialog.analyse_zoom_load(accept)
    low, high, labels_low = dialog._item_scales(item)  # pylint: disable=protected-access
    assert (low, high) == (zoom_load.scale_for_zoom(1.1e8, 13), 0.0)
    assert labels_low == zoom_load.scale_for_zoom(1.1e8, 16)
    assert "labels 1:" in item.text(5)
    config = dialog.collect().layers[0]
    assert (config.min_scale, config.labels_min_scale) == (low, labels_low)
    from q2vt_plugin.src.publishing.profile import dumps, load_profile  # pylint: disable=import-error
    assert load_profile(dumps(dialog.collect())).layers[0].labels_min_scale == labels_low
    # Unchecking a suggestion leaves that limit as it is.
    window = ZoomLoadDialog(None, [load], 1.1e8, (11, 16))
    window.picks[parcels.id()]["features"].check.setChecked(False)
    assert window.chosen() == {parcels.id(): (None, zoom_load.scale_for_zoom(1.1e8, 15))}
    # The Visible scales dialog shows and returns the labels limit too.
    from q2vt_plugin.src.gui.scale_range import ScaleRangeDialog  # pylint: disable=import-error
    scales = ScaleRangeDialog(None, 25000.0, 0.0, 1, "", None, 4000.0)
    assert scales.labels_check.isChecked() and scales.values() == (25000.0, 0.0, 4000.0)
    scales.labels_check.setChecked(False)
    assert scales.values() == (25000.0, 0.0, 0.0)
    dialog.close()


def test_export_points_out_a_slow_zoomed_out_map(plugin, monkeypatch, tmp_path):
    """Before an export, a map that will be slow zoomed out is pointed out:
    "Make it faster…" opens the Zoomed-out load suggestions (applied before
    the export), Cancel stops the export, and "Don't check this" stops the
    check for later exports."""
    for name in ("warning", "information", "critical"):
        monkeypatch.setattr(QMessageBox, name, lambda *a, **k: None)
    from qgis.core import QgsSettings
    project = reset_project()
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    project.addMapLayer(parcels)
    from q2vt_plugin.src.gui import zoom_load_dialog  # pylint: disable=import-error
    from q2vt_plugin.src.gui.publish_dialog import PublishDialog  # pylint: disable=import-error
    from q2vt_plugin.src.publishing import zoom_load  # pylint: disable=import-error
    key = PublishDialog.ZOOM_LOAD_CHECK_KEY
    QgsSettings().remove(key)
    QgsSettings().remove(zoom_load_dialog.SPEED_KEY)
    try:
        dialog = PublishDialog(iface=None)
        dialog.profile.view.extent = [EXTENT.xMinimum(), EXTENT.yMinimum(), EXTENT.xMaximum(), EXTENT.yMaximum()]
        item = next(dialog._tree_items())  # pylint: disable=protected-access
        item.setCheckState(1, Qt.CheckState.Checked)
        load = zoom_load.LayerLoad(parcels.id(), parcels.name(), "polygon", 50000, 11,
                                   tile_features={z: 50000 for z in range(11, 17)},
                                   tile_bytes={z: 2_000_000 for z in range(11, 17)}, suggested_from=13)
        runs = []
        monkeypatch.setattr(zoom_load, "analyse", lambda *a: runs.append(1) or ([load], 1.1e8))
        monkeypatch.setattr(dialog, "_confirm_extent", lambda: True)
        exported = []
        monkeypatch.setattr(dialog, "save_settings", lambda: exported.append(1) and False)
        asked = []

        def ask(answer, remind):
            def _ask(slow):
                asked.append([l.name for l in slow])
                return answer, remind
            return _ask
        monkeypatch.setattr(dialog, "_ask_zoom_load", ask("cancel", True))
        assert not dialog.export_locally() and asked == [[parcels.name()]] and not exported
        monkeypatch.setattr(zoom_load_dialog.ZoomLoadDialog, "exec", lambda self: 1)
        monkeypatch.setattr(dialog, "_ask_zoom_load", ask("faster", False))
        dialog.export_locally()
        assert exported  # the export goes on, with the suggested limit set
        assert dialog._item_scales(item)[0] == zoom_load.scale_for_zoom(1.1e8, 13)  # pylint: disable=protected-access
        assert str(QgsSettings().value(key)).lower() in ("false", "0")
        before = len(runs)
        dialog.export_locally()  # not checked again
        assert len(runs) == before and len(asked) == 2
        dialog.close()
    finally:
        QgsSettings().remove(key)


def test_an_answered_zoomed_out_check_is_not_run_again_until_something_changes(plugin, monkeypatch, tmp_path):
    """The estimate before an export runs once: a cancelled export asks again
    from the same estimate; once answered ("Export as it is", applied limits,
    or seen with the Zoomed-out load… button) the next export does not check
    again, until something the estimate reads changes (here the layer's
    symbology, then the extent)."""
    for name in ("warning", "information", "critical"):
        monkeypatch.setattr(QMessageBox, name, lambda *a, **k: None)
    from qgis.core import QgsFillSymbol, QgsSettings, QgsSingleSymbolRenderer
    project = reset_project()
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    project.addMapLayer(parcels)
    from q2vt_plugin.src.gui import zoom_load_dialog  # pylint: disable=import-error
    from q2vt_plugin.src.gui.publish_dialog import PublishDialog  # pylint: disable=import-error
    from q2vt_plugin.src.publishing import zoom_load  # pylint: disable=import-error
    key = PublishDialog.ZOOM_LOAD_CHECK_KEY
    QgsSettings().remove(key)
    QgsSettings().remove(zoom_load_dialog.SPEED_KEY)
    try:
        dialog = PublishDialog(iface=None)
        dialog.profile.view.extent = [EXTENT.xMinimum(), EXTENT.yMinimum(), EXTENT.xMaximum(), EXTENT.yMaximum()]
        item = next(dialog._tree_items())  # pylint: disable=protected-access
        item.setCheckState(1, Qt.CheckState.Checked)
        load = zoom_load.LayerLoad(parcels.id(), parcels.name(), "polygon", 50000, 11,
                                   tile_features={z: 50000 for z in range(11, 17)},
                                   tile_bytes={z: 2_000_000 for z in range(11, 17)}, suggested_from=13)
        runs, asked, answers = [], [], ["cancel", "as-is", "as-is"]
        monkeypatch.setattr(zoom_load, "analyse", lambda *a: runs.append(1) or ([load], 1.1e8))
        monkeypatch.setattr(dialog, "_confirm_extent", lambda: True)
        monkeypatch.setattr(dialog, "save_settings", lambda: False)
        monkeypatch.setattr(dialog, "_ask_zoom_load", lambda slow: (asked.append(1) or answers.pop(0), True))
        check = dialog._check_zoom_load_before_export  # pylint: disable=protected-access
        assert not check() and (len(runs), len(asked)) == (1, 1)  # cancelled
        assert check() and (len(runs), len(asked)) == (1, 2)      # asked again, not estimated again
        assert check() and (len(runs), len(asked)) == (1, 2)      # answered: not checked again
        parcels.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "red"})))
        assert check() and (len(runs), len(asked)) == (2, 3)      # the symbology changed
        assert check() and (len(runs), len(asked)) == (2, 3)
        dialog.profile.view.extent = [EXTENT.xMinimum(), EXTENT.yMinimum(),
                                      EXTENT.xMaximum() + 500, EXTENT.yMaximum()]
        dialog._populate(dialog.profile)  # pylint: disable=protected-access
        answers.append("as-is")
        assert check() and len(runs) == 3                        # the extent changed
        # Seen with the Zoomed-out load… button: the export does not ask.
        parcels.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "blue"})))
        assert not dialog.analyse_zoom_load(lambda window: False) and len(runs) == 4
        assert check() and (len(runs), len(asked)) == (4, 4)
        dialog.close()
    finally:
        QgsSettings().remove(key)


def _heavy_load(layer_id="p", kind="polygon", **extra):
    """Visible features (1 px at zoom 0) too many per tile up to zoom 11:
    light from zoom 12 on (12 500 features, 375 KB)."""
    from publishing import zoom_load
    features = {z: 200000 // 4 ** (z - 10) for z in range(10, 19)}
    extra.setdefault("feature_px", 1.0)
    return zoom_load.LayerLoad(layer_id, "Telkek", kind, 200000, 10, tile_features=features,
                               tile_bytes={z: n * 30 for z, n in features.items()}, **extra)


def test_zoomed_out_load_suggests_merged_or_images_for_heavy_visible_layers(plugin):
    """Heavy where its features are still visible: not hidden, but drawn
    merged (polygons) or as images (points, lines) below the first light
    zoom; a mode already set counts in the load and only its zoom moves."""
    from publishing import zoom_load
    polygons, points = _heavy_load(), _heavy_load("q", "point")
    zoom_load.resuggest([polygons, points], 18, zoom_load.BALANCED)
    assert polygons.suggested_from is None  # visible: not hidden
    assert (polygons.suggested_mode, polygons.suggested_mode_below) == ("merged", 12)
    assert polygons.mode_suggested() and polygons.modes() == ("full", "merged", "image")
    assert points.suggested_mode == "image" and points.modes() == ("full", "image")
    # Set already, and light: no suggestion; the load counts the merged copies.
    done = _heavy_load(zoomed_out="merged", zoomed_out_below=12)
    zoom_load.resuggest([done], 18, zoom_load.BALANCED)
    assert not done.heavy(10) and done.heavy(10, mode="full") and done.drawn(10)[1] == 6_000_000 * zoom_load.MERGED_SHARE
    assert done.suggested_mode is None and not done.mode_suggested()
    # Set too low: the same mode from a closer zoom.
    low = _heavy_load(zoomed_out="image", zoomed_out_below=11)
    zoom_load.resuggest([low], 18, zoom_load.BALANCED)
    assert (low.suggested_mode, low.suggested_mode_below) == ("image", 12) and low.mode_suggested()
    # Hidden there by a suggested limit: offered, not ticked.
    specks = _heavy_load(feature_px=1e-3)  # 2 px only from zoom 11
    zoom_load.resuggest([specks], 18, zoom_load.BALANCED)
    assert specks.suggested_from == 11 and specks.suggested_mode == "merged"
    assert specks.mode_suggested()  # zoom 11 is still drawn, and heavy
    specks.tile_bytes[11] = specks.tile_features[11] = 0
    zoom_load.resuggest([specks], 18, zoom_load.BALANCED)
    assert specks.suggested_mode == "merged" and not specks.mode_suggested()


def test_zoomed_out_load_dialog_applies_the_drawing_mode(plugin, monkeypatch, tmp_path):
    for name in ("warning", "information", "critical"):
        monkeypatch.setattr(QMessageBox, name, lambda *a, **k: None)
    project = reset_project()
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    project.addMapLayer(parcels)
    from q2vt_plugin.src.gui.publish_dialog import COL_ZOOMED, PublishDialog  # pylint: disable=import-error
    from q2vt_plugin.src.gui.zoom_load_dialog import ZoomLoadDialog, _ModePick  # pylint: disable=import-error
    from q2vt_plugin.src.publishing import zoom_load  # pylint: disable=import-error
    dialog = PublishDialog(iface=None)
    dialog.profile.view.extent = [EXTENT.xMinimum(), EXTENT.yMinimum(), EXTENT.xMaximum(), EXTENT.yMaximum()]
    item = next(dialog._tree_items())  # pylint: disable=protected-access
    item.setCheckState(1, Qt.CheckState.Checked)
    load = _heavy_load(parcels.id())
    zoom_load.resuggest([load], 18, zoom_load.BALANCED)
    monkeypatch.setattr(zoom_load, "analyse", lambda *a: ([load], 1.1e8))

    def accept(window):
        pick = window.picks[parcels.id()]["mode"]
        assert isinstance(pick, _ModePick) and pick.check.isChecked()
        assert (pick.mode.currentData(), pick.spin.value()) == ("merged", 12)
        assert "With the checked limits" in window.summary.text()
        pick.spin.setValue(13)
        return True

    assert dialog.analyse_zoom_load(accept)
    assert item.text(COL_ZOOMED) == "merged < z13"
    config = dialog.collect().layer(parcels.id())
    assert (config.zoomed_out, config.zoomed_out_below) == ("merged", 13)
    assert dialog._item_scales(item)[0] == 0.0  # no limit: still visible  # pylint: disable=protected-access
    # Unticked: nothing changes; a mode set back to every feature is removed.
    window = ZoomLoadDialog(None, [load], 1.1e8, (10, 18))
    window.picks[parcels.id()]["mode"].check.setChecked(False)
    assert window.chosen_modes() == {}
    done = _heavy_load(parcels.id(), zoomed_out="merged", zoomed_out_below=12)
    zoom_load.resuggest([done], 18, zoom_load.BALANCED)
    window = ZoomLoadDialog(None, [done], 1.1e8, (10, 18))
    pick = window.picks[parcels.id()]["mode"]
    assert not pick.check.isChecked() and (pick.mode.currentData(), pick.spin.value()) == ("merged", 12)
    assert "merged" in window.table.item(0, 2).text()
    pick.mode.setCurrentIndex(0)
    assert window.chosen_modes() == {parcels.id(): ("full", None)}
    # The analysis reads the mode set in the layer list.
    from qgis.core import QgsRectangle
    profile = dialog.collect()
    dialog.close()
    monkeypatch.undo()
    for name in ("warning", "information", "critical"):
        monkeypatch.setattr(QMessageBox, name, lambda *a, **k: None)
    loads, _factor = zoom_load.analyse(project, profile, QgsRectangle(EXTENT))
    assert (loads[0].zoomed_out, loads[0].zoomed_out_below) == ("merged", 13)


def test_merging_suits_only_plain_fills_of_a_few_styles(plugin):
    """merge_fit: plain fills without outlines, a few categories: merged;
    outlines, pattern fills, data-defined colours, effects or too many
    styles: images (merging would lose or distort them)."""
    from qgis.core import (QgsCategorizedSymbolRenderer, QgsFillSymbol, QgsLinePatternFillSymbolLayer,
                           QgsProperty, QgsRendererCategory, QgsSingleSymbolRenderer, QgsSymbolLayer)
    from qgis.PyQt.QtGui import QColor
    from publishing import zoom_load

    def fill(outline=False):
        return QgsFillSymbol.createSimple({"color": "200,180,120,255",
                                           "outline_style": "solid" if outline else "no"})

    def categories(count, outline=False):
        return QgsCategorizedSymbolRenderer("zone", [QgsRendererCategory(str(i), fill(outline), str(i))
                                                     for i in range(count)])
    assert zoom_load.merge_fit(categories(6)) == (6, "")
    assert zoom_load.merge_fit(QgsSingleSymbolRenderer(fill())) == (1, "")
    styles, note = zoom_load.merge_fit(categories(6, outline=True))
    assert styles == 6 and "outlines" in note
    see_through = fill()
    see_through.symbolLayer(0).setStrokeStyle(Qt.PenStyle.SolidLine)
    see_through.symbolLayer(0).setStrokeColor(QColor(0, 0, 0, 0))
    assert zoom_load.merge_fit(QgsSingleSymbolRenderer(see_through)) == (1, "")  # an invisible outline
    pattern = fill()
    pattern.appendSymbolLayer(QgsLinePatternFillSymbolLayer())
    assert "LinePatternFill" in zoom_load.merge_fit(QgsSingleSymbolRenderer(pattern))[1]
    coloured = fill()
    fill_color = getattr(QgsSymbolLayer, "PropertyFillColor", None) or QgsSymbolLayer.Property.FillColor
    coloured.symbolLayer(0).setDataDefinedProperty(fill_color,
                                                   QgsProperty.fromExpression("color_rgb(\"v\", 0, 0)"))
    assert "data-defined" in zoom_load.merge_fit(QgsSingleSymbolRenderer(coloured))[1]
    many = zoom_load.merge_fit(categories(zoom_load.MAX_MERGED_STYLES + 1))
    assert many[0] == zoom_load.MAX_MERGED_STYLES + 1 and "too many" in many[1]
    # The suggestion follows it; more styles leave more of the tile merged.
    plain, outlined = _heavy_load(), _heavy_load(merge_note="outlines")
    zoom_load.resuggest([plain, outlined], 18, zoom_load.BALANCED)
    assert plain.suggested_mode == "merged" and outlined.suggested_mode == "image"
    assert outlined.modes() == ("full", "merged", "image")  # still offered by hand
    assert _heavy_load(styles=12).merged_share() == 2 * plain.merged_share()
