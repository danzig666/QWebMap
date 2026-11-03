// Debug readout (?debug in the map's address): the map's zoom and the zoom
// of the vector tiles drawn at it, for checking zoom limits and styles
// against QGIS. ?debug=tiles also draws the tile boundaries. Not a secret,
// just not shown to visitors who did not ask for it.

export function debugMode(search = location.search) {
  const params = new URLSearchParams(search);
  if (!params.has("debug")) return null;
  return { tiles: params.get("debug") === "tiles" };
}

// The tile zoom MapLibre requests for a vector source at a map zoom: 512 px
// tiles at the zoom, 256 px tiles one zoom up (MapLibre's own rounding),
// within the source's zoom range; past its maxzoom the last tiles are
// magnified ("overzoomed").
export function tileZoom(zoom, source = {}) {
  const size = source.tileSize || 512;
  const z = Math.floor(zoom + Math.log2(512 / size) + 1e-9);
  const max = source.maxzoom ?? 22;
  return { z: Math.max(source.minzoom ?? 0, Math.min(max, z)), overzoomed: z > max };
}

export function installDebug(map, mode, sourceId = "q2vt_tiles") {
  const box = document.createElement("div");
  box.id = "q2vt-debug";
  box.setAttribute("aria-live", "off");
  document.body.append(box);
  const update = () => {
    // The loaded source: its zoom range comes from the archive's header.
    const loaded = map.getSource(sourceId) || {};
    const source = { tileSize: loaded.tileSize, minzoom: loaded.minzoom, maxzoom: loaded.maxzoom };
    const zoom = map.getZoom();
    const tiles = tileZoom(zoom, source);
    box.textContent = `zoom ${zoom.toFixed(2)} · tiles z${tiles.z}${tiles.overzoomed ? " (overzoomed)" : ""}`;
  };
  map.on("zoom", update);
  map.on("moveend", update);
  update();
  if (mode && mode.tiles) map.showTileBoundaries = true;
  return box;
}
