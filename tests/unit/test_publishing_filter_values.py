"""Values filter options are written the way the web map reads the tiles'
values (JavaScript String / MapLibre to-string)."""

from publishing.qgis_model import _js_string


def test_whole_reals_and_booleans_match_the_browser():
    assert _js_string(2.0) == "2" and _js_string(-3.0) == "-3"
    assert _js_string(2.5) == "2.5" and _js_string(7) == "7"
    assert _js_string(True) == "true" and _js_string(False) == "false"
    assert _js_string("Lk-1") == "Lk-1"
