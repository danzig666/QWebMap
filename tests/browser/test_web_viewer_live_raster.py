"""Raster layers loaded live from their own server: an XYZ web tile layer
is published as a source the viewer binds to the server's addresses (no
image archive in the release, the page policy allows the server), keeps its
QGIS opacity and the layer list can zoom to each layer when the option is
on. WMS answers to a click (GetFeatureInfo) become a popup: GeoJSON, HTML
tables and text; a server that hides its answers from the page gets a link."""

import json
import os
import subprocess

import pytest
from qgis.core import QgsRasterLayer

from publishing.controller import export_local
from publishing.models import LayerConfig
from publishing.preview_server import PreviewServer
from publishing.provenance import layer_logical_id

HERE = os.path.dirname(os.path.abspath(__file__))
TILES = "https://tiles.example.test/{z}/{x}/{y}.png"


def _run(url, actions, tmp_path, width=1200, height=800):
    path = tmp_path / f"actions_{abs(hash(json.dumps(actions)))}.json"
    path.write_text(json.dumps(actions))
    run = subprocess.run(["node", "interact.mjs", url, str(path), str(width), str(height)],
                         capture_output=True, text=True, cwd=HERE, timeout=300)
    assert run.returncode == 0, run.stderr[-3000:]
    out = json.loads(run.stdout.strip().splitlines()[-1])
    assert not out["pageErrors"], out
    return out["results"]


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "integration"))
    from test_publishing_pipeline import _parcels, _profile  # pylint: disable=import-error
    from test_publishing_raster import EXTENT  # pylint: disable=import-error
    from q2vt_fixtures import reset_project
    base = tmp_path_factory.mktemp("liveviewer")
    project = reset_project()
    parcels = _parcels(str(base / "parcels.gpkg"))
    web = QgsRasterLayer(f"type=xyz&url={TILES}&zmin=0&zmax=19", "Webes ortofotó", "wms")
    assert web.isValid()
    web.renderer().setOpacity(0.6)
    project.addMapLayer(parcels)
    project.addMapLayer(web)
    profile = _profile(parcels, base)
    profile.layers[0].initially_visible = True
    profile.layers.append(LayerConfig(web.id(), raster_max_zoom=15))
    profile.interaction.zoom_to_layer = True
    result = export_local(project, profile, EXTENT)
    with PreviewServer(os.path.dirname(result.publication_dir)) as server:
        yield {"url": server.url(f"{profile.slug}/index.html"), "web": layer_logical_id(web.id()),
               "parcels": layer_logical_id(parcels.id()), "release": result.release.release_dir}


def test_the_web_layer_is_live_not_rendered(site):
    release = site["release"]
    manifest = json.load(open(os.path.join(release, "manifest.json"), encoding="utf-8"))
    assert not [s for s in manifest["sources"] if s.get("role") == "raster"]  # no image archive
    (live,) = manifest["liveRasters"]
    assert live["layerId"] == site["web"] and live["kind"] == "xyz" and live["tiles"] == [TILES]
    layer = next(l for l in manifest["layers"] if l["id"] == site["web"])
    assert layer["live"] == "xyz" and len(layer["bounds"]) == 4
    page = open(os.path.join(release, "index.html"), encoding="utf-8").read()
    assert "https://tiles.example.test" in page  # the page policy lets the browser load its tiles


def test_the_viewer_binds_it_and_zooms_to_layers(site, tmp_path):
    results = _run(site["url"], [
        {"eval": """const v = q2vtViewer, m = v.map, live = v.manifest.liveRasters[0];
          const layer = m.getStyle().layers.find((l) => l.source === live.id);
          const source = m.getStyle().sources[live.id];
          const buttons = document.querySelectorAll('#q2vt-pane-layers .q2vt-zoom-layer');
          m.jumpTo({ center: [0, 0], zoom: 3 });
          buttons[0].click();
          for (let i = 0; i < 60 && m.isMoving(); i++) await new Promise((r) => setTimeout(r, 100));
          const c = m.getCenter();
          return { type: layer.type, opacity: layer.paint['raster-opacity'], tiles: source.tiles,
                   buttons: buttons.length, zoom: m.getZoom(), lng: c.lng, lat: c.lat };"""},
    ], tmp_path)
    r = results[0]
    assert r["type"] == "raster" and r["opacity"] == 0.6 and r["tiles"] == [TILES]
    assert r["buttons"] == 2                         # parcels and the web layer
    assert r["zoom"] > 10 and 18 < r["lng"] < 20 and 46 < r["lat"] < 48  # the export extent


def test_wms_feature_info(site, tmp_path):
    results = _run(site["url"], [
        {"eval": """const v = q2vtViewer;
          const { WmsInfo, featureInfoUrl, renderAnswer } = await import(new URL('assets/wms_info.mjs', v.releaseUrl).href);
          const wms = { url: 'https://wms.example.test/ows?map=zones', layers: 'zones', styles: '', version: '1.3.0',
                        infoFormats: ['application/json', 'text/html'] };
          const url = new URL(featureInfoUrl(wms, [19.04, 47.5], 2, 'text/html'));
          const p = Object.fromEntries(url.searchParams);
          const text = (nodes) => nodes && nodes.map((n) => n.textContent).join('|');
          const json = text(renderAnswer(JSON.stringify({ type: 'FeatureCollection', features: [
            { id: 'zones.7', properties: { code: 'Lk-1', height: 7.5 } }] }), 'application/json'));
          const html = text(renderAnswer('<html><body><table><tr><th>code</th><th>use</th><th>height</th></tr>'
            + '<tr><td>Lk-1</td><td>housing</td><td>7.5</td></tr></table><script>alert(1)</script></body></html>', 'text/html'));
          const empty = renderAnswer('{"type":"FeatureCollection","features":[]}', 'application/json');
          const none = renderAnswer('no features were found', 'text/plain');
          // A live WMS layer of the map, its server answering through a stubbed fetch.
          const manifest = { ...v.manifest, liveRasters: [{ id: 'q2vt_raster_w', layerId: '""" + site["parcels"] + """',
            kind: 'wms', wms }] };
          const info = new WmsInfo({ map: v.map, manifest, control: v.controls.control, state: v.controls.state });
          const realFetch = window.fetch;
          window.fetch = async (u) => new Response(JSON.stringify({ features: [{ properties: { code: 'Lk-2' } }] }),
            { headers: { 'content-type': 'application/json' } });
          const box = await info.query({ lng: 19.04, lat: 47.5 });
          window.fetch = async () => { throw new TypeError('Failed to fetch'); };
          const blocked = await info.query({ lng: 19.04, lat: 47.5 });
          window.fetch = realFetch;
          return { p, json, html, empty, none, popup: box && box.textContent,
                   link: blocked && blocked.querySelector('a').href, scripts: box && box.querySelectorAll('script').length };"""},
    ], tmp_path)
    r = results[0]
    p = r["p"]
    assert p["REQUEST"] == "GetFeatureInfo" and p["QUERY_LAYERS"] == "zones" and p["map"] == "zones"
    assert p["CRS"] == "EPSG:3857" and p["I"] == "50" and p["J"] == "50" and p["INFO_FORMAT"] == "text/html"
    west, south, east, north = (float(x) for x in p["BBOX"].split(","))
    assert round(east - west) == 202 and round(north - south) == 202  # 101 px at 2 m
    assert r["json"] == "zones.7|codeLk-1height7.5"
    assert r["html"] == "codeLk-1usehousingheight7.5"  # cells as text, the script dropped
    assert r["empty"] is None and r["none"] is None
    assert "Lk-2" in r["popup"] and r["scripts"] == 0
    assert r["link"].startswith("https://wms.example.test/ows?map=zones&") and "INFO_FORMAT=text%2Fhtml" in r["link"]
