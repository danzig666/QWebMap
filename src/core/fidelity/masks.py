"""
masks.py

QGIS selective masking on the web map, approximated. QGIS cuts the chosen
symbol layers around a label (a label's mask) or a mask marker's shape, so
what lies under those symbol layers shows through. MapLibre cannot cut one
layer with another's shape, so:

- a label's mask becomes the label's halo in the map's background colour
  (a halo of the mask's size, as strong as the mask's opacity): it covers
  everything under the label, not only the masked symbol layers;
- a mask marker becomes its shape drawn in the background colour, where
  the marker is, over the layers drawn before it.

Both are exact over a plain background (the usual case: contour labels,
road labels, symbols knocking out the lines under them) and are reported as
approximate (Q2VT_MASK_APPROXIMATE).

QGIS 4 also masks through the project's selective masking source sets: a
masked symbol layer names a set (selectiveMaskingSourceSetId) and the set
lists the labels / layers masking it. resolve_source_sets() turns them back
into the masker-side lists the approximation reads.
"""

from typing import Dict, List, Optional, Tuple

from qgis.core import Qgis, QgsProject, QgsStyle, QgsStyleEntityVisitorInterface, QgsSymbolLayer, \
    QgsSymbolLayerReference
from qgis.PyQt.QtGui import QColor

_COLOUR_PROPERTIES = ("PropertyFillColor", "PropertyStrokeColor", "PropertyColor",
                      "PropertySecondaryColor")


def background_colour(project=None) -> QColor:
    """The map's background colour (QGIS draws masks over it)."""
    project = project or QgsProject.instance()
    colour = QColor(project.backgroundColor())
    return colour if colour.isValid() else QColor(255, 255, 255)


def label_mask(text_format) -> Optional[object]:
    """The label's mask settings when it masks anything, else None."""
    mask = text_format.mask() if hasattr(text_format, "mask") else None
    if mask is None or not mask.enabled() or not mask.maskedSymbolLayers():
        return None
    return mask


# QGIS 4.0 brought source sets and, with them, mask markers that draw their
# mask whatever their own list (QgsMaskMarkerSymbolLayer::renderPoint no
# longer returns when it is empty).
HAS_SOURCE_SETS = hasattr(QgsSymbolLayer, "selectiveMaskingSourceSetId")


class _SetMembers(QgsStyleEntityVisitorInterface):
    """The symbol layers of a renderer that name a source set, sub-symbols
    included, visited as QgsVectorLayerUtils::collectObjectsMasked*FromLayer
    visit them (symbol rules only)."""

    def __init__(self):
        super().__init__()
        self.members: List[QgsSymbolLayer] = []

    def visitEnter(self, node):  # noqa: N802  pylint: disable=invalid-name
        return node.type == QgsStyleEntityVisitorInterface.NodeType.SymbolRule

    def visit(self, leaf):
        entity = leaf.entity
        if entity is not None and entity.type() == QgsStyle.StyleEntity.SymbolEntity \
                and entity.symbol() is not None:
            self._symbol(entity.symbol())
        return True

    def _symbol(self, symbol) -> None:
        for layer in symbol.symbolLayers():
            if layer.selectiveMaskingSourceSetId():
                self.members.append(layer)
            if layer.subSymbol() is not None:
                self._symbol(layer.subSymbol())


class SourceSetMasks:
    """What the project's source sets mask, by masker: ``labels`` maps
    (layer id, labeling provider id) to the symbol layers its labels mask,
    ``layers`` maps a layer id to the symbol layers its mask markers mask."""

    def __init__(self):
        self.labels: Dict[Tuple[str, str], List[QgsSymbolLayerReference]] = {}
        self.layers: Dict[str, List[QgsSymbolLayerReference]] = {}


def resolve_source_sets(rendered_layers, project=None) -> SourceSetMasks:
    """The project's selective masking source sets (QGIS 4) resolved as QGIS
    resolves them (QgsVectorLayerUtils::collectObjectsMaskedByLabelsFromLayer
    and collectObjectsMaskedBySymbolLayersFromLayer, qgsvectorlayerutils.cpp):
    every symbol layer of a rendered layer's renderer that names a set is
    masked by each of the set's sources. A label source names its layer and
    labeling provider (the rule key, "" for simple labeling); a symbol layer
    source names its layer only, its source id is not read: the layer's mask
    markers draw the mask. Only the symbol layers of ``rendered_layers``
    count (QGIS passes the rendered vector layers); a set id the project
    does not have masks nothing."""
    found = SourceSetMasks()
    project = project or QgsProject.instance()
    if not HAS_SOURCE_SETS:
        return found
    sets = {s.id(): s for s in project.selectiveMaskingSourceSetManager().sets()}
    if not sets:
        return found
    label_type = Qgis.SelectiveMaskSourceType.Label
    for layer in rendered_layers:
        if layer is None or layer.renderer() is None:
            continue
        visitor = _SetMembers()
        layer.renderer().accept(visitor)
        for member in visitor.members:
            masking_set = sets.get(member.selectiveMaskingSourceSetId())
            if masking_set is None:
                continue
            ref = QgsSymbolLayerReference(layer.id(), member.id())
            for source in masking_set.sources():
                if not source.isValid():
                    continue
                if source.sourceType() == label_type:
                    targets = found.labels.setdefault((source.layerId(), source.sourceId() or ""), [])
                else:
                    targets = found.layers.setdefault(source.layerId(), [])
                if ref not in targets:
                    targets.append(ref)
    return found


def add_masked_symbol_layers(settings, refs) -> bool:
    """Appends ``refs`` to the masked symbol layers of a label's mask (in the
    QgsPalLayerSettings ``settings``): masking through a set masks as the
    list does. True when changed."""
    text_format = settings.format()
    mask = text_format.mask()
    masked = list(mask.maskedSymbolLayers())
    added = [ref for ref in refs if ref not in masked]
    if not added:
        return False
    mask.setMaskedSymbolLayers(masked + added)
    text_format.setMask(mask)
    settings.setFormat(text_format)
    return True


def _masks_exported(layer, exported) -> bool:
    """Whether a mask marker's own list names a layer that is drawn (all
    layers when ``exported`` is None): with nothing drawn to cut, QGIS shows
    nothing of it."""
    refs = layer.masks()
    return bool(refs) and (exported is None or any(ref.layerId() in exported for ref in refs))


def layer_masks(renderer, set_masks: SourceSetMasks, layer_id: str, exported=None) -> bool:
    """Whether the layer's mask markers draw a mask in QGIS 4: the layer
    masks anything, through a symbol layer's own list or a set naming the
    layer (QgsMapRendererJob::prepareSecondPassJobs gives the
    layer a mask painter; every mask marker draws in it). On QGIS 3 only a
    mask marker with its own list draws."""
    if not HAS_SOURCE_SETS or renderer is None:
        return False
    if set_masks.layers.get(layer_id):
        return True

    class _Lists(_SetMembers):
        def _symbol(self, symbol) -> None:
            for layer in symbol.symbolLayers():
                if _masks_exported(layer, exported):
                    self.members.append(layer)
                if layer.subSymbol() is not None:
                    self._symbol(layer.subSymbol())

    visitor = _Lists()
    renderer.accept(visitor)
    return bool(visitor.members)


def _recolour(symbol, colour: QColor) -> None:
    for layer in symbol.symbolLayers():
        layer.setColor(colour)
        for setter in ("setFillColor", "setStrokeColor"):
            if hasattr(layer, setter):
                getattr(layer, setter)(colour)
        properties = layer.dataDefinedProperties()
        for name in _COLOUR_PROPERTIES:
            key = getattr(QgsSymbolLayer.Property, name, None)
            if key is not None and properties.property(key) is not None:
                properties.property(key).setActive(False)
        layer.setDataDefinedProperties(properties)
        if layer.subSymbol() is not None:
            _recolour(layer.subSymbol(), colour)


def knock_out_mask_markers(symbol, colour: QColor, layer_masks: bool = False,
                           exported=None) -> int:
    """Replaces every enabled mask marker in ``symbol`` (its sub-symbols
    too) that masks anything by its shape in ``colour``; returns how many.
    One masks with its own list naming a drawn layer (``exported``: layer
    ids, None = all), or when ``layer_masks`` (its layer masks anything, see
    layer_masks()). One switched off draws nothing (it is dropped with the
    other disabled symbol layers); QgsMaskMarkerSymbolLayer.enabled() hides
    that flag (it means "masks anything"), so the base method reads it."""
    if symbol is None:
        return 0
    count = 0
    index = 0
    while index < symbol.symbolLayerCount():
        layer = symbol.symbolLayer(index)
        if layer.layerType() == "MaskMarker":
            # QGIS 3: one that masks nothing is not enabled() and draws
            # nothing; QGIS 4 draws it in its layer's mask, if any.
            shape = layer.subSymbol()
            if QgsSymbolLayer.enabled(layer) and (_masks_exported(layer, exported) or layer_masks) \
                    and shape is not None and shape.symbolLayerCount():
                shape = shape.clone()
                _recolour(shape, colour)
                for offset, part in enumerate(shape.symbolLayers()):
                    symbol.insertSymbolLayer(index + offset, part.clone())
                index += shape.symbolLayerCount()
                symbol.takeSymbolLayer(index)  # owned by Python, freed with it
                count += 1
                continue
        else:
            count += knock_out_mask_markers(layer.subSymbol(), colour, layer_masks, exported)
        index += 1
    return count
