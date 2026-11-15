"""Label backgrounds drawn with their whole fill symbol, and wide text
buffers drawn as the rounded box QGIS's wide buffer becomes (a MapLibre halo
wider than about 1/4 em fills each glyph's box)."""

import pytest
from qgis.core import (Qgis, QgsFillSymbol, QgsPalLayerSettings, QgsProperty, QgsRenderContext,
                       QgsSimpleLineSymbolLayer, QgsTextBackgroundSettings, QgsTextBufferSettings,
                       QgsTextFormat, QgsTextRenderer)
from qgis.PyQt.QtCore import QPointF, QSizeF
from qgis.PyQt.QtGui import QColor, QFont, QImage, QPainter

from fidelity.diagnostics import DiagnosticCollector


@pytest.fixture
def mc(plugin):
    from q2vt_plugin.src.core import maplibre_converter as module  # pylint: disable=import-error
    module.PropertyExtractor.context = module.ConversionContext(DiagnosticCollector())
    module.PropertyExtractor.context.reference_zoom = 0.0
    return module


def _exporter(mc):
    exporter = mc.QgisMapLibreStyleExporter.__new__(mc.QgisMapLibreStyleExporter)
    exporter.pattern_images, exporter.marker_counter, exporter.maxzoom = {}, 0, 16
    exporter.profile = mc.ExportProfile()
    exporter.context = mc.PropertyExtractor.context
    return exporter


def _rectangle(symbol=None):
    frame = QgsTextBackgroundSettings()
    frame.setEnabled(True)
    frame.setType(QgsTextBackgroundSettings.ShapeType.ShapeRectangle)
    frame.setSizeType(QgsTextBackgroundSettings.SizeType.SizeBuffer)
    frame.setSize(QSizeF(1, 1))
    frame.setSizeUnit(Qgis.RenderUnit.Millimeters)
    if symbol is not None:
        frame.setFillSymbol(symbol)
    return frame


def _colours(image):
    return {image.getpixel((x, y))[:3] for x in range(image.width) for y in range(image.height)
            if image.getpixel((x, y))[3] > 200}


def test_a_background_is_drawn_with_all_layers_of_its_fill_symbol(mc):
    """Black fill, white outline and a second, red outline layer: the red
    outline was lost (only fillColor() and strokeColor() were drawn)."""
    exporter = _exporter(mc)
    symbol = QgsFillSymbol.createSimple({"color": "0,0,0,255", "outline_color": "255,255,255,255",
                                         "outline_width": "0.5"})
    symbol.appendSymbolLayer(QgsSimpleLineSymbolLayer(QColor(255, 0, 0), 0.6))
    name = exporter._background_image(_rectangle(symbol))  # pylint: disable=protected-access
    images = exporter.pattern_images[name]
    for image in (images.img_1x, images.img_2x):
        reds = [c for c in _colours(image) if c[0] > 200 and c[1] < 80 and c[2] < 80]
        assert reds, "the second layer's red outline is drawn"
        assert (0, 0, 0) in _colours(image)                   # the fill
    # The image and its stretch zones are those of the plain frame.
    plain = exporter._background_image(_rectangle(QgsFillSymbol.createSimple(  # pylint: disable=protected-access
        {"color": "0,0,0,255", "outline_color": "255,255,255,255", "outline_width": "0.5"})))
    assert exporter.pattern_images[plain].img_1x.size == images.img_1x.size
    assert exporter.pattern_images[plain].metadata == images.metadata


def test_a_plain_fill_background_keeps_its_exact_frame(mc):
    """One simple fill layer: drawn from its colours as before (no QGIS render)."""
    exporter = _exporter(mc)
    frame = _rectangle(QgsFillSymbol.createSimple({"color": "0,0,255,255", "outline_color": "255,0,0,255",
                                                   "outline_width": "0.3"}))
    assert exporter._background_fill_symbol(frame, 1.0) is None  # pylint: disable=protected-access
    frame.fillSymbol().appendSymbolLayer(QgsSimpleLineSymbolLayer(QColor(0, 255, 0), 0.3))
    assert exporter._background_fill_symbol(frame, 1.0) is not None  # pylint: disable=protected-access


def _label(text_size=10.0, buffer_mm=2.0, unit=Qgis.RenderUnit.Millimeters):
    settings = QgsPalLayerSettings()
    text_format = QgsTextFormat()
    text_format.setSize(text_size)
    text_format.setSizeUnit(Qgis.RenderUnit.Points)
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(buffer_mm)
    buffer.setSizeUnit(unit)
    buffer.setColor(QColor(255, 255, 0))
    buffer.setOpacity(0.8)
    text_format.setBuffer(buffer)
    settings.setFormat(text_format)
    return settings


def test_a_wide_buffer_becomes_a_rounded_box_behind_the_text(mc):
    exporter = _exporter(mc)
    settings = _label()                                       # 2 mm on 10 pt: reach 0.29 em
    frame = exporter._wide_buffer_background(settings.format(), settings, {})  # pylint: disable=protected-access
    assert frame is not None and frame.enabled()
    em = 10.0 * 25.4 / 72                                     # 10 pt in mm
    assert frame.size().width() == pytest.approx(1.0)        # half the buffer: its reach
    assert frame.size().height() == pytest.approx(1.0 - 0.225 * em)
    assert frame.radii().width() == pytest.approx(1.0)
    assert frame.offset().y() == pytest.approx(-0.175 * em)
    assert frame.fillColor() == QColor(255, 255, 0) and frame.opacity() == pytest.approx(0.8)
    # Fitted to the text like a "buffer" background, the halo off.
    layer_def = {"id": "l", "minzoom": 0, "maxzoom": 24, "layout": {"text-size": 13.3, "text-line-height": 1.2},
                 "paint": {}}
    exporter._apply_icon_from_background(layer_def, frame, "s", settings)  # pylint: disable=protected-access
    assert layer_def["layout"]["icon-text-fit"] == "both"
    assert layer_def["layout"]["icon-image"].startswith("frame_")


@pytest.mark.parametrize("change", ["narrow", "background", "data-defined", "line", "shadow", "percent"])
def test_buffers_a_halo_draws_stay_halos(mc, change):
    exporter = _exporter(mc)
    settings, layout = _label(), {}
    if change == "narrow":
        settings = _label(buffer_mm=1.0)                      # reach 0.14 em
    elif change == "background":
        text_format = settings.format()
        text_format.setBackground(_rectangle())
        settings.setFormat(text_format)
    elif change == "data-defined":
        settings.dataDefinedProperties().setProperty(QgsPalLayerSettings.Property.BufferSize,
                                                     QgsProperty.fromExpression('"w"'))
    elif change == "line":
        layout = {"symbol-placement": "line"}
    elif change == "shadow":
        text_format = settings.format()
        shadow = text_format.shadow()
        shadow.setEnabled(True)
        text_format.setShadow(shadow)
        settings.setFormat(text_format)
    elif change == "percent":
        settings = _label(buffer_mm=30, unit=Qgis.RenderUnit.Percentage)  # reach 0.15 em
    assert exporter._wide_buffer_background(settings.format(), settings, layout) is None  # pylint: disable=protected-access
    if change == "percent":
        wide = _label(buffer_mm=60, unit=Qgis.RenderUnit.Percentage)      # reach 0.3 em
        assert exporter._wide_buffer_background(wide.format(), wide, {}) is not None  # pylint: disable=protected-access


def _red_box(text, size_pt, fmt_extra):
    image = QImage(500, 260, QImage.Format.Format_ARGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    context = QgsRenderContext.fromQPainter(painter)
    context.setScaleFactor(96 / 25.4)
    text_format = QgsTextFormat()
    text_format.setFont(QFont("Noto Sans"))
    text_format.setSize(size_pt)
    text_format.setColor(QColor("black"))
    fmt_extra(text_format)
    QgsTextRenderer.drawText(QPointF(120, 160), 0, Qgis.TextHorizontalAlignment.Left, [text], context, text_format)
    painter.end()
    xs, ys = [], []
    for y in range(image.height()):
        for x in range(image.width()):
            colour = QColor(image.pixel(x, y))
            if colour.red() > 200 and colour.green() < 120:
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


@pytest.mark.parametrize("text, size_pt, buffer_mm", [("Budapest", 10, 2.0), ("Hálás", 12, 3.0),
                                                      ("Gyöngyös", 9, 2.5)])
def test_the_box_covers_what_the_qgis_buffer_covers(mc, text, size_pt, buffer_mm):
    """QGIS draws the wide buffer and the box made of it about the same
    size and place (within 3 px each side)."""
    exporter = _exporter(mc)
    settings = _label(size_pt, buffer_mm)
    frame = exporter._wide_buffer_background(settings.format(), settings, {})  # pylint: disable=protected-access
    frame.setFillColor(QColor(255, 0, 0))
    frame.setOpacity(1.0)

    def buffer(text_format):
        settings_buffer = QgsTextBufferSettings()
        settings_buffer.setEnabled(True)
        settings_buffer.setSize(buffer_mm)
        settings_buffer.setColor(QColor(255, 0, 0))
        text_format.setBuffer(settings_buffer)

    def box(text_format):
        text_format.setBackground(frame)
    expected, drawn = _red_box(text, size_pt, buffer), _red_box(text, size_pt, box)
    assert all(abs(a - b) <= 3 for a, b in zip(expected, drawn)), (expected, drawn)
