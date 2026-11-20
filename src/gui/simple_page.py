"""
simple_page.py

The Publish window's simple view: the few settings a first web map needs,
in plain words, and one button that makes it in the local output folder.

It has no settings of its own. Every control reads and writes the
advanced view's controls (and the window's layer settings), so the two
views always show the same settings, switching never changes or loses
anything, and the window saves and exports them as it always does.
"""

import math
import os
import shutil

from qgis.core import QgsMapLayer, QgsRasterLayer
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import (QButtonGroup, QComboBox, QFileDialog, QFrame,
                                 QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
                                 QRadioButton, QScrollArea, QSlider, QTableWidget,
                                 QTableWidgetItem, QVBoxLayout, QWidget)

# How close visitors can zoom: (words, tile zoom). The browser zooms a
# little closer still (it enlarges the last tiles).
ZOOM_STOPS = (("Region", 12), ("Town", 14), ("Streets", 16), ("Buildings", 18))
# Fields left out of "Show its information when clicked": ids and the
# like, not information for visitors.
TECHNICAL_FIELDS = {"fid", "id", "ogc_fid", "objectid", "gid", "oid", "rowid", "pk", "uuid", "guid",
                    "shape_length", "shape_area", "shape_leng"}
CHECKED, UNCHECKED = Qt.CheckState.Checked, Qt.CheckState.Unchecked


def tr(text: str) -> str:
    return QCoreApplication.translate("PublishDialog", text)


def visitor_fields(layer):
    """The fields "Show its information when clicked" publishes: all but ids,
    technical and binary ones."""
    out = []
    for field in layer.fields():
        name = field.name()
        low = name.lower()
        if low in TECHNICAL_FIELDS or low.startswith("q2vt") or low.endswith("_id"):
            continue
        if "blob" in field.typeName().lower() or "binary" in field.typeName().lower():
            continue
        out.append(name)
    return out


def _heading(number: int, text: str) -> QLabel:
    label = QLabel(f"<b>{number}.&nbsp;&nbsp;{text}</b>")
    font = label.font()
    font.setPointSizeF(font.pointSizeF() * 1.15)
    label.setFont(font)
    return label


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    font = label.font()
    font.setPointSizeF(font.pointSizeF() * 0.92)
    font.setItalic(True)
    label.setFont(font)
    return label


class SimplePage(QWidget):
    """The simple view of ``dialog`` (a PublishDialog): the settings scroll,
    the button that makes the map stays in sight below them."""

    def __init__(self, dialog):
        super().__init__()
        self.dialog = dialog
        self._updating = False
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        page_layout.addWidget(scroll, 1)
        page = QWidget()
        scroll.setWidget(page)
        outer = QHBoxLayout(page)
        column = QWidget()
        column.setMaximumWidth(860)
        outer.addStretch(1)
        outer.addWidget(column, 100)
        outer.addStretch(1)
        layout = QVBoxLayout(column)
        layout.setSpacing(8)
        intro = QLabel(tr("Make a web map of this project in a few steps. It is written to a folder on "
                          "this computer, ready to open in a browser or to copy to any web server. "
                          "The settings are kept in the project."))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # 1. Title
        layout.addWidget(_heading(1, tr("Title")))
        self.title = QLineEdit()
        self.title.setPlaceholderText(tr("e.g. Town map of Arló"))
        self.title.textEdited.connect(self._title_edited)
        layout.addWidget(self.title)

        # 2. Layers
        layout.addWidget(_heading(2, tr("Layers")))
        self.layers = QTableWidget(0, 3)
        self.layers.setHorizontalHeaderLabels([tr("Layer"), tr("On the map"),
                                               tr("Show its information when clicked")])
        header = self.layers.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.layers.verticalHeader().setVisible(False)
        self.layers.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.layers.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.layers.setMinimumHeight(210)
        self.layers.verticalHeader().setDefaultSectionSize(self.layers.fontMetrics().height() + 12)
        self.layers.itemChanged.connect(self._layer_item_changed)
        layout.addWidget(self.layers, 1)
        row = QHBoxLayout()
        visible = QPushButton(tr("Use the layers visible in QGIS"))
        visible.clicked.connect(self._use_visible_layers)
        row.addWidget(visible)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(_hint(tr("Information shown when a feature is clicked (its attributes, without ids) "
                                  "can be seen by anyone who opens the map.")))

        # 3. Area
        layout.addWidget(_heading(3, tr("Area")))
        area = QHBoxLayout()
        self.area = QComboBox()
        self.area.addItem(tr("What the QGIS map shows now"), "canvas")
        self.area.addItem(tr("The extent of a layer"), "layer")
        self.area.currentIndexChanged.connect(self._area_changed)
        self.area_layer = QComboBox()
        self.area_layer.currentIndexChanged.connect(self._area_changed)
        area.addWidget(self.area)
        area.addWidget(self.area_layer, 1)
        layout.addLayout(area)
        self.area_info = _hint("")
        layout.addWidget(self.area_info)

        # 4. How close visitors can zoom
        layout.addWidget(_heading(4, tr("How close visitors can zoom")))
        self.zoom = QSlider(Qt.Orientation.Horizontal)
        self.zoom.setRange(0, len(ZOOM_STOPS) - 1)
        self.zoom.setPageStep(1)
        self.zoom.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.zoom.setTickInterval(1)
        self.zoom.valueChanged.connect(self._zoom_changed)
        layout.addWidget(self.zoom)
        words_row = QHBoxLayout()  # under the stops: the first and last at the ends
        for index, (words, _zoom) in enumerate(ZOOM_STOPS):
            if index:
                words_row.addStretch(1)
            words_row.addWidget(QLabel(tr(words)))
        layout.addLayout(words_row)
        self.zoom_info = _hint("")
        layout.addWidget(self.zoom_info)

        # 5. Background map
        layout.addWidget(_heading(5, tr("Background map")))
        background = QHBoxLayout()
        self.bg_none = QRadioButton(tr("None: only the project's layers"))
        self.bg_osm = QRadioButton(tr("OpenStreetMap: streets, water and place names under your layers"))
        self.bg_group = QButtonGroup(self)
        for button in (self.bg_none, self.bg_osm):
            self.bg_group.addButton(button)
            background.addWidget(button)
            button.toggled.connect(self._background_changed)
        background.addStretch(1)
        layout.addLayout(background)
        layout.addWidget(_hint(tr("OpenStreetMap is downloaded for the area while the map is made "
                                  "(an internet connection is needed then, not later).")))

        # 6. Folder
        layout.addWidget(_heading(6, tr("Save in folder")))
        folder = QHBoxLayout()
        self.folder = QLineEdit()
        self.folder.textEdited.connect(self._folder_edited)
        browse = QPushButton(tr("Browse…"))
        browse.clicked.connect(self._browse)
        folder.addWidget(self.folder, 1)
        folder.addWidget(browse)
        layout.addLayout(folder)

        # Advanced settings in use
        self.advanced_note = QLabel()
        self.advanced_note.setWordWrap(True)
        self.advanced_note.setTextFormat(Qt.TextFormat.RichText)
        self.advanced_note.linkActivated.connect(lambda _link: self.dialog.set_simple_view(False))
        layout.addWidget(self.advanced_note)

        layout.addWidget(_hint(tr("To put it online, copy the map's folder to any web server, or use "
                                  "Publish in the advanced view (Cloudflare R2, S3 or an SSH server).")))
        layout.addStretch(1)

        # Make it (always in sight)
        bar = QFrame()
        bar.setFrameShape(QFrame.Shape.StyledPanel)
        bar_layout = QHBoxLayout(bar)
        self.make = QPushButton(tr("Make web map"))
        font = self.make.font()
        font.setPointSizeF(font.pointSizeF() * 1.2)
        font.setBold(True)
        self.make.setFont(font)
        self.make.setMinimumHeight(44)
        self.make.setMinimumWidth(220)
        self.make.setDefault(True)
        self.make.clicked.connect(self.make_map)
        bar_layout.addWidget(self.make)
        done = bar_layout
        self.open_browser = QPushButton(tr("Open in browser"))
        self.open_browser.clicked.connect(self.dialog.preview)
        self.open_folder = QPushButton(tr("Open folder"))
        self.open_folder.clicked.connect(self.dialog.open_folder)
        self.zip = QPushButton(tr("Make a ZIP to send"))
        self.zip.setToolTip(tr("One file with the whole web map, e.g. to send to a colleague or a web host"))
        self.zip.clicked.connect(self.make_zip)
        for button in (self.open_browser, self.open_folder, self.zip):
            button.setMinimumHeight(44)
            done.addWidget(button)
        done.addStretch(1)
        page_layout.addWidget(bar)

    # -- reading the window's settings ------------------------------------------------
    def refresh(self):
        """Show the window's current settings."""
        dialog = self.dialog
        self._updating = True
        try:
            self.title.setText(dialog.e_title.text())
            self._fill_layers()
            mode = dialog.profile.view.extent_mode
            self.area.blockSignals(True)
            fixed = self.area.findData("fixed")
            if mode == "fixed" and fixed < 0:
                self.area.addItem(tr("A drawn or frozen area (advanced view)"), "fixed")
            elif mode != "fixed" and fixed >= 0:
                self.area.removeItem(fixed)
            self.area.setCurrentIndex(max(0, self.area.findData(mode)))
            self.area.blockSignals(False)
            self._fill_area_layers()
            maximum = dialog.e_max_zoom.value()
            nearest = min(range(len(ZOOM_STOPS)), key=lambda i: abs(ZOOM_STOPS[i][1] - maximum))
            self.zoom.setValue(nearest)
            (self.bg_osm if dialog.b_kind.currentData() == "protomaps" else self.bg_none).setChecked(True)
            self.folder.setText(dialog.o_dir.text())
        finally:
            self._updating = False
        self._show_area()
        self._show_zoom()
        self.update_buttons()
        self._show_advanced()

    def _fill_layers(self):
        dialog = self.dialog
        dialog._store_layer_fields()  # pylint: disable=protected-access
        self.layers.blockSignals(True)
        self.layers.setRowCount(0)
        for item in self._ordered_items():
            layer_id = item.data(0, dialog.LAYER_ROLE)
            layer = dialog.project.mapLayer(layer_id)
            if layer is None:
                continue
            row = self.layers.rowCount()
            self.layers.insertRow(row)
            name = QTableWidgetItem(layer.name())
            name.setData(Qt.ItemDataRole.UserRole, layer_id)
            name.setIcon(item.icon(0))
            name.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.layers.setItem(row, 0, name)
            shown = QTableWidgetItem()
            shown.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            shown.setCheckState(item.checkState(dialog.COL_PUBLISH))
            self.layers.setItem(row, 1, shown)
            info = QTableWidgetItem()
            config = dialog.layer_configs.get(layer_id)
            if isinstance(layer, QgsRasterLayer) or layer.type() != QgsMapLayer.LayerType.VectorLayer:
                info.setFlags(Qt.ItemFlag.NoItemFlags)
                info.setToolTip(tr("An image layer: nothing to show when clicked"))
            else:
                info.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                info.setCheckState(CHECKED if config is not None and config.popup_fields else UNCHECKED)
            self.layers.setItem(row, 2, info)
        self.layers.blockSignals(False)

    def _ordered_items(self):
        """The layer rows of the advanced layer list, top to bottom (as in QGIS)."""
        out = []

        def walk(parent):
            for index in range(parent.childCount()):
                child = parent.child(index)
                if child.data(0, self.dialog.LAYER_ROLE):
                    out.append(child)
                walk(child)
        walk(self.dialog.tree.invisibleRootItem())
        return out

    def _fill_area_layers(self):
        dialog = self.dialog
        current = dialog.profile.view.extent_layer
        self.area_layer.blockSignals(True)
        self.area_layer.clear()
        for item in self._ordered_items():
            layer = dialog.project.mapLayer(item.data(0, dialog.LAYER_ROLE))
            if layer is not None:
                self.area_layer.addItem(layer.name(), layer.id())
        self.area_layer.setCurrentIndex(max(0, self.area_layer.findData(current)))
        self.area_layer.setVisible(self.area.currentData() == "layer")
        self.area_layer.blockSignals(False)

    def _show_area(self):
        dialog = self.dialog
        try:
            extent = dialog._current_extent_3857()  # pylint: disable=protected-access
        except Exception:  # noqa: BLE001 - shown as unknown
            extent = None
        if not extent:
            self.area_info.setText(tr("The map view when the map is made.") if self.area.currentData() == "canvas"
                                   else tr("Choose a layer."))
            return
        from ..publishing.raster_tiles import count_tiles  # pylint: disable=import-outside-toplevel
        width, height, _ = dialog._extent_size_km(extent)  # pylint: disable=protected-access
        tiles = count_tiles(extent, dialog.e_min_zoom.value(), dialog.e_max_zoom.value())
        self.area_info.setText(tr("About {w:.1f} × {h:.1f} km, {tiles} tiles.").format(
            w=width, h=height, tiles=f"{tiles:,}".replace(",", " ")))

    def _show_zoom(self):
        dialog = self.dialog
        self.zoom_info.setText(tr("Detail up to zoom level {z} (about 1:{scale}); the map opens zoomed out "
                                  "to the whole area.").format(
            z=dialog.e_max_zoom.value(),
            scale=f"{round(591657527.6 / 2 ** dialog.e_max_zoom.value(), -1):,.0f}".replace(",", " ")))

    def _show_advanced(self):
        """One line naming the advanced settings this project uses: kept and
        exported, though not shown here."""
        dialog = self.dialog
        used = []
        if dialog.profile.view.extent_mode == "fixed":
            used.append(tr("a drawn area"))
        if getattr(dialog, "p_enabled", None) is not None and dialog.p_enabled.isChecked():
            used.append(tr("the parcel report"))
        if getattr(dialog, "b_xyz", None) is not None and dialog.b_xyz.rowCount():
            used.append(tr("web basemaps"))
        if dialog.d_kind.currentData() not in ("local", None):
            used.append(tr("an online destination (used by Publish, not here)"))
        if getattr(dialog, "i_docs", None) is not None and dialog.i_docs.rowCount():
            used.append(tr("documents"))
        if dialog.e_description.toPlainText().strip():
            used.append(tr("a description"))
        self.advanced_note.setVisible(bool(used))
        if used:
            self.advanced_note.setText(tr("Also uses advanced settings: {} — kept as they are. "
                                          "<a href='advanced'>Show them</a>").format(", ".join(used)))

    def update_buttons(self):
        available = bool(self.dialog._local_map_dir())  # pylint: disable=protected-access
        for button in (self.open_browser, self.open_folder, self.zip):
            button.setEnabled(available)

    # -- writing them ------------------------------------------------------------------
    def _title_edited(self, text):
        dialog = self.dialog
        dialog.e_title.setText(text)
        dialog._title_edited(text)  # pylint: disable=protected-access  (the address follows)
        self.update_buttons()

    def _tree_item(self, layer_id):
        return next((item for item in self.dialog._tree_items()  # pylint: disable=protected-access
                     if item.data(0, self.dialog.LAYER_ROLE) == layer_id), None)

    def _layer_item_changed(self, cell):
        if self._updating:
            return
        dialog = self.dialog
        layer_id = self.layers.item(cell.row(), 0).data(Qt.ItemDataRole.UserRole)
        on = cell.checkState() == CHECKED
        if cell.column() == 1:
            item = self._tree_item(layer_id)
            if item is not None:
                item.setCheckState(dialog.COL_PUBLISH, CHECKED if on else UNCHECKED)
                if on:
                    item.setCheckState(dialog.COL_VISIBLE, CHECKED)
        elif cell.column() == 2:
            self.set_information(layer_id, on)
            if on:  # information of a layer not on the map is nowhere to click
                shown = self.layers.item(cell.row(), 1)
                if shown.checkState() != CHECKED:
                    shown.setCheckState(CHECKED)

    def set_information(self, layer_id, on: bool):
        """Popups of ``layer_id``: its visitor fields, or none."""
        from ..publishing.models import LayerConfig, PopupField  # pylint: disable=import-outside-toplevel
        dialog = self.dialog
        layer = dialog.project.mapLayer(layer_id)
        if layer is None:
            return
        dialog._store_layer_fields()  # pylint: disable=protected-access
        config = dialog.layer_configs.setdefault(layer_id, LayerConfig(layer_id))
        if on:
            kept = {p.field: p for p in config.popup_fields}
            config.popup_fields = [kept.get(name) or PopupField(name) for name in visitor_fields(layer)]
        else:
            config.popup_fields = []
        # The Interaction tab shows the layer settings again (its table held the old ones).
        dialog.current_layer_id = None
        try:
            dialog._fill_interaction_layers()  # pylint: disable=protected-access
        except Exception:  # noqa: BLE001 - it fills itself when shown
            pass

    def _use_visible_layers(self):
        self.dialog.publish_visible_layers()
        self.refresh()

    def _area_changed(self, *_):
        if self._updating:
            return
        dialog = self.dialog
        mode = self.area.currentData()
        self.area_layer.setVisible(mode == "layer")
        if mode == "layer":
            layer = dialog.project.mapLayer(self.area_layer.currentData() or "")
            if layer is not None:
                dialog.e_extent_layer.setLayer(layer)
        if mode != dialog.profile.view.extent_mode:
            dialog.e_extent_mode.setCurrentIndex(max(0, dialog.e_extent_mode.findData(mode)))
        self._fit_min_zoom()
        self._show_area()

    def _zoom_changed(self, index):
        if self._updating:
            return
        self.dialog.e_max_zoom.setValue(ZOOM_STOPS[index][1])
        self._fit_min_zoom()
        self._show_zoom()
        self._show_area()

    def _fit_min_zoom(self):
        """The farthest zoom out: a little beyond the whole area (no tiles of
        the whole country for a town map)."""
        dialog = self.dialog
        try:
            extent = dialog._current_extent_3857()  # pylint: disable=protected-access
        except Exception:  # noqa: BLE001
            extent = None
        if not extent:
            return
        from ..core.fidelity.zoom import fit_zoom  # pylint: disable=import-outside-toplevel
        whole = fit_zoom(extent[2] - extent[0], extent[3] - extent[1], 0, 22)
        dialog.e_min_zoom.setValue(max(0, min(dialog.e_max_zoom.value(), int(math.floor(whole)) - 2)))

    def _background_changed(self, *_):
        if self._updating:
            return
        kind = "protomaps" if self.bg_osm.isChecked() else "none"
        combo = self.dialog.b_kind
        combo.setCurrentIndex(max(0, combo.findData(kind)))

    def _folder_edited(self, text):
        self.dialog.o_dir.setText(text)
        self.update_buttons()

    def _browse(self):
        start = self.folder.text().strip() or os.path.dirname(self.dialog.project.fileName())
        path = QFileDialog.getExistingDirectory(self, tr("Save in folder"), start)
        if path:
            self.folder.setText(path)
            self._folder_edited(path)

    # -- actions ----------------------------------------------------------------------------
    def make_map(self) -> bool:
        """Export locally, whatever the advanced view's destination."""
        done = self.dialog.export_locally()
        self.update_buttons()
        if done:
            self.dialog.status.setText(tr("Your web map is ready. Open it in your browser, or open its folder.")
                                       + "  (" + self.dialog._local_map_dir() + ")")  # pylint: disable=protected-access
        return done

    def make_zip(self) -> str:
        """``<map folder>.zip`` next to the map's folder; opens the folder holding it."""
        folder = self.dialog._local_map_dir()  # pylint: disable=protected-access
        if not folder:
            return ""
        archive = shutil.make_archive(folder.rstrip(os.sep), "zip", os.path.dirname(folder.rstrip(os.sep)),
                                      os.path.basename(folder.rstrip(os.sep)))
        self.dialog.status.setText(tr("ZIP ready: {}").format(archive))
        from qgis.PyQt.QtCore import QUrl  # pylint: disable=import-outside-toplevel
        from qgis.PyQt.QtGui import QDesktopServices  # pylint: disable=import-outside-toplevel
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(archive)))
        return archive
