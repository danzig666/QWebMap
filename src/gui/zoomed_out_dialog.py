"""How vector layers are drawn zoomed out (Interaction tab, Zoomed out
column): every feature, the features of one style merged per tile, or
images rendered by QGIS, below a zoom level."""

from typing import Optional, Tuple

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QSpinBox,
                                 QVBoxLayout)


def tr(text: str) -> str:
    return QCoreApplication.translate("ZoomedOut", text)

MODES = ("full", "merged", "image")


def mode_labels():
    return {"full": tr("Every feature (as now)"),
            "merged": tr("Merged: the features of one style joined per tile"),
            "image": tr("Image: rendered by QGIS")}


def zoomed_out_text(mode: str, below: Optional[int]) -> str:
    """The Zoomed out cell: "" (every feature), "merged < z13", "image < z13"."""
    if mode not in ("merged", "image") or not below:
        return ""
    return tr("{} < z{}").format(tr("merged") if mode == "merged" else tr("image"), int(below))


class ZoomedOutDialog(QDialog):
    def __init__(self, parent, mode: str = "full", below: Optional[int] = None, count: int = 1,
                 max_zoom: int = 16):
        super().__init__(parent)
        self.setWindowTitle(tr("Zoomed out"))
        layout = QVBoxLayout(self)
        intro = QLabel(tr(
            "How {} layer(s) are drawn when zoomed out beyond a zoom level. Dense layers (many "
            "parcels, buildings) make the web map slow there; these keep them visible but lighter:").format(count))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.mode = QComboBox()
        for key, label in mode_labels().items():
            self.mode.addItem(label, key)
        self.mode.setCurrentIndex(max(0, MODES.index(mode) if mode in MODES else 0))
        self.below = QSpinBox()
        self.below.setRange(1, 24)
        self.below.setPrefix(tr("below zoom "))
        self.below.setValue(int(below) if below else max(1, min(24, int(max_zoom) - 2)))
        form.addRow(tr("Zoomed out:"), self.mode)
        form.addRow("", self.below)
        layout.addLayout(form)
        notes = QLabel(tr(
            "Merged: features with the same style (and the same filter values) are joined into "
            "one shape per tile. Much lighter; the outlines between joined features and their "
            "popups are gone at those zooms.\n"
            "Image: QGIS renders the layer's symbols as images there, exactly as in QGIS; the "
            "lightest, but no popups or highlighting there, and the layer's category switches do "
            "not affect the images. Its labels stay as text.\n"
            "From the zoom set here on, every feature is drawn as usual."))
        notes.setWordWrap(True)
        layout.addWidget(notes)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.mode.currentIndexChanged.connect(self._sync)
        self._sync()

    def _sync(self, *_):
        self.below.setEnabled(self.mode.currentData() != "full")

    def values(self) -> Tuple[str, Optional[int]]:
        mode = self.mode.currentData()
        return (mode, int(self.below.value())) if mode != "full" else ("full", None)
