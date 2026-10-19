"""QGIS-vs-browser parity of the QGIS 4 label placement modes: text lines
split over the parts of a feature, characters at the vertices of a line,
spacing stretched so a curved label fills its line. Skipped on QGIS 3."""

import os
import sys

import pytest
from qgis.core import (Qgis, QgsFeature, QgsFillSymbol, QgsGeometry, QgsLineSymbol,
                       QgsPalLayerSettings, QgsSingleSymbolRenderer, QgsTextFormat,
                       QgsVectorLayer, QgsVectorLayerSimpleLabeling)
from qgis.PyQt.QtGui import QColor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_browser_parity import CENTER, _black_box, _compare  # noqa: E402 pylint: disable=wrong-import-position

pytestmark = [pytest.mark.browser,
              pytest.mark.skipif(not hasattr(Qgis, "MultiPartLabelingBehavior"),
                                 reason="QGIS 4 label placement modes")]


def _layer(tmp_path, kind, rows, fill="230,230,230"):
    from q2vt_fixtures import to_geopackage
    memory = QgsVectorLayer(f"{kind}?crs=EPSG:3857&field=t:string", "src", "memory")
    for wkt, text in rows:
        feature = QgsFeature(memory.fields())
        feature.setAttributes([text])
        feature.setGeometry(QgsGeometry.fromWkt(wkt))
        memory.dataProvider().addFeature(feature)
    layer = to_geopackage(memory, str(tmp_path / "src.gpkg"))
    symbol = QgsFillSymbol.createSimple({"color": fill, "outline_style": "no"}) if "Polygon" in kind \
        else QgsLineSymbol.createSimple({"color": fill, "width": "0.3"})
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    return layer


def _label(layer, placement, size=14, multipart=None, curved=None, wrap=""):
    settings = QgsPalLayerSettings()
    settings.fieldName = "t"
    settings.placement = placement
    settings.wrapChar = wrap
    fmt = QgsTextFormat()
    fmt.setSize(size)
    fmt.setSizeUnit(Qgis.RenderUnit.Pixels)
    fmt.setColor(QColor("black"))
    settings.setFormat(fmt)
    if multipart:
        placement_settings = settings.placementSettings()
        placement_settings.setMultiPartBehavior(getattr(Qgis.MultiPartLabelingBehavior, multipart))
        settings.setPlacementSettings(placement_settings)
    if curved:
        line_settings = settings.lineSettings()
        line_settings.setCurvedLabelMode(getattr(Qgis.CurvedLabelMode, curved))
        settings.setLineSettings(line_settings)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)
    return layer


def _square(x, y, half):
    x, y = CENTER[0] + x, CENTER[1] + y
    return f"(({x - half} {y - half}, {x + half} {y - half}, {x + half} {y + half}, " \
           f"{x - half} {y + half}, {x - half} {y - half}))"


def _line(points):
    return "LINESTRING(" + ", ".join(f"{CENTER[0] + x} {CENTER[1] + y}" for x, y in points) + ")"


@pytest.mark.parametrize("placement", ["OverPoint", "Horizontal"])
def test_split_lines_are_drawn_one_per_part(tmp_path, placement):
    """"Split label text lines over parts": each part shows its own line,
    where QGIS draws it; the third part (no third line) has no label."""
    wkt = f"MULTIPOLYGON({_square(-90, 60, 40)}, {_square(70, -70, 45)}, {_square(80, 90, 30)})"
    layer = _label(_layer(tmp_path, "MultiPolygon", [(wkt, "WEST|EAST")]),
                   getattr(Qgis.LabelPlacement, placement), multipart="SplitLabelTextLinesOverParts",
                   wrap="|")
    near = _compare(tmp_path, layer)
    ink_qgis, ink_browser = _compare_ink(tmp_path)
    assert ink_qgis > 50 and ink_browser == pytest.approx(ink_qgis, rel=0.35)
    assert near > 0.8, near
    for name in ("qgis", "browser"):  # a line in each of the first two parts, none in the third
        west, east, third = (_dark_near(tmp_path, name, x, y) for x, y in ((-90, 60), (70, -70), (80, 90)))
        assert west > 20 and east > 20 and third == 0, (name, west, east, third)


def _dark_near(tmp_path, name, x, y, reach=30):
    """Dark pixels of a capture within ``reach`` px of the map point (x, y)
    (metres from CENTER, the view at test_browser_parity.ZOOM)."""
    from PIL import Image
    from test_browser_parity import SIZE, ZOOM, gallery
    per_px = gallery.EARTH / (512 * 2 ** ZOOM)
    cx, cy = SIZE / 2 + x / per_px, SIZE / 2 - y / per_px
    image = Image.open(str(tmp_path / f"v_{name}.png")).convert("L")
    box = image.crop((int(cx - reach), int(cy - reach), int(cx + reach), int(cy + reach)))
    return sum(1 for v in box.getdata() if v < 128)


def _compare_ink(tmp_path):
    from PIL import Image
    return tuple(sum(1 for v in Image.open(str(tmp_path / f"v_{name}.png")).convert("L").getdata() if v < 128)
                 for name in ("qgis", "browser"))


def test_split_lines_of_curved_line_labels(tmp_path):
    """Curved labels may have several lines when they are split over the
    parts: each part of the line gets its own line of text."""
    wkt = "MULTILINESTRING(" + _line([(-140, 60), (-20, 80), (120, 60)])[len("LINESTRING"):] + ", " \
        + _line([(-130, -70), (0, -90), (130, -70)])[len("LINESTRING"):] + ")"
    layer = _label(_layer(tmp_path, "MultiLineString", [(wkt, "Upper reach|Lower reach")]),
                   Qgis.LabelPlacement.Curved, multipart="SplitLabelTextLinesOverParts", wrap="|")
    near = _compare(tmp_path, layer)
    ink_qgis, ink_browser = _compare_ink(tmp_path)
    assert ink_qgis > 100 and ink_browser == pytest.approx(ink_qgis, rel=0.35)
    assert near > 0.8, near


@pytest.mark.parametrize("distance", [0, 3])
def test_characters_at_vertices_sit_where_qgis_draws_them(tmp_path, distance):
    """"Place characters at vertices": one character on each vertex, turned
    along the segment from it (the last vertex: the segment before it),
    the label distance to the left of the line."""
    points = [(-140, -40), (-90, -40), (-40, 0), (10, 40), (60, 40), (110, 0)]
    layer = _label(_layer(tmp_path, "LineString", [(_line(points), "QGIS 4!")]),
                   Qgis.LabelPlacement.Curved, size=20, curved="PlaceCharactersAtVertices")
    if distance:
        settings = layer.labeling().settings()
        settings.dist = distance
        settings.distUnits = Qgis.RenderUnit.Millimeters
        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    near = _compare(tmp_path, layer)
    ink_qgis, ink_browser = _compare_ink(tmp_path)
    assert ink_qgis > 100 and ink_browser == pytest.approx(ink_qgis, rel=0.3)
    assert near > 0.85, near


@pytest.mark.parametrize("mode,text", [("StretchCharacterSpacingToFitLine", "Mill Road"),
                                       ("StretchWordSpacingToFitLine", "Old Mill Road")])
def test_stretched_curved_labels_fill_their_line(tmp_path, mode, text):
    """Stretched spacing: the label runs from one end of its line to the
    other (QGIS FeaturePart::createDefaultCurvedCandidatesAlongLine)."""
    points = [(-130, -10), (-40, 10), (40, -10), (130, 10)]
    layer = _label(_layer(tmp_path, "LineString", [(_line(points), text)], fill="255,255,255"),
                   Qgis.LabelPlacement.Curved, size=14, curved=mode)
    _compare(tmp_path, layer, metric="shape")
    (qleft, _, qright, _), (bleft, _, bright, _) = (_black_box(tmp_path, n) for n in ("qgis", "browser"))
    assert qright - qleft > 200  # QGIS stretches it over the ~300 px line
    assert abs(bleft - qleft) <= 12 and abs(bright - qright) <= 12, ((qleft, qright), (bleft, bright))


@pytest.mark.parametrize("size", [1400, 2000])
def test_long_stretched_labels_are_drawn_whole(tmp_path, monkeypatch, size):
    """A stretched label longer than MapLibre lays out on one tile (its line
    clipped to the tile and the source's buffer: about a thousand pixels)
    is laid out by the viewer character by character: drawn whole, from one
    end of its visible line to the other, where QGIS draws it."""
    import test_browser_parity as tbp  # pylint: disable=import-outside-toplevel
    monkeypatch.setattr(tbp, "SIZE", size)
    half = size * 0.4
    points = [(-half, -10), (0, 10), (half, -10)]
    layer = _label(_layer(tmp_path, "LineString", [(_line(points), "Mill Road")], fill="255,255,255"),
                   Qgis.LabelPlacement.Curved, size=14, curved="StretchCharacterSpacingToFitLine")
    _compare(tmp_path, layer, metric="shape")
    (qleft, _, qright, _), browser = (_black_box(tmp_path, n) for n in ("qgis", "browser"))
    assert qright - qleft > size * 0.8
    assert browser, "no label drawn"
    bleft, _, bright, _ = browser
    assert abs(bleft - qleft) <= 12 and abs(bright - qright) <= 12, ((qleft, qright), (bleft, bright))
    ink_qgis, ink_browser = _compare_ink(tmp_path)
    assert ink_browser == pytest.approx(ink_qgis, rel=0.3), (ink_qgis, ink_browser)


def test_one_word_in_word_stretch_mode_is_a_plain_curved_label(tmp_path):
    """Word spacing cannot stretch one word: QGIS places it as a plain
    curved label (FeaturePart::createDefaultCurvedCandidatesAlongLine),
    here laid out character by character like the stretched ones."""
    points = [(-130, -10), (-40, 10), (40, -10), (130, 10)]
    layer = _label(_layer(tmp_path, "LineString", [(_line(points), "Millroad")], fill="255,255,255"),
                   Qgis.LabelPlacement.Curved, size=14, curved="StretchWordSpacingToFitLine")
    near = _compare(tmp_path, layer)
    ink_qgis, ink_browser = _compare_ink(tmp_path)
    assert ink_qgis > 50 and ink_browser == pytest.approx(ink_qgis, rel=0.3), (ink_qgis, ink_browser)
    assert near > 0.8, near
    (qleft, _, qright, _), (bleft, _, bright, _) = (_black_box(tmp_path, n) for n in ("qgis", "browser"))
    assert qright - qleft < 120  # not stretched
    assert abs(bleft - qleft) <= 8 and abs(bright - qright) <= 8, ((qleft, qright), (bleft, bright))


def test_stretched_label_follows_a_winding_line(tmp_path):
    """Each character of a stretched label sits on its own chord of a
    winding line, turned to it (QgsTextRendererUtils::
    generateCurvedTextPlacement), not on the label's box turned at its
    middle."""
    points = [(-140, -40), (-90, 40), (-40, -40), (10, 40), (60, -40), (110, 40), (140, 0)]
    layer = _label(_layer(tmp_path, "LineString", [(_line(points), "Winding Lane")], fill="255,255,255"),
                   Qgis.LabelPlacement.Curved, size=14, curved="StretchCharacterSpacingToFitLine")
    near = _compare(tmp_path, layer)
    ink_qgis, ink_browser = _compare_ink(tmp_path)
    assert ink_qgis > 100 and ink_browser == pytest.approx(ink_qgis, rel=0.3), (ink_qgis, ink_browser)
    assert near > 0.8, near
