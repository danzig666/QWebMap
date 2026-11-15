import pytest

from fidelity import zoom as zm
from fidelity.model import OverzoomPolicy, ZoomInterval


def test_roundtrip():
    for z in [0, 1, 7.5, 16, 22]:
        assert zm.scale_to_zoom(zm.zoom_to_scale(z)) == pytest.approx(z)


def test_fractional_single_zoom_rule_is_nonempty():
    # Scale range strictly between zoom 3 and zoom 4 (regression: legacy
    # integer rounding produced min_zoom 4 > max_zoom 3).
    interval = zm.interval_from_scales(zm.zoom_to_scale(3.2), zm.zoom_to_scale(3.8))
    assert not interval.is_empty
    assert interval.min_zoom == pytest.approx(3.2)
    assert interval.max_zoom == pytest.approx(3.8)
    assert interval.tile_zooms(0, 14) == (3, 3)


def test_breakpoint_semantics_half_open():
    interval = ZoomInterval(5, 10)
    assert interval.contains(5)
    assert interval.contains(9.999)
    assert not interval.contains(10)
    assert not interval.contains(4.999)


def test_integer_breakpoints_tile_range():
    interval = zm.interval_from_scales(zm.zoom_to_scale(5), zm.zoom_to_scale(10))
    assert interval.tile_zooms(0, 22) == (5, 9)


def test_unbounded_interval_and_overzoom_policies():
    interval = zm.interval_from_scales(0, 0)
    assert interval.max_zoom is None
    assert interval.style_bounds(14, OverzoomPolicy.PERSIST) == (0, 24)
    assert interval.style_bounds(14, OverzoomPolicy.STOP) == (0, 15)
    assert interval.tile_zooms(2, 14) == (2, 14)


def test_tile_zoom_helpers_match_interval():
    assert zm.tile_min_zoom(0) == 0
    assert zm.tile_max_zoom(0) == zm.MAX_TILE_ZOOM
    assert zm.tile_min_zoom(zm.zoom_to_scale(3.2)) == 3
    assert zm.tile_max_zoom(zm.zoom_to_scale(3.8)) == 3
    assert zm.tile_max_zoom(zm.zoom_to_scale(10)) == 9


def test_inverted_scales_are_empty():
    interval = zm.interval_from_scales(zm.zoom_to_scale(8), zm.zoom_to_scale(6))
    assert interval.is_empty
    assert interval.tile_zooms(0, 22) is None


def test_viewer_start_zoom_fits_the_export_extent():
    """The viewer opened at the minimum zoom: the whole earth for zoom 0."""
    from fidelity.zoom import fit_zoom
    # ~20 x 15 km (the reporter's project): about zoom 11.6 in a 1280 x 800 window.
    zoom = fit_zoom(19723, 15351, 0, 17)
    assert 11 < zoom < 12.5
    assert fit_zoom(19723, 15351, 13, 17) == 13      # never below the exported zooms
    assert fit_zoom(19723, 15351, 0, 10) == 10       # nor above
    assert fit_zoom(40075016, 40075016, 0, 17) < 1   # the whole world


def test_web_zoom_scales_and_their_whole_number_roundings():
    """The QGIS scales of web zooms (a project's scale list, the shipped
    resources/web_zoom_scales.xml) start and end layers exactly at zooms."""
    import os  # pylint: disable=import-outside-toplevel
    import re  # pylint: disable=import-outside-toplevel
    zm.configure(zm.WEB_MERCATOR_TOP_SCALE)
    scales = zm.zoom_scales()
    assert len(scales) == 23 and scales[0] == 295829355 and scales[22] == 71
    for zoom, scale in enumerate(scales):
        assert zm.interval_from_scales(scale, 0).min_zoom == zoom
        assert zm.interval_from_scales(0, scale).max_zoom == zoom
        assert zm.tile_min_zoom(scale) == zoom
        assert zm.tile_max_zoom(scale) == max(0, zoom - 1)
    assert zm.interval_from_scales(1100, 0).min_zoom != 19       # other scales unchanged
    eov = zm.zoom_scales(zm.WEB_MERCATOR_TOP_SCALE * 0.68)
    assert eov[16] == round(zm.WEB_MERCATOR_TOP_SCALE * 0.68 / 2 ** 16)
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "..", "resources", "web_zoom_scales.xml"), encoding="utf-8") as handle:
        shipped = [int(v) for v in re.findall(r'<scale value="1:(\d+)"/>', handle.read())]
    assert shipped == scales
