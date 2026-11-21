"""Local tile server of the Processing export (resources/tiles_server.py):
folder names with URI characters, no other site reading the tiles, zooms
checked before any arithmetic."""

import http.client
import importlib.util
import sqlite3
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[2] / "resources" / "tiles_server.py"


def _module():
    spec = importlib.util.spec_from_file_location("q2vt_tiles_server", SERVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mbtiles(folder: Path) -> None:
    folder.mkdir(parents=True)
    conn = sqlite3.connect(str(folder / "tiles.mbtiles"))
    conn.execute("CREATE TABLE metadata (name TEXT, value TEXT)")
    conn.execute("CREATE TABLE tiles (zoom_level INT, tile_column INT, tile_row INT, tile_data BLOB)")
    conn.executemany("INSERT INTO metadata VALUES (?, ?)", [("minzoom", "0"), ("maxzoom", "2")])
    conn.execute("INSERT INTO tiles VALUES (0, 0, 0, ?)", (b"SECRET",))
    conn.commit()
    conn.close()


@pytest.mark.parametrize("name", ["plain", "web #2", "50%20done", "what?", "a #b %41"])
def test_mbtiles_opens_in_folders_with_uri_characters(tmp_path, name):
    """SQLite's URI mode ended the path at '#' or '?' and decoded '%xx':
    the viewer then showed no data."""
    module = _module()
    _mbtiles(tmp_path / name)
    layers = module.load_mbtiles(tmp_path / name)
    try:
        assert list(layers) == ["tiles"]
        assert layers["tiles"]["maxzoom"] == 2
    finally:
        for layer in layers.values():
            layer["conn"].close()


def test_mbtiles_uri_of_a_network_share_has_no_authority():
    """A mapped drive resolves to UNC (//server/share): 'file://server/...'
    made 'server' the URI authority and SQLite refused it."""
    from urllib.parse import urlsplit

    module = _module()

    class Unc:
        def resolve(self):
            return self

        def as_posix(self):
            return "//server/share/web #2/tiles.mbtiles"

    uri = module._sqlite_uri(Unc())
    assert urlsplit(uri).netloc == ""
    assert uri.startswith("file:////server/share/web%20%232/")
    drive = Unc()
    drive.as_posix = lambda: "C:/web/tiles.mbtiles"
    assert module._sqlite_uri(drive).startswith("file:///C:/web/tiles.mbtiles?")


@pytest.fixture
def server(tmp_path):
    module = _module()
    _mbtiles(tmp_path / "export")
    (tmp_path / "export" / "style").mkdir()
    (tmp_path / "export" / "style" / "style.json").write_text("{}", encoding="utf-8")
    module.STYLE_DIR = tmp_path / "export" / "style"
    module.ROOT_DIR = tmp_path / "export"
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), module.Handler)
    httpd.daemon_threads = True
    httpd.layers = module.load_mbtiles(tmp_path / "export")
    httpd.static_cache = module.StaticCache([module.STYLE_DIR])
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()
    for layer in httpd.layers.values():
        layer["conn"].close()


def _get(port, path, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request("GET", path, headers=headers or {})
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        conn.close()


def test_other_sites_cannot_read_tiles_or_style(server):
    """No "Access-Control-Allow-Origin: *": a web page open in the browser
    read the exported data from the loopback server."""
    for path in ("/tiles/tiles/0/0/0.pbf", "/style/style.json"):
        status, headers, body = _get(server, path, {"Origin": "http://evil.example"})
        assert status == 403 and body == b"", (path, status)
        assert "Access-Control-Allow-Origin" not in headers
        # Another web app of this computer on port 80/443 (no port in Origin).
        for origin in ("http://localhost", "https://localhost", "http://127.0.0.1"):
            status, headers, body = _get(server, path, {"Origin": origin})
            assert status == 403 and body == b"", (path, origin, status)
            assert "Access-Control-Allow-Origin" not in headers
        status, _, body = _get(server, path, {"Host": "localhost"})
        assert status == 403 and body == b"", (path, status)
        # A DNS-rebound name reaching 127.0.0.1.
        status, _, body = _get(server, path, {"Host": f"evil.example:{server}"})
        assert status == 403 and body == b"", (path, status)


def test_the_viewer_still_reads_them(server):
    status, headers, body = _get(server, "/tiles/tiles/0/0/0.pbf")
    assert status == 200 and body == b"SECRET"
    assert "Access-Control-Allow-Origin" not in headers  # same origin: none needed
    # The style names localhost, the page may be 127.0.0.1: each other's origin.
    for origin in (f"http://localhost:{server}", f"http://127.0.0.1:{server}"):
        status, headers, body = _get(server, "/tiles/tiles/0/0/0.pbf",
                                     {"Origin": origin, "Host": f"localhost:{server}"})
        assert status == 200 and body == b"SECRET"
        assert headers["Access-Control-Allow-Origin"] == origin
    # Another port of this computer is another site.
    status, _, _ = _get(server, "/style/style.json", {"Origin": f"http://localhost:{server + 1}"})
    assert status == 403


@pytest.mark.parametrize("path", ["/tiles/tiles/-1/0/0.pbf", "/tiles/tiles/4000000000/0/0.pbf",
                                  "/tiles/tiles/31/0/0.pbf", "/tiles/tiles/1/2/0.pbf",
                                  "/tiles/tiles/1/0/-1.pbf"])
def test_tile_coordinates_out_of_range_are_rejected(server, path):
    """A negative zoom raised (negative shift), a huge one made a huge
    integer per request before SQLite refused it."""
    status, _, body = _get(server, path)
    assert status == 400 and body == b""
    assert _get(server, "/tiles/tiles/0/0/0.pbf")[0] == 200  # the server still answers




def test_a_port_used_by_another_program_moves_the_server_and_its_urls(tmp_path):
    """Another program (MinIO, PHP-FPM, Portainer...) on the port: the server
    takes the next free one, and the style and viewer name the port it got."""
    import socket  # pylint: disable=import-outside-toplevel
    module = _module()
    _mbtiles(tmp_path / "export")
    style = tmp_path / "export" / "style"
    style.mkdir()
    module.STYLE_DIR, module.ROOT_DIR = style, tmp_path / "export"
    other = socket.socket()
    other.bind(("127.0.0.1", 0))
    other.listen(1)
    taken = other.getsockname()[1]
    text = ('{"glyphs": "http://localhost:%d/style/glyphs/{fontstack}/{range}.pbf", '
            '"sprite": "http://127.0.0.1:%d/style/sprite/sprite", "value": "localhost:%d"}' % (taken, taken, taken))
    (style / "style.json").write_text(text, encoding="utf-8")
    try:
        httpd = module.bind(taken)
        actual = httpd.server_address[1]
        assert actual != taken
        moved = [(f"{h}:{taken}/".encode(), f"{h}:{actual}/".encode()) for h in ("localhost", "127.0.0.1")]
        httpd.daemon_threads = True
        httpd.layers = module.load_mbtiles(tmp_path / "export")
        httpd.static_cache = module.StaticCache([style], rewrite=moved)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            status, _, body = _get(actual, "/style/style.json")
            assert status == 200
            # The URLs follow the port; a value that only looks like one does not.
            assert body.decode() == text.replace(f"localhost:{taken}/", f"localhost:{actual}/").replace(
                f"127.0.0.1:{taken}/", f"127.0.0.1:{actual}/")
            assert f'"localhost:{taken}"' in body.decode()
        finally:
            httpd.shutdown()
            httpd.server_close()
            for layer in httpd.layers.values():
                layer["conn"].close()
    finally:
        other.close()


def test_a_free_port_is_used_as_asked(tmp_path):
    import socket  # pylint: disable=import-outside-toplevel
    module = _module()
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    httpd = module.bind(port)
    try:
        assert httpd.server_address[1] == port
    finally:
        httpd.server_close()


def test_a_program_listening_on_all_addresses_is_not_shared(tmp_path):
    """macOS and Windows let 127.0.0.1:port be bound beside a program on
    0.0.0.0:port (the requests then go to either): the port is skipped."""
    import socket  # pylint: disable=import-outside-toplevel
    module = _module()
    other = socket.socket()
    other.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    other.bind(("0.0.0.0", 0))
    other.listen(1)
    taken = other.getsockname()[1]
    try:
        httpd = module.bind(taken)
        try:
            assert httpd.server_address[1] != taken
        finally:
            httpd.server_close()
    finally:
        other.close()


def test_a_bound_port_another_program_answers_on_is_left(monkeypatch):
    """The check after binding (macOS, Windows, [::1]): the port is released
    and the next one taken."""
    module = _module()
    seen = []

    def answers(host, port):
        seen.append(port)
        return len(seen) <= 2  # the first port: someone answers
    monkeypatch.setattr(module, "_answers", answers)
    import socket  # pylint: disable=import-outside-toplevel
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    first = probe.getsockname()[1]
    probe.close()
    httpd = module.bind(first)
    try:
        assert httpd.server_address[1] != first and seen[0] == first
    finally:
        httpd.server_close()
