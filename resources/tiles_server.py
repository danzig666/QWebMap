"""Serve mbtiles, style.json, sprite — and the offline viewer.

The viewer has to be served over HTTP (not opened as file://) because
modern browsers refuse to load ES-module bundles and reject fetch()
calls when the page origin is a file:// URL. Hosting everything from
one localhost server avoids that and avoids CORS hassles too.

Directory layout assumed:
    <root>/
        *.mbtiles
        style/
            style.json
            sprite/                       # sprite.json, sprite.png, sprite@2x.*
        utils/
            tile_server.py                # ← this file
            viewer/                       # viewer.html, bundle.js, ol.css …
"""

import argparse
import errno
import hashlib
import os
import socket
import sqlite3
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
HERE        = Path(__file__).resolve().parent
ROOT_DIR    = HERE.parent
STYLE_DIR   = ROOT_DIR / "style"
VIEWER_DIR  = HERE / "viewer"
# Names of this computer the viewer may be opened with (no other site).
LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "::1")


# Files holding this server's own address (style.json's tile, glyph and
# sprite URLs, the viewer's style URL): moved with the port.
TEXT_SUFFIXES = (".json", ".html", ".js", ".mjs")
# Ports tried after the one asked for, when another program uses it.
PORT_TRIES = 50


# Pre-built mime map — avoids per-request mimetypes.guess_type() overhead
MIME_TYPES = {
    ".json":  "application/json",
    ".html":  "text/html; charset=utf-8",
    ".js":    "application/javascript",
    ".mjs":   "application/javascript",
    ".css":   "text/css",
    ".png":   "image/png",
    ".jpg":   "image/jpeg",
    ".jpeg":  "image/jpeg",
    ".webp":  "image/webp",
    ".svg":   "image/svg+xml",
    ".ico":   "image/x-icon",
    ".woff":  "font/woff",
    ".woff2": "font/woff2",
    ".map":   "application/json",
    ".pbf":   "application/x-protobuf",
}


# ----------------------------------------------------------------------
# MBTiles
# ----------------------------------------------------------------------
def xyz_y_to_tms(zoom: int, y: int) -> int:
    """Flip Y between XYZ (browser) and TMS (mbtiles) tile schemes."""
    return (1 << zoom) - 1 - y


def _sqlite_uri(path: Path) -> str:
    """Read-only SQLite URI of *path*: '#', '?' and '%' of a folder name
    escaped (SQLite would end or decode the path there)."""
    full = path.resolve().as_posix()
    if not full.startswith("/"):
        full = "/" + full    # C:/... -> file:///C:/...
    # Always an empty authority: a mapped drive resolves to UNC
    # (//server/share/...), and 'file://server/...' is an invalid authority.
    return "file://" + quote(full, safe="/:") + "?mode=ro&immutable=1"


def load_mbtiles(directory: Path) -> dict:
    """Open every .mbtiles in *directory* read-only with aggressive SQLite tuning."""
    layers = {}
    for f in directory.glob("*.mbtiles"):
        try:
            conn = sqlite3.connect(
                _sqlite_uri(f),
                uri=True,
                check_same_thread=False,
                isolation_level=None,
            )
            # Read-only, memory-mapped, generous page cache — best read perf
            conn.execute("PRAGMA query_only   = ON")
            conn.execute("PRAGMA temp_store   = MEMORY")
            conn.execute("PRAGMA mmap_size    = 268435456")   # 256 MB
            conn.execute("PRAGMA cache_size   = -65536")      # 64 MB
            conn.execute("PRAGMA journal_mode = OFF")
            conn.execute("PRAGMA synchronous  = OFF")

            meta = dict(conn.execute("SELECT name, value FROM metadata").fetchall())

            layers[f.stem] = {
                "conn":    conn,
                "lock":    threading.Lock(),
                "minzoom": int(meta.get("minzoom", 0)),
                "maxzoom": int(meta.get("maxzoom", 14)),
            }
            print(f"Loaded {f.name} "
                  f"(zoom {layers[f.stem]['minzoom']}-{layers[f.stem]['maxzoom']})")
        except (sqlite3.Error, OSError) as e:
            print(f"Failed to load {f.name}: {e}")
    return layers


# ----------------------------------------------------------------------
# Static cache (style/, sprite/, viewer/)
# Stores (data, mime, etag) per file. ETag is a content hash, so any
# change to the file on disk between server runs produces a different
# tag and any browser cache entry pinned to the old tag is invalidated.
# ----------------------------------------------------------------------
class StaticCache:
    """Lazy thread-safe in-memory cache, scoped to a list of allowed dirs."""

    __slots__ = ("_cache", "_lock", "_allowed", "_rewrite")

    def __init__(self, allowed_dirs, rewrite=None):
        self._cache   = {}
        self._lock    = threading.Lock()
        self._allowed = [d.resolve() for d in allowed_dirs]
        # (old bytes, new bytes) pairs for the text files (the port moved).
        self._rewrite = rewrite or []

    def get(self, file_path: Path):
        """Return (bytes, mime, etag) — or None if missing or out of scope."""
        target = file_path.resolve()

        if not any(self._is_under(target, d) for d in self._allowed):
            return None      # path-traversal guard

        key    = str(target)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                return cached
            if not target.is_file():
                return None
            data  = target.read_bytes()
            mime  = MIME_TYPES.get(target.suffix.lower(),
                                   "application/octet-stream")
            if target.suffix.lower() in TEXT_SUFFIXES:
                for old, new in self._rewrite:
                    data = data.replace(old, new)
            etag  = '"' + hashlib.md5(data, usedforsecurity=False).hexdigest()[:16] + '"'
            entry = (data, mime, etag)
            self._cache[key] = entry
            return entry

    @staticmethod
    def _is_under(target: Path, parent: Path) -> bool:
        try:
            target.relative_to(parent)
            return True
        except ValueError:
            return False


# ----------------------------------------------------------------------
# HTTP handler
# ----------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    """Serves /viewer/*, /style/*, /tiles/{layer}/{z}/{x}/{y}.pbf — and nothing else."""

    # HTTP/1.1 keep-alive (tile bursts reuse a single TCP connection)
    # and TCP_NODELAY for low-latency response delivery.
    protocol_version        = "HTTP/1.1"
    disable_nagle_algorithm = True

    # ---- routing ----
    def do_GET(self):
        # Only the viewer's own pages: another site open in the browser (or a
        # DNS-rebound name) must not read the exported data.
        if not self._local_request():
            return self._send_status(403)
        path = unquote(self.path).lstrip("/").split("?", 1)[0]

        # Root / bare /viewer  → viewer home page
        if path in ("", "viewer", "viewer/"):
            return self._serve_static(VIEWER_DIR / "viewer.html")

        # Viewer assets (bundle.js, ol.css, etc.)
        if path.startswith("viewer/"):
            return self._serve_static(VIEWER_DIR / path[len("viewer/"):])

        # Tiles
        if path.startswith("tiles/"):
            return self._serve_tile(path)

        # Style + sprites
        if path == "style" or path.startswith("style/"):
            return self._serve_static(ROOT_DIR / path)

        self._send_status(404)

    # ---- tiles ----
    def _serve_tile(self, path: str):
        parts = path.split("/")
        if len(parts) < 5:
            return self._send_status(400)

        try:
            z = int(parts[2])
            x = int(parts[3])
            y = int(parts[4].split(".", 1)[0])
        except ValueError:
            return self._send_status(400)
        # Before any arithmetic: a huge zoom is a huge integer (1 << z).
        if not (0 <= z <= 30 and 0 <= x < (1 << z) and 0 <= y < (1 << z)):
            return self._send_status(400)

        layer = self.server.layers.get(parts[1])
        if layer is None:
            return self._send_status(404)

        tms_y = xyz_y_to_tms(z, y)

        with layer["lock"]:
            row = layer["conn"].execute(
                "SELECT tile_data FROM tiles "
                "WHERE zoom_level=? AND tile_column=? AND tile_row=?",
                (z, x, tms_y),
            ).fetchone()

        if row is None:
            return self._send_status(204)

        data = row[0]

        self.send_response(200)
        self.send_header("Content-Type",   "application/x-protobuf")
        if data[:2] == b"\x1f\x8b":
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control",  "no-cache")
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    # ---- static (viewer + style + sprite + glyphs) ----
    def _serve_static(self, target: Path):
        entry = self.server.static_cache.get(target)
        if entry is None:
            return self._send_status(404)

        data, mime, etag = entry

        if self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", "0")
            self._cors()
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", mime)
        
        if mime == "application/x-protobuf" and data[:2] == b"\x1f\x8b":
            self.send_header("Content-Encoding", "gzip")

        self.send_header("Content-Length", str(len(data)))
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", "no-cache")
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    # ---- helpers ----
    def _send_status(self, code: int):
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self._cors()
        self.end_headers()

    def _own_origin(self, value: str) -> bool:
        """``value`` (a Host or an Origin) names this server on loopback."""
        try:
            url = urlsplit(value if "//" in value else "//" + value)
            host, port = url.hostname, url.port
        except ValueError:
            return False
        if port is None:
            # No port means the scheme's default (80/443), never this server.
            port = 443 if url.scheme == "https" else 80
        return host in LOOPBACK_HOSTS and port == self.server.server_address[1]

    def _local_request(self) -> bool:
        host, origin = self.headers.get("Host"), self.headers.get("Origin")
        return (host is None or self._own_origin(host)) and \
            (origin is None or self._own_origin(origin))

    def _cors(self):
        # localhost and 127.0.0.1 are two origins (the style's absolute URLs
        # name localhost): allowed to each other, no other site.
        origin = self.headers.get("Origin")
        if origin and self._own_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def log_message(self, fmt, *args):   # noqa: A002
        # Silence per-request stderr noise
        pass


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
class _Server(ThreadingHTTPServer):
    """No address reuse on Windows: there SO_REUSEADDR lets a second program
    bind a port that is already listened on (the requests then go to either)."""
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def _taken_on_ipv6(port: int) -> bool:
    """Something listens on [::1]:port: "localhost" may reach it instead of
    this server (browsers try ::1 first), so the port is not ours."""
    try:
        with socket.create_connection(("::1", port), timeout=0.3):
            return True
    except OSError:
        return False


def bind(port: int):
    """A server on ``port``, else on the next free one of PORT_TRIES, else on
    any free port: another program (MinIO, PHP-FPM, Portainer…) may use it."""
    for candidate in [p for p in range(port, port + PORT_TRIES) if p < 65536] + [0]:
        if candidate and _taken_on_ipv6(candidate):
            continue
        try:
            return _Server(("127.0.0.1", candidate), Handler)
        except OSError as error:
            if error.errno not in (errno.EADDRINUSE, errno.EACCES, 10048, 10013):
                raise
    raise OSError(errno.EADDRINUSE, "no free port")


def run(port: int = 18111991, open_path: str = ""):

    layers = load_mbtiles(ROOT_DIR)
    if not layers:
        print("No .mbtiles found in:", ROOT_DIR)

    server                = bind(port)
    actual                = server.server_address[1]
    server.daemon_threads = True
    server.layers         = layers
    moved = [] if actual == port else [
        (f"{host}:{port}/".encode(), f"{host}:{actual}/".encode())
        for host in ("localhost", "127.0.0.1")]
    server.static_cache   = StaticCache([VIEWER_DIR, STYLE_DIR], rewrite=moved)

    if actual != port:
        print(f"\nPort {port} is used by another program: using {actual}.")
    print(f"\nServer running at http://localhost:{actual}")
    print(f"  Viewer:  http://localhost:{actual}/viewer/viewer.html")
    print( "  Style:   /style/style.json")
    print( "  Sprite:  /style/sprite/sprite.{json,png}")
    print( "  Tiles:   /tiles/{layer}/{z}/{x}/{y}.pbf\n")
    if open_path:
        # Here, not in the launcher: only this server knows its port.
        threading.Timer(0.5, webbrowser.open,
                        [f"http://localhost:{actual}/{open_path.lstrip('/')}"]).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        for layer in layers.values():
            try:
                layer["conn"].close()
            except sqlite3.Error:
                pass
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MBTiles tile server")
    parser.add_argument("--port", type=int, default=18111991,
                        help="TCP port to listen on (1–65535, default %(default)s); "
                             "the next free one if another program uses it")
    parser.add_argument("--open", default="",
                        help="open this page of the server in the browser once it listens")
    args = parser.parse_args()
    run(args.port, args.open)