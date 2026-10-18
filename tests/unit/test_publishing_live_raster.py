"""Raster layers loaded live from their own server (publishing.live_raster):
which QGIS web tile / WMS layers can be (https, no login, templates
MapLibre understands), their tile and GetFeatureInfo addresses."""

from urllib.parse import parse_qs, urlsplit

from publishing import live_raster


def test_an_https_xyz_layer_is_loaded_live_with_its_zoom_range():
    source, why = live_raster.describe({"type": "xyz", "url": "https://tiles.example.org/{z}/{x}/{y}.png",
                                        "zmin": "3", "zmax": "19"})
    assert why == "" and source["kind"] == "xyz"
    assert source["tiles"] == ["https://tiles.example.org/{z}/{x}/{y}.png"]
    assert (source["minzoom"], source["maxzoom"], source["scheme"]) == (3, 19, "xyz")
    tms, _ = live_raster.describe({"type": "xyz", "url": "https://{s}.t.example.org/{z}/{x}/{-y}.jpg"})
    assert tms["scheme"] == "tms" and len(tms["tiles"]) == 3 and tms["format"] == "jpg"


def test_layers_a_browser_cannot_load_are_rendered():
    cases = [
        ({"type": "xyz", "url": "http://tiles.example.org/{z}/{x}/{y}.png"}, "https"),
        ({"type": "xyz", "url": "https://t.example.org/{z}/{x}/{y}.png", "authcfg": "abc123"}, "login"),
        ({"type": "xyz", "url": "https://t.example.org/{z}/{x}/{y}.png", "username": "u"}, "login"),
        ({"type": "xyz", "url": "https://t.example.org/{z}/{x}/{y}.png", "http-header:referer": "x"}, "headers"),
        ({"type": "xyz", "url": "https://t.example.org/q/{q}.png"}, "template"),
        ({"url": "https://wmts.example.org/wmts", "tileMatrixSet": "EPSG:3857", "layers": "a"}, "WMTS"),
        ({"url": "https://wms.example.org/ows"}, "layer"),
    ]
    for uri, reason in cases:
        source, why = live_raster.describe(uri)
        assert source is None and reason in why, (uri, why)


def test_a_wms_layer_gets_getmap_tiles_getfeatureinfo_and_a_legend():
    source, _ = live_raster.describe(
        {"url": "https://wms.example.org/ows?map=/srv/zones.map&SERVICE=WMS&REQUEST=GetCapabilities",
         "layers": ["zones", "roads"], "styles": ["", ""], "format": "image/png", "crs": "EPSG:23700"},
        [live_raster.INFO_JSON, live_raster.INFO_HTML])
    assert source["kind"] == "wms"
    tile = urlsplit(source["tiles"][0])
    query = parse_qs(tile.query)
    assert query["REQUEST"] == ["GetMap"] and query["LAYERS"] == ["zones,roads"]
    assert query["CRS"] == ["EPSG:3857"] and source["tiles"][0].endswith("&BBOX={bbox-epsg-3857}")
    wms = source["wms"]
    # The service's own parameters stay, the request ones go.
    assert wms["url"] == "https://wms.example.org/ows?map=%2Fsrv%2Fzones.map" or \
        parse_qs(urlsplit(wms["url"]).query) == {"map": ["/srv/zones.map"]}
    assert wms["infoFormats"] == ["application/json", "text/html"] and wms["layers"] == "zones,roads"
    legend = parse_qs(urlsplit(wms["legend"]).query)
    assert legend["REQUEST"] == ["GetLegendGraphic"] and legend["LAYER"] == ["zones"]


def test_a_sample_tile_for_the_cors_check_is_inside_the_export():
    source, _ = live_raster.describe({"type": "xyz", "url": "https://t.example.org/{z}/{x}/{y}.png"})
    url = live_raster.sample_tile_url(source, (19.04, 47.5))
    assert url == "https://t.example.org/12/2264/1432.png"
    wms, _ = live_raster.describe({"url": "https://wms.example.org/ows", "layers": "a"})
    bbox = parse_qs(urlsplit(live_raster.sample_tile_url(wms, (19.04, 47.5))).query)["BBOX"][0]
    west, south, east, north = (float(v) for v in bbox.split(","))
    assert west < 2119500 < east and south < 6026000 < north
