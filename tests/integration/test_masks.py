"""QGIS selective masking on the web map (fidelity.masks): a label's mask is
its halo in the map's background colour, a mask marker its shape in that
colour; both reported as approximate."""

import json
import os
import sys

import pytest
from qgis.core import (Qgis, QgsMarkerSymbol, QgsMaskMarkerSymbolLayer,
                       QgsPalLayerSettings, QgsSingleSymbolRenderer, QgsSymbolLayer,
                       QgsSymbolLayerReference, QgsTextFormat, QgsVectorLayerSimpleLabeling)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor

from q2vt_fixtures import reset_project, zoning_layer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_end_to_end import EXTENT, export  # noqa: E402,F401  pylint: disable=wrong-import-position,unused-import

BACKGROUND = QColor(250, 240, 200)


def _masked_labels(path, buffer=False):
    layer = zoning_layer(path=path)
    symbol = layer.renderer().symbol()
    target = symbol.symbolLayer(0)
    settings = QgsPalLayerSettings()
    settings.fieldName = "zone"
    fmt = QgsTextFormat()
    fmt.setSize(10)
    mask = fmt.mask()
    mask.setEnabled(True)
    mask.setSize(2.0)  # mm
    mask.setOpacity(0.8)
    mask.setMaskedSymbolLayers([QgsSymbolLayerReference(layer.id(), target.id())])
    fmt.setMask(mask)
    if buffer:
        fmt.buffer().setEnabled(True)
    settings.setFormat(fmt)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)
    return layer


def _style(result):
    return json.load(open(os.path.join(result, "style", "style.json"), encoding="utf-8"))


def _run(export, layer):  # noqa: F811
    project = reset_project(layer)
    project.setBackgroundColor(BACKGROUND)
    return export(layer, keep_project=True)


def test_label_mask_is_a_background_halo(export, tmp_path):  # noqa: F811
    exporter, result = _run(export, _masked_labels(str(tmp_path / "zones.gpkg")))
    labels = [l for l in _style(result)["layers"] if "text-field" in l.get("layout", {})]
    assert labels
    for label in labels:
        assert label["paint"]["text-halo-color"].replace(" ", "") in (
            "rgba(250,240,200,0.8)", "rgba(250,240,200,0.80)")
        # QGIS strokes the mask 2 mm wide around the glyphs: 1 mm beyond them.
        assert label["paint"]["text-halo-width"] == pytest.approx(96 / 25.4, rel=0.05)
    assert exporter.diagnostics.by_code("Q2VT_MASK_APPROXIMATE")


def test_label_buffer_stays_the_halo(export, tmp_path):  # noqa: F811
    _, result = _run(export, _masked_labels(str(tmp_path / "zones.gpkg"), buffer=True))
    labels = [l for l in _style(result)["layers"] if "text-field" in l.get("layout", {})]
    assert labels and all("250" not in str(l["paint"]["text-halo-color"]) for l in labels)


def test_mask_marker_is_its_shape_in_the_background_colour(plugin):
    from q2vt_plugin.src.core.fidelity import masks  # pylint: disable=import-error
    shape = QgsMarkerSymbol.createSimple({"name": "circle", "color": "255,0,0", "size": "6"})
    mask = QgsMaskMarkerSymbolLayer()
    mask.setSubSymbol(shape)
    mask.setMasks([QgsSymbolLayerReference("roads", "line-1")])
    symbol = QgsMarkerSymbol.createSimple({"name": "square", "color": "0,0,255", "size": "3"})
    symbol.insertSymbolLayer(0, mask)
    assert masks.knock_out_mask_markers(symbol, BACKGROUND) == 1
    drawn = symbol.symbolLayers()
    assert [l.layerType() for l in drawn] == ["SimpleMarker", "SimpleMarker"]
    knockout, own = drawn
    assert knockout.color() == BACKGROUND and knockout.strokeColor() == BACKGROUND
    assert knockout.size() == 6 and own.color() == QColor(0, 0, 255)
    # Masking nothing: QGIS draws nothing.
    idle = QgsMaskMarkerSymbolLayer()
    idle.setSubSymbol(QgsMarkerSymbol.createSimple({"name": "circle", "size": "6"}))
    other = QgsMarkerSymbol([idle])
    assert masks.knock_out_mask_markers(other, BACKGROUND) == 0
    assert not other.symbolLayer(0).enabled()  # skipped by the export
    # Unless its layer masks (QGIS 4 draws it in the layer's mask).
    assert masks.knock_out_mask_markers(other.clone(), BACKGROUND, layer_masks=True) == 1
    QgsSingleSymbolRenderer(symbol)  # still a valid symbol


def test_mask_marker_exports_as_a_knockout(export, tmp_path):  # noqa: F811
    from qgis.core import QgsFeature, QgsGeometry, QgsVectorLayer  # pylint: disable=import-outside-toplevel
    from q2vt_fixtures import to_geopackage  # pylint: disable=import-outside-toplevel
    layer = QgsVectorLayer("Point?crs=EPSG:3857", "signs", "memory")
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromWkt("POINT(2121000 6021000)"))
    layer.dataProvider().addFeatures([feature])
    layer = to_geopackage(layer, str(tmp_path / "signs.gpkg"))
    mask = QgsMaskMarkerSymbolLayer()
    mask.setSubSymbol(QgsMarkerSymbol.createSimple({"name": "circle", "color": "255,0,0", "size": "6"}))
    mask.setMasks([QgsSymbolLayerReference("roads", "line-1")])
    symbol = QgsMarkerSymbol.createSimple({"name": "square", "color": "0,0,255", "size": "3"})
    symbol.insertSymbolLayer(0, mask)
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    exporter, result = _run(export, layer)
    assert not [d for d in exporter.diagnostics.by_code("Q2VT_UNSUPPORTED_SYMBOL_LAYER")
                if "MaskMarker" in str(d.message) + str(getattr(d, "detail", ""))]
    assert exporter.diagnostics.by_code("Q2VT_MASK_APPROXIMATE")
    assert layer.renderer().symbol().symbolLayer(0).layerType() == "MaskMarker"  # project unchanged
    assert [l for l in _style(result)["layers"] if l.get("source-layer") and l["type"] in ("symbol", "circle")]


def test_unsupported_renderer_is_reported(export, tmp_path):  # noqa: F811
    """A renderer QGIS cannot turn into rules (here 2.5D) drew nothing and
    was not in the report."""
    from qgis.core import Qgs25DRenderer  # pylint: disable=import-outside-toplevel
    layer = zoning_layer(path=str(tmp_path / "blocks.gpkg"))
    layer.setRenderer(Qgs25DRenderer())
    exporter, _ = _run(export, layer)
    found = exporter.diagnostics.by_code("Q2VT_UNSUPPORTED_RENDERER")
    assert found and "25dRenderer" in found[0].message and found[0].layer_id == layer.id()


def test_marker_sized_in_meters_at_scale_is_drawn(export, tmp_path):  # noqa: F811
    """A marker sized in "meters at scale" (QGIS Hub military symbols: a
    300 m square with a 40 m outline): the sprite's render context had no
    CRS for distances, QGIS drew it a thousandth of a pixel wide and every
    per-zoom sprite was empty."""
    from qgis.core import QgsFeature, QgsGeometry, QgsVectorLayer  # pylint: disable=import-outside-toplevel
    from q2vt_fixtures import to_geopackage  # pylint: disable=import-outside-toplevel
    layer = QgsVectorLayer("Point?crs=EPSG:3857", "points", "memory")
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromWkt("POINT(2121000 6021000)"))
    layer.dataProvider().addFeatures([feature])
    layer = to_geopackage(layer, str(tmp_path / "points.gpkg"))
    symbol = QgsMarkerSymbol.createSimple({"name": "square", "color": "0,0,0,0", "outline_color": "0,0,0",
                                           "size": "300", "size_unit": "RenderMetersInMapUnits",
                                           "outline_width": "40",
                                           "outline_width_unit": "RenderMetersInMapUnits"})
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    exporter, result = _run(export, layer)
    assert not exporter.diagnostics.by_code("Q2VT_SPRITE_TRANSPARENT")
    assert [l for l in _style(result)["layers"] if l.get("type") == "symbol" and "icon-image" in l.get("layout", {})]


def test_pattern_marker_too_large_for_a_sprite_does_not_stop_the_export(export, tmp_path):  # noqa: F811
    """A random marker fill whose marker is sized in map units and is
    kilometres wide (QGIS Hub "Mondriaan"): too large for a sprite even at
    the lowest zoom. The pattern is reported and left out; the export
    finishes (it stopped with "Sprite 'pattern-marker' would be 51519 px
    wide")."""
    from qgis.core import QgsFillSymbol, QgsRandomMarkerFillSymbolLayer  # pylint: disable=import-outside-toplevel
    layer = zoning_layer(path=str(tmp_path / "zones.gpkg"))
    fill = QgsRandomMarkerFillSymbolLayer(10, Qgis.PointCountMethod.DensityBased, 250000.0)
    fill.setSubSymbol(QgsMarkerSymbol.createSimple({"name": "square", "size": "200000",
                                                    "size_unit": "MapUnit"}))
    layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol([fill])))
    exporter, result = _run(export, layer)
    assert result and os.path.exists(os.path.join(result, "style", "style.json"))
    assert any("RandomMarkerFill left out" in d.message
               for d in exporter.diagnostics.by_code("Q2VT_SPRITE_RENDER_FAILED"))


# --- QGIS 4 selective masking source sets ----------------------------------

needs_sets = pytest.mark.skipif(not hasattr(QgsSymbolLayer, "selectiveMaskingSourceSetId"),
                                reason="selective masking source sets are QGIS 4")


def _source_set(project, *sources):
    """A project source set of (layer id, "Label"/"SymbolLayer", source id);
    returns its id, which a masked symbol layer names."""
    from qgis.core import QgsSelectiveMaskingSourceSet, QgsSelectiveMaskSource  # pylint: disable=import-outside-toplevel
    masking_set = QgsSelectiveMaskingSourceSet()
    masking_set.setName(f"knockouts {len(project.selectiveMaskingSourceSetManager().sets())}")
    masking_set.setSources([QgsSelectiveMaskSource(layer_id, getattr(Qgis.SelectiveMaskSourceType, kind), key)
                            for layer_id, kind, key in sources])
    assert project.selectiveMaskingSourceSetManager().addSet(masking_set)
    return masking_set.id()


def _set_labels(path, rule_based=False):
    """_masked_labels with an empty list: masking its fill is left to a set."""
    from qgis.core import QgsRuleBasedLabeling  # pylint: disable=import-outside-toplevel
    layer = _masked_labels(path)
    settings = QgsPalLayerSettings(layer.labeling().settings())
    fmt = settings.format()
    mask = fmt.mask()
    mask.setMaskedSymbolLayers([])
    fmt.setMask(mask)
    settings.setFormat(fmt)
    if rule_based:
        root = QgsRuleBasedLabeling.Rule(None)
        root.appendChild(QgsRuleBasedLabeling.Rule(QgsPalLayerSettings(settings), 0, 0, "\"zone\" = 'K1'"))
        root.appendChild(QgsRuleBasedLabeling.Rule(QgsPalLayerSettings(settings), 0, 0, "\"zone\" <> 'K1'"))
        layer.setLabeling(QgsRuleBasedLabeling(root))
    else:
        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    return layer


def _signs(path, listed):
    """A point drawn as a square over a mask marker (a 6 mm circle) that
    lists a symbol layer when ``listed``, else masks nothing itself."""
    from qgis.core import QgsFeature, QgsGeometry, QgsVectorLayer  # pylint: disable=import-outside-toplevel
    from q2vt_fixtures import to_geopackage  # pylint: disable=import-outside-toplevel
    layer = QgsVectorLayer("Point?crs=EPSG:3857", "signs", "memory")
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromWkt("POINT(2121000 6021000)"))
    layer.dataProvider().addFeatures([feature])
    if path:
        layer = to_geopackage(layer, path)
    mask = QgsMaskMarkerSymbolLayer()
    mask.setSubSymbol(QgsMarkerSymbol.createSimple({"name": "circle", "color": "255,0,0", "size": "6"}))
    if listed:
        mask.setMasks([QgsSymbolLayerReference(*listed)])
    symbol = QgsMarkerSymbol.createSimple({"name": "square", "color": "0,0,255", "size": "3"})
    symbol.insertSymbolLayer(0, mask)
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    return layer


def _fixed_fill(layer):
    """A dark fill without outline (the same symbol layer: lists name it)."""
    fill = layer.renderer().symbol().symbolLayer(0)
    fill.setColor(QColor(60, 60, 60))
    fill.setStrokeStyle(Qt.PenStyle.NoPen)
    return layer


def _label_halos(result):
    return [str(l["paint"]["text-halo-color"]).replace(" ", "") for l in _style(result)["layers"]
            if "text-field" in l.get("layout", {})]


def _approximate(exporter):
    return sorted(d.message for d in exporter.diagnostics.by_code("Q2VT_MASK_APPROXIMATE"))


@needs_sets
def test_source_set_label_mask_exports_as_the_list(export, tmp_path):  # noqa: F811
    """A label masking through a set (source: its layer, provider "" for
    simple labeling) exports as the label masking with its list."""
    exporter, result = _run(export, _fixed_fill(_masked_labels(str(tmp_path / "zones.gpkg"))))
    listed, listed_notes = _style(result), _approximate(exporter)
    assert listed_notes
    for masked in (False, True):
        layer = _fixed_fill(_set_labels(str(tmp_path / f"set_zones_{masked}.gpkg")))
        project = reset_project(layer)
        project.setBackgroundColor(BACKGROUND)
        if masked:
            set_id = _source_set(project, (layer.id(), "Label", ""))
            layer.renderer().symbol().symbolLayer(0).setSelectiveMaskingSourceSetId(set_id)
        exporter, result = export(layer, keep_project=True)
        if masked:
            assert _style(result) == listed and _approximate(exporter) == listed_notes
            assert not layer.labeling().settings().format().mask().maskedSymbolLayers()  # project unchanged
        else:
            assert not _approximate(exporter)  # an enabled mask masking nothing


@needs_sets
def test_source_set_names_the_labeling_rule(export, tmp_path):  # noqa: F811
    """Rule-based labeling: a label source names one rule by its key; the
    other rule's labels do not mask. A set no symbol layer names masks
    nothing."""
    layer = _set_labels(str(tmp_path / "zones.gpkg"), rule_based=True)
    project = reset_project(layer)
    project.setBackgroundColor(BACKGROUND)
    first, second = layer.labeling().rootRule().children()
    set_id = _source_set(project, (layer.id(), "Label", first.ruleKey()))
    _source_set(project, (layer.id(), "Label", second.ruleKey()))  # named by nothing
    layer.renderer().symbol().symbolLayer(0).setSelectiveMaskingSourceSetId(set_id)
    exporter, result = export(layer, keep_project=True)
    halos = _label_halos(result)
    assert len(halos) == 2 and sum(h.startswith("rgba(250,240,200,0.8") for h in halos) == 1
    assert len(_approximate(exporter)) == 1


@needs_sets
def test_source_set_mask_marker_exports_as_the_list(export, tmp_path):  # noqa: F811
    """A mask marker listing nothing in a layer a set names: QGIS 4 draws
    it in the layer's mask, as one masking with its list. Only when the
    set's symbol layer is drawn (QGIS resolves sets over the rendered
    layers)."""
    zones = _fixed_fill(zoning_layer(path=str(tmp_path / "zones.gpkg")))
    listed = _signs(str(tmp_path / "signs.gpkg"), (zones.id(), zones.renderer().symbol().symbolLayer(0).id()))
    project = reset_project(listed, zones)
    project.setBackgroundColor(BACKGROUND)
    exporter, result = export(listed, keep_project=True)
    as_listed, listed_notes = _style(result), _approximate(exporter)
    assert listed_notes

    for masked, drawn in ((False, True), (True, True), (True, False)):
        zones = _fixed_fill(zoning_layer(path=str(tmp_path / f"set_zones_{masked}_{drawn}.gpkg")))
        signs = _signs(str(tmp_path / f"set_signs_{masked}_{drawn}.gpkg"), None)
        project = reset_project(signs, zones)
        project.setBackgroundColor(BACKGROUND)
        if masked:
            marker = signs.renderer().symbol().symbolLayer(0)
            set_id = _source_set(project, (signs.id(), "SymbolLayer", marker.id()))
            zones.renderer().symbol().symbolLayer(0).setSelectiveMaskingSourceSetId(set_id)
        project.layerTreeRoot().findLayer(zones.id()).setItemVisibilityChecked(drawn)
        exporter, result = export(signs, keep_project=True)
        if masked and drawn:
            assert _style(result) == as_listed and _approximate(exporter) == listed_notes
            assert signs.renderer().symbol().symbolLayer(0).layerType() == "MaskMarker"  # project unchanged
        else:
            assert not _approximate(exporter)


@needs_sets
def test_qgis_masks_through_a_set_as_through_the_list(plugin):
    """What the export assumes, in QGIS 4 itself: a set masks as the
    masker's list does (a label of a set, a mask marker listing nothing in
    a layer of a set)."""
    from qgis.core import (QgsMapRendererSequentialJob, QgsMapSettings,  # pylint: disable=import-outside-toplevel
                           QgsProject)
    from qgis.PyQt.QtCore import QSize  # pylint: disable=import-outside-toplevel

    def render(*layers):
        settings = QgsMapSettings()
        settings.setLayers(list(layers))
        settings.setDestinationCrs(layers[0].crs())
        settings.setExtent(EXTENT)
        settings.setOutputSize(QSize(160, 160))
        settings.setBackgroundColor(BACKGROUND)
        settings.setSelectiveMaskingSourceSets(QgsProject.instance().selectiveMaskingSourceSetManager().sets())
        job = QgsMapRendererSequentialJob(settings)
        job.start()
        job.waitForFinished()
        return job.renderedImage()

    zones = _fixed_fill(_masked_labels(None))
    project = reset_project(zones)
    by_list = render(zones)
    zones = _fixed_fill(_set_labels(None))
    project = reset_project(zones)
    unmasked = render(zones)
    zones.renderer().symbol().symbolLayer(0).setSelectiveMaskingSourceSetId(
        _source_set(project, (zones.id(), "Label", "")))
    assert by_list != unmasked and render(zones) == by_list

    zones = _fixed_fill(zoning_layer())
    signs = _signs(None, (zones.id(), zones.renderer().symbol().symbolLayer(0).id()))
    project = reset_project(signs, zones)
    by_list = render(signs, zones)
    zones = _fixed_fill(zoning_layer())
    signs = _signs(None, None)
    project = reset_project(signs, zones)
    unmasked = render(signs, zones)
    zones.renderer().symbol().symbolLayer(0).setSelectiveMaskingSourceSetId(
        _source_set(project, (signs.id(), "SymbolLayer", signs.renderer().symbol().symbolLayer(0).id())))
    assert by_list != unmasked and render(signs, zones) == by_list

    # A second, larger mask marker listing nothing beside one with a list:
    # QGIS 4 draws it in the layer's mask too.
    zones = _fixed_fill(zoning_layer())
    signs = _signs(None, (zones.id(), zones.renderer().symbol().symbolLayer(0).id()))
    project = reset_project(signs, zones)
    idle = QgsMaskMarkerSymbolLayer()
    idle.setSubSymbol(QgsMarkerSymbol.createSimple({"name": "circle", "size": "12"}))
    signs.renderer().symbol().appendSymbolLayer(idle)
    assert render(signs, zones) != by_list
    from q2vt_plugin.src.core.fidelity import masks  # pylint: disable=import-error,import-outside-toplevel
    assert masks.layer_masks(signs.renderer(), masks.SourceSetMasks(), signs.id())
    assert masks.knock_out_mask_markers(signs.renderer().symbol().clone(), BACKGROUND, True) == 2
