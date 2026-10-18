// Live WMS layers (manifest liveRasters with "wms"): a click on the map asks
// their servers what is there (GetFeatureInfo) when no feature of the map's
// own layers was hit. Answers become DOM text only: GeoJSON properties as a
// table, an HTML answer's table cells (parsed, never inserted as HTML) or
// plain text. A server that does not allow the page to read its answer
// (CORS) gets a link that opens the answer in a new tab.
import { t } from "./i18n.mjs";

const SIZE = 101;                 // the queried image: 101 x 101 px around the click
const MAX_FEATURES = 10;
const MAX_TEXT = 4000;
const TIMEOUT_MS = 8000;

// Web Mercator metres of a [lng, lat].
export function mercator([lng, lat]) {
  const r = 6378137;
  const y = Math.max(-85.0511287798, Math.min(85.0511287798, lat)) * Math.PI / 180;
  return [lng * Math.PI / 180 * r, Math.log(Math.tan(Math.PI / 4 + y / 2)) * r];
}

// The GetFeatureInfo address of a live WMS entry at a map point: a 101 px
// image centred on the click at the map's current scale.
export function featureInfoUrl(wms, lngLat, metresPerPixel, format) {
  const [x, y] = mercator(lngLat);
  const half = (SIZE / 2) * metresPerPixel;
  const url = new URL(wms.url);
  const params = {
    SERVICE: "WMS", VERSION: wms.version || "1.3.0", REQUEST: "GetFeatureInfo",
    LAYERS: wms.layers, QUERY_LAYERS: wms.layers, STYLES: wms.styles || "",
    CRS: "EPSG:3857", BBOX: [x - half, y - half, x + half, y + half].map((v) => v.toFixed(3)).join(","),
    WIDTH: String(SIZE), HEIGHT: String(SIZE), I: String((SIZE - 1) / 2), J: String((SIZE - 1) / 2),
    INFO_FORMAT: format, FEATURE_COUNT: String(MAX_FEATURES), FORMAT: "image/png",
  };
  if (!(wms.version || "1.3.0").startsWith("1.3")) {
    params.SRS = params.CRS; delete params.CRS;
    params.X = params.I; params.Y = params.J; delete params.I; delete params.J;
  }
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
  return url.href;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function table(rows) {
  const out = element("table");
  for (const [key, value] of rows) {
    const row = element("tr");
    row.append(element("th", "", key), element("td", "", value));
    out.append(row);
  }
  return out;
}

const shown = (value) => (value === null || value === undefined ? "" : typeof value === "object"
  ? JSON.stringify(value) : String(value));

// DOM nodes of an answer, or null when it says nothing is there.
export function renderAnswer(text, format) {
  if (format === "application/json") {
    let data;
    try { data = JSON.parse(text); } catch { return null; }
    const features = Array.isArray(data?.features) ? data.features : [];
    if (!features.length) return null;
    const nodes = [];
    for (const feature of features.slice(0, MAX_FEATURES)) {
      const rows = Object.entries(feature.properties || {}).map(([k, v]) => [k, shown(v)]);
      if (feature.id !== undefined && feature.id !== null) nodes.push(element("div", "q2vt-popup-layer", String(feature.id)));
      if (rows.length) nodes.push(table(rows));
    }
    return nodes.length ? nodes : null;
  }
  if (format === "text/html") {
    const doc = new DOMParser().parseFromString(text, "text/html");
    const nodes = [];
    for (const source of doc.querySelectorAll("table")) {
      const rows = [...source.querySelectorAll("tr")].map((tr) => [...tr.children].map((c) => c.textContent.trim()));
      const head = rows.length > 1 && rows[0].length > 2 ? rows.shift() : null;
      if (head) {  // a row per feature: a table of field / value per feature
        for (const values of rows.slice(0, MAX_FEATURES)) {
          nodes.push(table(head.map((name, i) => [name, values[i] ?? ""]).filter(([n]) => n)));
        }
      } else {
        const pairs = rows.filter((r) => r.length >= 2).map((r) => [r[0], r.slice(1).join(" ")]);
        if (pairs.length) nodes.push(table(pairs));
      }
    }
    if (nodes.length) return nodes;
    const body = (doc.body?.textContent || "").replace(/\s+\n/g, "\n").trim();
    return body ? [element("pre", "q2vt-wms-text", body.slice(0, MAX_TEXT))] : null;
  }
  const plain = String(text || "").trim();
  if (!plain || /no features? (were )?found|search returned no results/i.test(plain)) return null;
  return [element("pre", "q2vt-wms-text", plain.slice(0, MAX_TEXT))];
}

async function fetchText(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(url, { signal: controller.signal, credentials: "omit", referrerPolicy: "strict-origin-when-cross-origin" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const type = response.headers.get("content-type") || "";
    if (/xml/i.test(type) && !/html/i.test(type)) {
      const body = await response.text();
      if (/ServiceException/i.test(body)) throw new Error("WMS exception");
      return body;
    }
    return await response.text();
  } finally {
    clearTimeout(timer);
  }
}

export class WmsInfo {
  constructor({ map, manifest, control, state }) {
    Object.assign(this, { map, manifest, control, state });
    const layers = new Map(manifest.layers.map((l) => [l.id, l]));
    this.entries = (manifest.liveRasters || [])
      .filter((r) => r.kind === "wms" && r.wms && (r.wms.infoFormats || []).length)
      .map((r) => ({ ...r, layer: layers.get(r.layerId) }));
  }

  get available() { return this.entries.length > 0; }

  // The visible ones at this zoom (switched on, in their zoom range).
  visible() {
    const zoom = this.map.getZoom();
    const state = this.state.value;
    return this.entries.filter(({ layerId, layer }) => layer && this.control.layerEnabled(layerId, state)
      && (state.opacity[layerId] ?? 1) > 0
      && zoom >= (layer.minZoom ?? 0) && zoom < (layer.maxZoom ?? 99));
  }

  // A popup body for a click at lngLat, or null when no server knows anything there.
  async query(lngLat) {
    const entries = this.visible();
    if (!entries.length) return null;
    const center = this.map.project(lngLat);
    const a = this.map.unproject([center.x - 0.5, center.y]);
    const b = this.map.unproject([center.x + 0.5, center.y]);
    const metresPerPixel = Math.abs(mercator([b.lng, b.lat])[0] - mercator([a.lng, a.lat])[0]);
    const point = [lngLat.lng, lngLat.lat];
    const results = await Promise.all(entries.map((entry) => this.ask(entry, point, metresPerPixel)));
    const box = element("div", "q2vt-popup q2vt-popup-wms");
    let any = false;
    for (const [entry, result] of entries.map((e, i) => [e, results[i]])) {
      if (!result) continue;
      any = true;
      box.append(element("h3", "", entry.layer?.title || entry.wms.layers));
      if (result.nodes) box.append(...result.nodes);
      if (result.link) {
        const link = element("a", "q2vt-chip q2vt-chip-ghost", t("wms.open"));
        link.href = result.link;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        box.append(element("p", "q2vt-note", t("wms.blocked")), link);
      }
    }
    return any ? box : null;
  }

  // {nodes} of the first format the server answers in, {link} when the page
  // may not read its answers, null when it says nothing is there.
  async ask(entry, point, metresPerPixel) {
    const formats = entry.wms.infoFormats;
    let blocked = false;
    for (const format of formats) {
      const url = featureInfoUrl(entry.wms, point, metresPerPixel, format);
      try {
        const nodes = renderAnswer(await fetchText(url), format);
        return nodes ? { nodes } : null;
      } catch (error) {
        blocked = blocked || error instanceof TypeError;  // network / CORS
      }
    }
    if (!blocked) return null;
    const readable = formats.includes("text/html") ? "text/html" : formats[0];
    return { link: featureInfoUrl(entry.wms, point, metresPerPixel, readable) };
  }
}
