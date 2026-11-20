// One shard of an index (search, feature lookup, parcel report): its own
// JSON file, or a gzip member of the index's pack file (shard_pack.py) read
// with one HTTP range request, as the map's PMTiles tiles are. A server that
// ignores Range sends the whole pack: it is kept and sliced.

const wholePacks = new Map(); // pack URL -> Promise<Uint8Array>
const ranged = new Set(); // pack URLs a range request was answered (206)
const probes = new Map(); // pack URL -> the first request's answer awaited

// A shard's identity (the shards of a pack share its path).
export function shardId(shard) {
  return shard.offset === undefined || shard.offset === null ? shard.path : `${shard.path}#${shard.offset}`;
}

async function packBytes(url, shard) {
  const start = shard.offset;
  const end = shard.offset + shard.length - 1;
  const href = url.href;
  // While the first request for a pack is out, the others wait for its
  // answer: a server that ignores Range sent each of them (a search loads
  // up to 24 shards at once) the whole pack.
  if (probes.has(href)) await probes.get(href);
  if (!wholePacks.has(href)) {
    const first = !ranged.has(href) && !probes.has(href);
    let answered = () => {};
    if (first) {
      const known = new Promise((resolve) => { answered = resolve; });
      probes.set(href, known);
      known.then(() => { if (probes.get(href) === known) probes.delete(href); });
    }
    try {
      const response = await fetch(url, { headers: { Range: `bytes=${start}-${end}` } });
      if (response.status === 206) {
        ranged.add(href);
        answered();
        return new Uint8Array(await response.arrayBuffer());
      }
      if (!response.ok) throw new Error(`${shard.path}: HTTP ${response.status}`);
      const loading = response.arrayBuffer().then((buffer) => new Uint8Array(buffer));
      wholePacks.set(href, loading);
      loading.catch(() => wholePacks.delete(href));  // tried again next time
    } finally {
      answered();
    }
  }
  return (await wholePacks.get(href)).subarray(start, end + 1);
}

async function gunzipText(bytes) {
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
  return new Response(stream).text();
}

export async function fetchShard(base, shard) {
  const url = new URL(shard.path, base);
  if (shard.offset === undefined || shard.offset === null) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${shard.path}: HTTP ${response.status}`);
    return response.json();
  }
  const bytes = await packBytes(url, shard);
  if (bytes.length !== shard.length) throw new Error(`${shard.path}: short read at ${shard.offset}`);
  const text = shard.encoding === "gzip" ? await gunzipText(bytes) : new TextDecoder().decode(bytes);
  return JSON.parse(text);
}
