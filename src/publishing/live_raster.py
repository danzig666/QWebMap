"""
QGIS raster layers served by a tile or map server (the ``wms`` provider:
XYZ tiles, WMS) published *live*: the visitor's browser loads their images
from that server while browsing, instead of QGIS rendering them into the
release (``raster_tiles``). A WMS layer also answers a click on the map
(GetFeatureInfo) in the web map.

Only what a browser can load from another site: ``https`` addresses (the
page's Content-Security-Policy, and an https page cannot load http images),
no QGIS login (authentication configurations, user names, referer headers
stay in QGIS), XYZ templates MapLibre understands (``{z}/{x}/{y}``,
``{-y}``, ``{s}``) and WMS servers (images requested in Web Mercator).
WMTS and other services keep being rendered.
"""

from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from ..utils.qt_compat import enum_int
from . import xyz

# Formats a WMS GetFeatureInfo answer may be asked in, best first: features
# as GeoJSON (GeoServer, QGIS Server, MapServer with OGR output), an HTML
# table, plain text.
INFO_JSON, INFO_HTML, INFO_TEXT = "application/json", "text/html", "text/plain"


def _flag(provider, name: str) -> bool:
    """A raster interface capability of ``provider`` (QGIS 3.x and 3.36+ names)."""
    try:
        caps = enum_int(provider.capabilities())
        if caps is None:
            return False
    except Exception:  # pylint: disable=broad-except
        return False
    try:
        from qgis.core import Qgis  # pylint: disable=import-outside-toplevel
        value = getattr(Qgis.RasterInterfaceCapability, name, None)
        if value is not None:
            return bool(caps & (enum_int(value) or 0))
    except (ImportError, AttributeError, TypeError):
        pass
    from qgis.core import QgsRasterInterface  # pylint: disable=import-outside-toplevel
    value = getattr(QgsRasterInterface, name, None)
    return value is not None and bool(caps & (enum_int(value) or 0))


def info_formats(provider) -> List[str]:
    """GetFeatureInfo formats the WMS server answers in (empty: not queryable)."""
    out = []
    if _flag(provider, "IdentifyFeature"):
        out.append(INFO_JSON)
    if _flag(provider, "IdentifyHtml"):
        out.append(INFO_HTML)
    if _flag(provider, "IdentifyText"):
        out.append(INFO_TEXT)
    return out


def _joined(value) -> str:
    if isinstance(value, (list, tuple)):
        return ",".join(str(v) for v in value)
    return str(value or "")


def _int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def describe(uri: Dict[str, object], formats: Optional[List[str]] = None) -> Tuple[Optional[dict], str]:
    """(live source, "") of a decoded ``wms`` provider URI, or (None, why not).

    The source: ``{"kind": "xyz" | "wms", "tiles": [...], "scheme",
    "minzoom", "maxzoom", "format", "wms": {...}}``."""
    if uri.get("authcfg") or uri.get("username") or uri.get("password"):
        return None, "it needs a login"
    if any(str(k).lower().startswith("http-header") or str(k).lower() == "referer" for k in uri):
        return None, "it sends its own HTTP headers"
    url = str(uri.get("url") or "")
    if urlsplit(url).scheme != "https":
        return None, "its address is not https"
    if str(uri.get("type") or "") == "xyz":
        if "{q}" in url or not all(p in url for p in ("{z}", "{x}")) \
                or not ("{y}" in url or "{-y}" in url):
            return None, "its tile address is not a {z}/{x}/{y} template"
        tiles, scheme = xyz.tile_urls(url)
        low, high = _int(uri.get("zmin")), _int(uri.get("zmax"))
        image = "jpg" if ".jpg" in url.lower() or ".jpeg" in url.lower() else "png"
        return {"kind": "xyz", "tiles": tiles, "scheme": scheme,
                "minzoom": max(0, low) if low is not None else 0,
                # (no zmax: QGIS's own default, 18; deeper tiles rarely exist)
                "maxzoom": min(22, high) if high is not None else 18, "format": image}, ""
    if uri.get("tileMatrixSet"):
        return None, "WMTS services are rendered"
    layers = _joined(uri.get("layers"))
    if not layers:
        return None, "no WMS layer is chosen"
    image_format = str(uri.get("format") or "image/png")
    if image_format not in ("image/png", "image/jpeg", "image/png8", "image/webp"):
        image_format = "image/png"
    styles = _joined(uri.get("styles"))
    template = xyz.wms_template(url, layers, image_format, styles)
    return {"kind": "wms", "tiles": [template], "scheme": "xyz", "minzoom": 0, "maxzoom": 22,
            "format": "jpg" if image_format == "image/jpeg" else "png",
            "wms": {"url": service_url(url), "layers": layers, "styles": styles, "version": "1.3.0",
                    "infoFormats": list(formats or []),
                    "legend": legend_url(url, layers.split(",")[0])}}, ""


def service_url(url: str) -> str:
    """The WMS address with its own query parameters (a map= or key), the
    request ones (service, request, version...) dropped."""
    parts = urlsplit(url.strip())
    request = {"service", "version", "request", "layers", "styles", "crs", "srs", "bbox", "width",
               "height", "format", "transparent", "query_layers", "info_format", "i", "j", "x", "y"}
    own = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in request]
    return urlunsplit((parts.scheme, parts.netloc, parts.path,
                       urlencode(own, quote_via=quote, safe=":,"), ""))


def legend_url(url: str, layer: str) -> str:
    """GetLegendGraphic of one WMS layer (the first of the chosen ones)."""
    base = service_url(url)
    query = urlencode([("SERVICE", "WMS"), ("VERSION", "1.3.0"), ("REQUEST", "GetLegendGraphic"),
                       ("FORMAT", "image/png"), ("LAYER", layer), ("SLD_VERSION", "1.1.0")],
                      quote_via=quote, safe=":,")
    return base + ("&" if "?" in base else "?") + query


def live_source(layer) -> Tuple[Optional[dict], str]:
    """(live source, "") of a QGIS raster layer, or (None, why it is rendered)."""
    try:
        if layer.providerType() != "wms":
            return None, "it is not a web tile or WMS layer"
        from qgis.core import QgsProviderRegistry  # pylint: disable=import-outside-toplevel
        uri = dict(QgsProviderRegistry.instance().decodeUri("wms", layer.source()))
    except Exception as error:  # pylint: disable=broad-except
        return None, f"its address could not be read ({error})"
    formats = info_formats(layer.dataProvider()) if layer.dataProvider() is not None else []
    return describe(uri, formats)


def paint(layer) -> Dict[str, float]:
    """MapLibre raster paint of the layer's QGIS rendering settings: opacity,
    saturation (grayscale), contrast and brightness."""
    out: Dict[str, float] = {}
    try:
        renderer = layer.renderer()
        opacity = float(renderer.opacity()) if renderer is not None else 1.0
    except Exception:  # pylint: disable=broad-except
        opacity = 1.0
    out["raster-opacity"] = round(max(0.0, min(1.0, opacity)), 3)
    try:
        hue = layer.hueSaturationFilter()
        grey = bool(int(getattr(hue.grayscaleMode(), "value", hue.grayscaleMode())))
        saturation = -1.0 if grey else max(-1.0, min(1.0, hue.saturation() / 100.0))
        if saturation:
            out["raster-saturation"] = round(saturation, 3)
    except Exception:  # pylint: disable=broad-except
        pass
    try:
        bc = layer.brightnessFilter()
        contrast = max(-1.0, min(1.0, bc.contrast() / 100.0))
        if contrast:
            out["raster-contrast"] = round(contrast, 3)
        brightness = max(-1.0, min(1.0, bc.brightness() / 255.0))
        if brightness > 0:
            out["raster-brightness-min"] = round(brightness, 3)
        elif brightness < 0:
            out["raster-brightness-max"] = round(1 + brightness, 3)
    except Exception:  # pylint: disable=broad-except
        pass
    return out


def sample_tile_url(source: dict, lonlat) -> str:
    """One tile address of ``source`` near ``lonlat`` (the export's middle)."""
    import math  # pylint: disable=import-outside-toplevel
    zoom = max(source.get("minzoom", 0), min(source.get("maxzoom", 22), 12))
    lon, lat = lonlat
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(max(-85.05, min(85.05, lat)))
    y = int((1.0 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    if source.get("scheme") == "tms":
        y = n - 1 - y
    url = source["tiles"][0]
    if xyz.WMS_BBOX in url:
        size = 2 * 20037508.342789244 / n
        west, north = -20037508.342789244 + x * size, 20037508.342789244 - y * size
        return url.replace(xyz.WMS_BBOX, f"{west:.3f},{north - size:.3f},{west + size:.3f},{north:.3f}")
    return url.replace("{z}", str(zoom)).replace("{x}", str(x)).replace("{y}", str(y))


def probe(source: dict, lonlat, origin: str = "https://example.org",
          timeout_ms: int = 8000) -> Tuple[Optional[bool], str]:
    """(usable, why not) of the server's sample tile: an image another
    site's page may use (CORS: WebGL draws only those). None when the server
    could not be asked (no network). A WMS that cannot draw in Web Mercator
    answers with an error (an exception document), not an image."""
    from qgis.core import QgsBlockingNetworkRequest  # pylint: disable=import-outside-toplevel
    from qgis.PyQt.QtCore import QUrl  # pylint: disable=import-outside-toplevel
    from qgis.PyQt.QtNetwork import QNetworkRequest  # pylint: disable=import-outside-toplevel
    request = QNetworkRequest(QUrl(sample_tile_url(source, lonlat)))
    request.setRawHeader(b"Origin", origin.encode("ascii"))
    try:
        request.setTransferTimeout(timeout_ms)
    except AttributeError:
        pass
    blocking = QgsBlockingNetworkRequest()
    error = blocking.get(request, forceRefresh=True)
    reply = blocking.reply()
    status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
    if error != QgsBlockingNetworkRequest.NoError:
        if status is not None and 400 <= int(status) < 600 and source.get("kind") == "wms":
            return False, f"its server answered a test image with HTTP {int(status)}"
        return None, ""  # no answer (offline): kept live
    kind = bytes(reply.rawHeader(b"Content-Type")).decode("latin-1").strip().lower()
    if source.get("kind") == "wms" and kind and not kind.startswith("image/"):
        return False, "its server answered a test image in Web Mercator (EPSG:3857) with an error"
    allowed = bytes(reply.rawHeader(b"Access-Control-Allow-Origin")).decode("latin-1").strip()
    if allowed not in ("*", origin):
        return False, "its server does not let other sites' pages use its images (CORS)"
    return True, ""
