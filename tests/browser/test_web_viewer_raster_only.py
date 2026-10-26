"""A web map of raster layers only (a QGIS-rendered image and a live web
layer, no vector layer, so no vector source): the viewer loads without
errors, draws the image, lists both layers in the layer list and the
legend, switches them off and on, zooms to a layer and prints; there is no
labels switch and no search box (nothing to search)."""

import json
import os
import subprocess

import pytest

from publishing.controller import export_local
from publishing.preview_server import PreviewServer
from publishing.provenance import layer_logical_id

HERE = os.path.dirname(os.path.abspath(__file__))


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
    from test_publishing_raster import EXTENT  # pylint: disable=import-error
    from test_publishing_raster_only import raster_only_project  # pylint: disable=import-error
    base = tmp_path_factory.mktemp("rasteronly")
    project, profile, layers = raster_only_project(base)
    # The viewer's extras, none of which may need a vector layer.
    interaction = profile.interaction
    interaction.overview_map = interaction.measure = interaction.drawing = interaction.three_d = True
    result = export_local(project, profile, EXTENT)
    ids = {name: layer_logical_id(layer.id()) for name, layer in layers.items()}
    # Live layers only: no source in the manifest at all.
    live_project, live_profile, _ = raster_only_project(base / "live", local=False)
    live_profile.slug = "csak-web"
    live_profile.output.local_directory = profile.output.local_directory
    export_local(live_project, live_profile, EXTENT)
    with PreviewServer(os.path.dirname(result.publication_dir)) as server:
        # ?print: the map's drawing buffer is kept, so its pixels can be read.
        yield {"url": server.url(f"{profile.slug}/index.html") + "?print",
               "live": server.url(f"{live_profile.slug}/index.html"),
               "ortho": ids["ortho"], "web": ids["web"]}


# Pixels of the map that are the ortho's (its bands differ; the background is grey or white).
PIXELS = """const pixels = async () => {
  const m = q2vtViewer.map;
  await new Promise((r) => { m.once('idle', r); m.triggerRepaint(); });
  const canvas = m.getCanvas(), copy = document.createElement('canvas');
  copy.width = canvas.width; copy.height = canvas.height;
  const ctx = copy.getContext('2d');
  ctx.drawImage(canvas, 0, 0);
  const data = ctx.getImageData(0, 0, copy.width, copy.height).data;
  let n = 0;
  for (let i = 0; i < data.length; i += 4) if (data[i + 3] && (data[i] !== data[i + 1] || data[i + 1] !== data[i + 2])) n++;
  return n / (data.length / 4);
};"""


def test_raster_only_map_draws_and_lists_its_layers(site, tmp_path):
    ortho, web = site["ortho"], site["web"]
    results = _run(site["url"], [
        {"idle": True},
        {"eval": PIXELS + """const v = q2vtViewer, m = v.map, man = v.manifest;
          const rows = [...document.querySelectorAll('#q2vt-pane-layers .q2vt-layer .q2vt-title')].map((n) => n.textContent);
          document.getElementById('q2vt-tab-legend').click();
          const legend = [...document.querySelectorAll('#q2vt-pane-legend .q2vt-legend-item')].map((li) => ({
            text: li.textContent, icon: !!li.querySelector('svg, img') }));
          return { sources: man.sources.map((s) => s.role), labels: v.labels,
                   style: Object.values(m.getStyle().sources).map((s) => s.type),
                   drawn: await pixels(), rows, legend,
                   labelsSwitch: !!document.querySelector('#q2vt-pane-layers .q2vt-row-labels'),
                   search: getComputedStyle(document.getElementById('q2vt-searchbox')).display,
                   webOn: v.controls.state.value.layers['""" + web + """'] };"""},
        {"eval": PIXELS + """const s = q2vtViewer.controls.state;
          s.setIn('layers', '""" + ortho + """', false);
          const off = await pixels();
          s.setIn('layers', '""" + ortho + """', true);
          return { off, on: await pixels() };"""},
        {"eval": """const m = q2vtViewer.map;
          m.jumpTo({ center: [0, 0], zoom: 3 });
          const button = [...document.querySelectorAll('#q2vt-pane-layers .q2vt-zoom-layer')]
            .find((b) => b.getAttribute('aria-label').includes('Ortofotó'));
          button.click();
          for (let i = 0; i < 60 && m.isMoving(); i++) await new Promise((r) => setTimeout(r, 100));
          const c = m.getCenter();
          return { zoom: m.getZoom(), lng: c.lng, lat: c.lat,
                   buttons: document.querySelectorAll('#q2vt-pane-layers .q2vt-zoom-layer').length };"""},
        {"eval": """window.print = () => { window.__printed = (window.__printed || 0) + 1; };
          await q2vtViewer.printer.print('map');
          const sheet = document.querySelector('.q2vt-legend-print');
          const out = { printed: window.__printed, classes: document.body.className,
                        legend: sheet ? [...sheet.querySelectorAll('.q2vt-legend-item')].map((li) => li.textContent) : null };
          window.dispatchEvent(new Event('afterprint'));
          await new Promise((r) => setTimeout(r, 200));
          out.restored = !document.body.classList.contains('q2vt-printing');
          return out;"""},
    ], tmp_path)
    first, toggled, zoomed, printed = results
    assert first["sources"] == ["raster"] and first["labels"] is None
    assert set(first["style"]) == {"raster"}
    assert first["drawn"] > 0.1, first           # the ortho fills much of the view
    assert sorted(first["rows"]) == ["Ortofotó", "Webes térkép"]
    assert any(item["text"] == "Ortofotó" and item["icon"] for item in first["legend"]), first["legend"]
    assert not first["labelsSwitch"] and first["search"] == "none"
    assert first["webOn"] is False                # initially hidden, as published
    assert toggled["off"] < 0.01 and toggled["on"] > 0.1, toggled
    assert zoomed["buttons"] == 2 and zoomed["zoom"] > 10
    assert 18 < zoomed["lng"] < 20 and 46 < zoomed["lat"] < 48  # the export extent
    assert printed["printed"] == 1 and "q2vt-printing-map" in printed["classes"]
    assert printed["legend"] == ["Ortofotó"] and printed["restored"]


def test_clicks_links_and_extras_need_no_vector_layer(site, tmp_path):
    ortho = site["ortho"]
    results = _run(site["url"], [
        {"eval": """const v = q2vtViewer;
          return { ready: v.ready, errors: v.diagnostics.errors.length,
                   overview: !!document.querySelector('.q2vt-overview'),
                   tools: !!document.getElementById('q2vt-pane-tools'),
                   searchToggle: !!document.querySelector('.q2vt-search-toggle') };"""},
        {"clickLngLat": [19.05, 47.48]}, {"wait": 600},
        {"eval": """const v = q2vtViewer, s = v.controls.state;
          const popups = document.querySelectorAll('.maplibregl-popup').length;
          s.setIn('layers', '""" + ortho + """', false);
          await new Promise((r) => setTimeout(r, 400));
          return { popups, link: v.permalink.links().versioned };"""},
    ], tmp_path)
    first, clicked = results
    assert first == {"ready": True, "errors": 0, "overview": True, "tools": True, "searchToggle": False}
    assert clicked["popups"] == 0
    # The link keeps the ortho switched off.
    reopened = _run(clicked["link"], [
        {"eval": "return q2vtViewer.ready && q2vtViewer.controls.state.value.layers['" + ortho + "'];"},
    ], tmp_path)
    assert reopened == [False]


def test_live_layers_alone_load(site, tmp_path):
    results = _run(site["live"], [
        {"eval": """const v = q2vtViewer, m = v.map;
          return { ready: v.ready, errors: v.diagnostics.errors.length, sources: v.manifest.sources.length,
                   live: m.getStyle().layers.filter((l) => l.type === 'raster').length,
                   rows: [...document.querySelectorAll('#q2vt-pane-layers .q2vt-layer .q2vt-title')].map((n) => n.textContent) };"""},
    ], tmp_path)
    assert results[0] == {"ready": True, "errors": 0, "sources": 0, "live": 1, "rows": ["Webes térkép"]}
