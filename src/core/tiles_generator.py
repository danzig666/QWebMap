"""
tiles_generator.py

GDALTilesGenerator — builds a multi-layer OGR VRT from the exported
datasets and calls ogr2ogr to produce MVT (Mapbox Vector Tiles) in MBTiles
format.

* Per-layer zoom ranges come from explicit metadata (the flattened rules),
  with the legacy filename parsing kept only as a fallback.
* There is no hidden per-layer zoom cap: the archive covers every requested
  zoom (the legacy VRT silently capped each layer at zoom 16).
* The VRT is written with an XML library, so paths containing ``&``, ``<``
  or non-ASCII characters are escaped correctly.
* Generated ``q2vt_property_*`` fields are pruned from the style's actual
  per-source-layer dependencies, not by searching ``str(style)``.
* ogr2ogr runs as an argument list (no shell) and is terminated when the
  user cancels.
"""

import collections
import contextlib
import heapq
import itertools
import json
import math
import os
import pathlib
import re
import sqlite3
import shutil
import subprocess
import threading
import tempfile
import time
import xml.etree.ElementTree as ET
import zlib
from concurrent.futures import ThreadPoolExecutor
from os import cpu_count
from os.path import join, basename
from typing import Dict, List, Optional, Tuple
from osgeo import gdal, ogr
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsProcessingFeedback, QgsProcessingUtils

from ..utils import main_thread
from ..utils import gdal_guard
from ..utils.config import _EPSG_CRS, _SIMPLIFICATION, _SIMPLIFICATION_MAX_ZOOM
from .fidelity.dependencies import prunable_fields, style_field_dependencies
from . import export_cache
from .datasets import drop_fields, gpkg_info

# The MVT writer keeps its features in a temporary SQLite database, by default
# a file next to the output; in memory (/vsimem) a run is about a third
# faster. It takes up to about 4x the run's input (measured); a run goes in
# memory while 8x its input fits in half of the memory left (an idea of
# QGIS2VectorTiles 4.0, GallPeters/QGIS2VectorTiles); a run that fails is
# run once more on disk.
_MEMORY_DB_FACTOR = 8


def available_memory() -> Optional[int]:
    """Bytes of memory the system can still give (None: unknown)."""
    try:
        if os.name == "nt":
            import ctypes  # pylint: disable=import-outside-toplevel

            class _Status(ctypes.Structure):  # MEMORYSTATUSEX
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
                            ("total", ctypes.c_ulonglong), ("available", ctypes.c_ulonglong),
                            ("page_total", ctypes.c_ulonglong), ("page_available", ctypes.c_ulonglong),
                            ("virtual_total", ctypes.c_ulonglong), ("virtual_available", ctypes.c_ulonglong),
                            ("extended", ctypes.c_ulonglong)]
            status = _Status()
            status.length = ctypes.sizeof(_Status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.available)
            return None
        with open("/proc/meminfo", encoding="ascii") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
    except Exception:  # noqa: BLE001 - macOS and others: on disk
        return None
    return None


def vrt_input_bytes(vrt_path: str) -> int:
    """Size of the files a tile run's VRT reads."""
    total = 0
    try:
        for node in ET.parse(vrt_path).getroot().iter("SrcDataSource"):
            path = (node.text or "").split("|")[0]
            if os.path.isfile(path):
                total += os.path.getsize(path)
    except (ET.ParseError, OSError):
        return 0
    return total

_MVT_MAX_ZOOM = 22


def mbtiles_uri(path: str) -> str:
    """Vector tile layer URI of an MBTiles file, the path encoded as QGIS
    decodes it (an output folder named "Maps & Data" cut the plain path
    short at the "&")."""
    uri = QgsDataSourceUri()
    uri.setParam("type", "mbtiles")
    uri.setParam("url", path)
    return bytes(uri.encodedUri()).decode()



def _open_gpkg(path: str, update: bool = False):
    """A GeoPackage opened with GDAL's GeoPackage driver only. ogr.Open
    without a driver probes every driver (in recent GDAL loading plugin
    drivers on first use), which crashed QGIS 4 on Windows when the main
    thread opened raster layers at the same moment. Anything else (not a
    GeoPackage): ogr.Open as before."""
    flags = gdal.OF_VECTOR | (gdal.OF_UPDATE if update else gdal.OF_READONLY)
    try:
        ds = gdal.OpenEx(path, flags, allowed_drivers=["GPKG"])
    except RuntimeError:
        ds = None
    if ds is not None:
        return ds
    try:
        return ogr.Open(path, update=1 if update else 0)
    except RuntimeError:
        return None

class TilesGenerationCancelled(RuntimeError):
    """Raised when the user cancels while ogr2ogr is running."""


# Seconds per unit of TileProgress cost until a job has finished (measured
# 6e-8 .. 1.1e-7 with 4 jobs on 4 cores; the finished jobs correct it).
_SECONDS_PER_COST = 1e-7
# Cost of one output tile, in source bytes.
_TILE_COST = 2000


class TileProgress:
    """Estimated progress of ogr2ogr jobs.

    A job's cost is the size of its datasets times their zoom levels plus
    the tiles of the extent at those zooms. A job that reports its progress
    (ogr2ogr -progress: the share of its features written; the tiles are
    put together after the last ones) advances with it. Otherwise a running
    job advances with its elapsed time against the time its cost should
    take at the rate of the jobs already finished (a fixed guess before the
    first one); past that time it still creeps on, never reaching its end
    before it finishes.
    """

    # Share of a job done when all its features are written.
    _FEATURES = 0.85

    def __init__(self, costs: List[float], reporting: bool = False):
        self.costs = [max(1.0, float(c)) for c in costs]
        self.total = sum(self.costs)
        self.reporting = reporting  # the jobs report their progress
        self.started: Dict[int, float] = {}
        self.finished: Dict[int, float] = {}
        self.reported: Dict[int, float] = {}
        self._written: Dict[int, float] = {}
        self._last = 0.0

    def start(self, job: int, now: float) -> None:
        self.started[job] = now

    def report(self, job: int, fraction: float, now: float) -> None:
        """``fraction`` of the job's features written (ogr2ogr -progress)."""
        self.reported[job] = max(self.reported.get(job, 0.0), min(1.0, fraction))
        if self.reported[job] >= 0.97 and job not in self._written:
            self._written[job] = now

    def finish(self, job: int, now: float) -> None:
        self.finished[job] = now - self.started.get(job, now)

    def forget(self, job: int) -> None:
        """A job to be run again: its progress so far does not count."""
        for known in (self.started, self.reported, self._written):
            known.pop(job, None)

    def rate(self) -> float:
        cost = sum(self.costs[j] for j in self.finished)
        seconds = sum(self.finished.values())
        return seconds / cost if cost > 0 and seconds > 0 else _SECONDS_PER_COST

    def _reported_part(self, job: int, now: float) -> float:
        reported = self.reported[job]
        written = self._written.get(job)
        if written is None:
            return self._FEATURES * reported
        # Putting the tiles together: about a fifth of the time the features took.
        tau = max(1.0, 0.25 * (written - self.started[job]))
        return self._FEATURES + (0.99 - self._FEATURES) * (1 - math.exp(-(now - written) / tau))

    def fraction(self, now: float) -> float:
        rate = self.rate()
        done = sum(self.costs[j] for j in self.finished)
        for job, began in self.started.items():
            if job in self.finished:
                continue
            if job in self.reported:
                done += self.costs[job] * self._reported_part(job, now)
                continue
            if self.reporting:
                continue  # not one feature written yet
            x = (now - began) / max(1e-9, self.costs[job] * rate)
            part = 0.9 * x if x <= 1 else 0.9 + 0.09 * (1 - math.exp(-(x - 1)))
            done += self.costs[job] * part
        self._last = max(self._last, min(1.0, done / self.total if self.total else 1.0))
        return self._last


class _OutputReader(threading.Thread):
    """Reads a job's output as it comes, so a full pipe never stops it:
    ogr2ogr -progress on stdout ("0...10...20..." up to "100 - done."),
    the end of stderr for the error message."""

    def __init__(self, stream, progress: bool):
        super().__init__(daemon=True)
        self.stream = stream
        self.progress = progress
        self.fraction = 0.0
        self.text = ""

    def run(self) -> None:
        if not self.progress:  # the error text: read by lines, the last 20000 characters kept
            tail, size = collections.deque(), 0
            try:
                for line in self.stream:
                    tail.append(line)
                    size += len(line)
                    while size - len(tail[0]) >= 20000:
                        size -= len(tail.popleft())
            except (OSError, ValueError):
                pass
            self.text = "".join(tail)[-20000:]
            return
        number, dots, last = "", 0, 0
        try:
            for char in iter(lambda: self.stream.read(1), ""):
                if char.isdigit():
                    number += char
                    continue
                if number:
                    last, dots, number = int(number), 0, ""
                if char == ".":
                    dots += 1  # each dot is 2.5 %
                self.fraction = min(1.0, (last + 2.5 * dots) / 100.0)
        except (OSError, ValueError):
            pass


class GDALTilesGenerator:
    """Generate MBTiles vector tiles using GDAL CLI with an OGR VRT intermediary."""

    def __init__(
        self,
        layers: List[QgsVectorLayer],
        style: dict,
        output_dir: str,
        extent,
        cpu_percent: int,
        feedback: QgsProcessingFeedback,
        layer_zooms: Optional[Dict[str, Tuple[int, int]]] = None,
        cache: Optional["export_cache.ExportCache"] = None,
        dataset_keys: Optional[Dict[str, str]] = None,
        layer_groups: Optional[Dict[str, List[str]]] = None,
        progress_range: Tuple[float, float] = (0.0, 100.0),
        exact_datasets: Optional[set] = None,
        min_feature_px: float = 0.0,
        small_datasets: Optional[set] = None,
        merged: Optional[Dict[str, int]] = None,
    ):
        # {QGIS layer id: zoom}: below it the layer's fills and outlines are
        # tiled from copies merged per tile (merge_per_tile).
        self.merged = {k: int(v) for k, v in (merged or {}).items()}
        # With a cache: one tile set per QGIS layer (its datasets), reused
        # while the layer's datasets are unchanged, then merged.
        self.cache = cache
        self.dataset_keys = dataset_keys or {}
        self.layer_groups = layer_groups or {}
        # Datasets tiled without simplification: colour bands that do not
        # overlap share their edges, which must stay the same in both bands
        # (simplified apart, they open cracks and lose thin rings).
        self.exact_datasets = exact_datasets or set()
        # Fills and lines of ``small_datasets`` under ``min_feature_px`` CSS
        # px (both sides of their bounding box) are left out of the tiles of
        # the zooms where they are that small (see _small_cuts).
        self.min_feature_px = max(0.0, float(min_feature_px or 0.0))
        self.small_datasets = small_datasets or set()
        # Zoom ranges of the datasets' unfiltered tiles (_small_cuts).
        self._zoom_override: Dict[str, Tuple[int, int]] = {}
        self.layers = layers
        self.style = style
        self.output_dir = output_dir
        self.extent = extent
        self.cpu_percent = cpu_percent
        self.feedback = feedback
        self.layer_zooms = layer_zooms or {}
        self.progress_range = progress_range
        # (table, fields) per dataset file, read once (remove_unused_fields).
        self._datasets: Dict[str, Tuple[Optional[str], List[str]]] = {}
        # ogr2ogr seconds per QGIS layer id (layer_groups), for the export log,
        # and the number of jobs (pieces of zoom levels run side by side).
        self.layer_seconds: Dict[str, float] = {}
        self.layer_pieces: Dict[str, int] = {}

    def _report(self, fraction: float) -> None:
        if self.feedback is not None:
            low, high = self.progress_range
            self.feedback.setProgress(low + (high - low) * fraction)

    def _tiles_at(self, zoom: int) -> int:
        """Tiles of the export extent at ``zoom`` (whole world without one)."""
        n = 2 ** zoom
        extent = self.extent
        if extent is None or extent.isEmpty():
            return n * n
        half = 20037508.342789244
        size = 2 * half / n

        def span(low, high):
            return int(math.floor((high + half) / size)) - int(math.floor((low + half) / size)) + 1
        return max(1, min(n, span(extent.xMinimum(), extent.xMaximum()))
                   * min(n, span(extent.yMinimum(), extent.yMaximum())))

    def _job_cost(self, members: List[QgsVectorLayer]) -> float:
        """TileProgress cost of tiling ``members``: every feature is cut at
        every zoom, and every tile is written."""
        cost = 0.0
        for layer in members:
            try:
                size = os.path.getsize(layer.source().split("|")[0])
            except OSError:
                size = 0
            low, high = self._layer_zoom_range(layer)
            cost += sum(size + _TILE_COST * self._tiles_at(z) for z in range(low, high + 1))
        return cost

    def generate(self) -> Tuple[str, int]:
        """Build VRT, run ogr2ogr, return (mbtiles URI, min_zoom).

        The tiles of each QGIS layer are made by their own ogr2ogr, several
        at a time, and merged (one ogr2ogr for everything used one core for
        most of its time); Q2VT_SINGLE_OGR2OGR=1 makes them in one run."""
        self.remove_unused_fields()
        output, uri = self._prepare_output_paths()
        vrt_path = join(QgsProcessingUtils.tempFolder(), "layers.vrt")

        min_zoom = self._get_global_min_zoom()
        max_zoom = self._get_global_max_zoom()

        if self.cache is not None or os.environ.get("Q2VT_SINGLE_OGR2OGR") != "1":
            self._generate_per_layer(output, min_zoom, max_zoom)
        else:
            self._build_vrt(vrt_path)
            conf_path = join(QgsProcessingUtils.tempFolder(), "layers_conf.json")
            self._write_layer_conf(conf_path)
            self._run_ogr2ogr(vrt_path, output, min_zoom, max_zoom, conf_path)
        self._prune_tiles_outside_extent(output)

        return uri, min_zoom

    @staticmethod
    def _layer_name(layer: QgsVectorLayer) -> str:
        return basename(layer.source().split("|layername=")[0]).rsplit(".", 1)[0]

    @gdal_guard.shared_section
    def remove_unused_fields(self):
        """Drop generated property fields that no style layer of *that* source layer reads."""
        dependencies = style_field_dependencies(self.style)
        for layer in self.layers:
            gpkg = layer.source().split("|layername=")[0]
            name = self._layer_name(layer)
            required = set(dependencies.get(name, set()))
            for suffix in ("_vp", "_vl"):  # the polygons / lines of a label: its fields
                if name.endswith(suffix):
                    required |= dependencies.get(name[:-len(suffix)], set())
            info = gpkg_info(gpkg)  # SQLite: a fraction of an OGR open
            if info is not None:
                unused = prunable_fields(info.fields, required)
                if drop_fields(gpkg, info.table, [n for n in info.fields if n in unused]):
                    self._datasets[gpkg] = (info.table, [n for n in info.fields if n not in unused])
                    continue
            ds = _open_gpkg(gpkg, update=True)
            if ds is None:
                continue
            ogr_layer = ds.GetLayer(0)
            layer_defn = ogr_layer.GetLayerDefn()
            names = [layer_defn.GetFieldDefn(i).GetName() for i in range(layer_defn.GetFieldCount())]
            unused = prunable_fields(names, required)
            # Iterate backwards because field indices change after deletion.
            for i in range(len(names) - 1, -1, -1):
                if names[i] in unused:
                    ogr_layer.DeleteField(i)
            self._datasets[gpkg] = (ogr_layer.GetName(), [n for n in names if n not in unused])
            ds = None  # Flush changes and close the dataset

    # --- VRT construction ---

    def _build_vrt(self, vrt_path: str, layers: Optional[List[QgsVectorLayer]] = None,
                   min_size: float = 0.0):
        """Write an OGR VRT containing one entry per layer with per-zoom
        configuration; with ``min_size`` (metres) only the features whose
        bounding box is that wide or high."""
        root = ET.Element("OGRVRTDataSource")
        for layer in self.layers if layers is None else layers:
            name = self._layer_name(layer)
            node = ET.SubElement(root, "OGRVRTLayer", name=name)
            source = layer.source().split("|layername=")[0]
            ET.SubElement(node, "SrcDataSource").text = source
            # The table inside the file: a dataset reused from the export cache
            # keeps the name it was first written under (another rule's name
            # when only the rule's zoom range changed); without SrcLayer OGR
            # looks for a table named like the tile layer and writes nothing.
            table = self._table_of(source)
            column = self._geometry_column(source) if min_size > 0 else None
            if table and column:
                ET.SubElement(node, "SrcSQL").text = (
                    f"SELECT * FROM {_quoted(table)} WHERE {self._size_sql(column)} >= {min_size!r}")
            elif table and table != name:
                ET.SubElement(node, "SrcLayer").text = table
            ET.SubElement(node, "LayerSRS").text = f"EPSG:{_EPSG_CRS}"
            ET.SubElement(node, "GeometryType").text = "wkbUnknown"
        ET.ElementTree(root).write(vrt_path, encoding="utf-8", xml_declaration=True)

    @staticmethod
    def _size_sql(column: str) -> str:
        """The larger side of a feature's bounding box (GeoPackage SQL)."""
        geom = _quoted(column)
        return f"MAX(ST_MaxX({geom}) - ST_MinX({geom}), ST_MaxY({geom}) - ST_MinY({geom}))"

    @staticmethod
    def _geometry_column(path: str) -> Optional[str]:
        try:
            uri = pathlib.Path(os.path.abspath(path)).as_uri() + "?mode=ro"
            with contextlib.closing(sqlite3.connect(uri, uri=True)) as conn:
                row = conn.execute("SELECT column_name FROM gpkg_geometry_columns").fetchone()
        except sqlite3.Error:
            return None
        return row[0] if row else None

    # Metres of a CSS px at zoom 0 (512 px tiles, EPSG:3857).
    _PX0 = 40075016.68557849 / 512.0

    @gdal_guard.shared_section
    def _size_range(self, layer: QgsVectorLayer) -> Optional[Tuple[float, float]]:
        """(smallest, largest) bounding box side of the dataset's features
        (the larger of width and height); None when unknown."""
        source = layer.source().split("|layername=")[0]
        column, table = self._geometry_column(source), self._table_of(source)
        if not column or not table:
            return None
        ds = _open_gpkg(source)
        if ds is None:
            return None
        try:
            result = ds.ExecuteSQL(f"SELECT MIN(s), MAX(s) FROM (SELECT {self._size_sql(column)} AS s "
                                   f"FROM {_quoted(table)} WHERE {_quoted(column)} IS NOT NULL)")
            if result is None:
                return None
            feature = result.GetNextFeature()
            values = (feature.GetField(0), feature.GetField(1)) if feature is not None else (None, None)
            ds.ReleaseResultSet(result)
        finally:
            ds = None
        if values[0] is None or values[1] is None:
            return None
        return float(values[0]), float(values[1])

    def _drawn_small(self, name: str, zoom: int) -> bool:
        """Whether the dataset is only drawn as fills and thin lines (at most
        2 px wide at ``zoom``): a feature smaller than a pixel draws no more
        than a pixel or two. Not a symbol (its label or icon), circle,
        extrusion or heatmap."""
        from .fidelity import expressions as ex  # pylint: disable=import-outside-toplevel
        if name.endswith(("_vp", "_vl")) or name in self.exact_datasets:
            return False
        style = self.style if isinstance(self.style, dict) else {}
        layers = [layer for layer in style.get("layers", []) if layer.get("source-layer") == name]
        if not layers:
            return False
        for layer in layers:
            kind = layer.get("type")
            if kind == "fill":
                continue
            if kind != "line":
                return False
            paint = layer.get("paint") or {}
            try:
                width = sum(float(ex.evaluate_zoom_curve(paint.get(key, default), zoom))
                            for key, default in (("line-width", 1), ("line-gap-width", 0)))
            except (ex.ExpressionError, TypeError, IndexError, ValueError):
                return False  # feature-dependent: unknown
            if width > 2:
                return False
        return True

    def _small_cuts(self, members: List[QgsVectorLayer]) -> Dict[str, Tuple[int, int, float]]:
        """{dataset: (first, last, largest)}: the zooms (below its last tile
        zoom) whose tiles leave out the dataset's features under
        ``min_feature_px``, and its largest feature size (metres). The tiles
        of those zooms are made one zoom at a time (_filtered_jobs); the
        dataset's other zooms as before."""
        cuts: Dict[str, Tuple[int, int, float]] = {}
        if self.min_feature_px <= 0:
            return cuts
        for layer in members:
            name = self._layer_name(layer)
            low, high = self._layer_zoom_range(layer)
            if name not in self.small_datasets or not self._drawn_small(name, max(low, high - 1)):
                continue
            sizes = self._size_range(layer) if high > low else None
            if sizes is None or sizes[0] <= 0 and sizes[1] <= 0:
                continue
            smallest = max(sizes[0], 1e-9)
            # The highest zoom where the smallest feature is under the limit.
            last = math.ceil(math.log2(self.min_feature_px * self._PX0 / smallest)) - 1
            last = min(high - 1, last)
            if last >= low:
                cuts[name] = (low, last, sizes[1])
        return cuts

    def _min_size(self, zoom: int) -> float:
        """``min_feature_px`` in metres at ``zoom``."""
        return self.min_feature_px * self._PX0 / 2 ** zoom

    def _write_layer_conf(self, conf_path: str, layers: Optional[List[QgsVectorLayer]] = None,
                          band: Optional[Tuple[int, int]] = None):
        """Per-layer zoom ranges for the MVT writer (``-dsco CONF``), cut to
        ``band`` for a piece of zoom levels (the writer makes every zoom of
        CONF, whatever the dataset's MINZOOM / MAXZOOM).

        OGR VRT has no layer-creation options, so zoom ranges put there are
        ignored and every dataset would be written at every zoom level.
        """
        conf = {}
        for layer in self.layers if layers is None else layers:
            min_zoom, max_zoom = self._layer_zoom_range(layer)
            if band is not None:
                min_zoom, max_zoom = max(min_zoom, band[0]), min(max_zoom, band[1])
            conf[self._layer_name(layer)] = {"minzoom": int(min_zoom), "maxzoom": int(max_zoom)}
        with open(conf_path, "w", encoding="utf-8") as handle:
            json.dump(conf, handle)

    # --- ogr2ogr execution ---

    @staticmethod
    def _ogr2ogr_executable() -> str:
        """ogr2ogr from the QGIS/GDAL environment (PATH as set up by QGIS)."""
        return shutil.which("ogr2ogr") or "ogr2ogr"

    def _cpu_num(self) -> int:
        return max(1, int((cpu_count() or 1) * self.cpu_percent / 100))

    # The MVT writer keeps geometry this far outside a tile (tile units, 4096
    # a tile; 80 = 10 CSS px is its default).
    _MIN_BUFFER, _MAX_BUFFER = 80, 1024

    def _buffer(self, members: Optional[List[QgsVectorLayer]] = None) -> int:
        """Clip buffer for the datasets ``members`` (all without): a line is
        cut that far outside the tile, so a wide line (map units at the last
        tile zoom, square caps) needs about its width there, or both edges of
        the band step where it crosses a tile edge. A translated fill or line
        (a QGIS fill offset) needs its shift there too: MapLibre draws a
        tile's features only inside the tile, so the neighbour's cut edge
        would show."""
        from .fidelity import expressions as ex  # pylint: disable=import-outside-toplevel
        members = self.layers if members is None else members
        top = {self._layer_name(m): self._layer_zoom_range(m)[1] for m in members}
        widest = 0.0
        for layer in self.style.get("layers", []) if isinstance(self.style, dict) else []:
            kind = layer.get("type")
            if kind not in ("line", "fill") or layer.get("source-layer") not in top:
                continue
            paint, zoom = layer.get("paint") or {}, top[layer["source-layer"]]
            # A style layer shown only beyond the last tile zoom draws its
            # tiles magnified: its width there is that much less of a tile.
            shown = max(zoom, float(layer.get("minzoom") or 0))
            magnify = 2 ** (shown - zoom)
            shift = self._translate_px(paint.get(f"{kind}-translate"), shown)
            if kind == "fill":
                widest = max(widest, shift / magnify)
                continue
            try:
                values = [ex.evaluate_zoom_curve(paint.get(name, default), shown)
                          for name, default in (("line-width", 1), ("line-gap-width", 0),
                                                ("line-offset", 0))]
            except (ex.ExpressionError, TypeError, IndexError):
                continue  # feature-dependent: unknown
            width, gap, offset = (float(v) for v in values)
            widest = max(widest, (width + 2 * gap + abs(offset) + shift) / magnify)
        units = math.ceil(widest * 8) + 8  # 8 tile units a CSS px (512 px tiles)
        return max(self._MIN_BUFFER, min(self._MAX_BUFFER, units))

    @staticmethod
    def _translate_px(translate, zoom: float) -> float:
        """Length of a ``*-translate`` ([x, y], or a zoom curve of literal
        [x, y] stops) at ``zoom``; 0 when unknown."""
        from .fidelity import expressions as ex  # pylint: disable=import-outside-toplevel
        if isinstance(translate, list) and len(translate) == 2 and \
                all(ex.is_number(v) for v in translate):
            return math.hypot(*translate)
        if not ex.is_zoom_curve(translate) or translate[0] != "interpolate":
            return 0.0
        try:
            parts = [list(translate[:3]) + [item if index % 2 == 0 else item[1][axis]
                                            for index, item in enumerate(translate[3:])]
                     for axis in (0, 1)]
            return math.hypot(*(ex.evaluate_zoom_curve(part, zoom) for part in parts))
        except (ex.ExpressionError, TypeError, IndexError):
            return 0.0

    # The MVT writer silently drops features from a tile over these limits
    # (5 MB / 2 million features were hit at zooms 0-8 by marker positions
    # materialized for every zoom): QGIS draws every feature, so no limit
    # that a tile of an export can reach.
    _MAX_TILE_BYTES = 1_000_000_000
    _MAX_TILE_FEATURES = 1_000_000_000

    def _ogr2ogr_command(self, vrt_path: str, output: str, min_zoom: int, max_zoom: int,
                         conf_path: Optional[str] = None,
                         top_simplification: float = _SIMPLIFICATION_MAX_ZOOM,
                         buffer: int = _MIN_BUFFER,
                         simplification: float = _SIMPLIFICATION) -> List[str]:
        """``top_simplification``: of each dataset's last zoom (its CONF
        maxzoom), as the writer applies SIMPLIFICATION_MAX_ZOOM."""
        cmd = [
            self._ogr2ogr_executable(), "-f", "MBTiles", output, vrt_path,
            "-dsco", f"MINZOOM={min_zoom}",
            "-dsco", f"MAXZOOM={max_zoom}",
            "-t_srs", f"EPSG:{_EPSG_CRS}",
            "-dsco", f"MAX_SIZE={self._MAX_TILE_BYTES}",
            "-dsco", f"MAX_FEATURES={self._MAX_TILE_FEATURES}",
            "-dsco", f"SIMPLIFICATION={simplification}",
            "-dsco", f"SIMPLIFICATION_MAX_ZOOM={min(top_simplification, simplification)}",
            "-dsco", f"BUFFER={buffer}",
        ]
        if conf_path:
            cmd += ["-dsco", f"CONF={conf_path}"]
        return cmd

    @staticmethod
    def _popen_options() -> dict:
        if os.name != "nt":
            return {}
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        return {"startupinfo": startupinfo, "creationflags": 0x08000000}  # CREATE_NO_WINDOW

    def _run_ogr2ogr(self, vrt_path: str, output: str, min_zoom: int, max_zoom: int,
                     conf_path: Optional[str] = None):
        """Execute ogr2ogr to convert the VRT to MBTiles."""
        env = os.environ.copy()
        env["GDAL_NUM_THREADS"] = str(self._cpu_num())
        cmd = self._ogr2ogr_command(vrt_path, output, min_zoom, max_zoom, conf_path,
                                    buffer=self._buffer())

        startupinfo = None
        creationflags = 0
        if os.name == "nt":
            creationflags = 0x08000000  # CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

        tracker = TileProgress([self._job_cost(self.layers)])
        # stderr to a file, not a pipe nobody reads while ogr2ogr runs: more
        # than a pipe's worth of GDAL warnings blocked it for ever.
        errors_file = tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace")
        with errors_file, subprocess.Popen(
            cmd, env=env, stdout=subprocess.DEVNULL, stderr=errors_file, text=True,
            startupinfo=startupinfo, creationflags=creationflags,
        ) as proc:
            started = last_message = last_report = time.monotonic()
            tracker.start(0, started)
            while proc.poll() is None:
                now = time.monotonic()
                if now - last_report > 1:
                    last_report = now
                    self._report(tracker.fraction(now))
                if self.feedback is not None and now - last_message > 15:
                    last_message = now
                    self.feedback.pushInfo(
                        f"   Still generating tiles ({(now - started) / 60:.1f} minutes, "
                        f"about {100 * tracker.fraction(now):.0f}% done)...")
                if self.feedback is not None and self.feedback.isCanceled():
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    if os.path.exists(output):
                        os.remove(output)  # partial archive in the new output dir only
                    raise TilesGenerationCancelled("Tile generation cancelled")
                time.sleep(0.1)
                main_thread.keep_responsive()
            proc.wait()
            errors_file.seek(0)
            stderr = errors_file.read()
            if proc.returncode != 0:
                error_msg = f"ogr2ogr failed.\nError: {stderr}"
                if self.feedback:
                    self.feedback.reportError(error_msg)
                raise RuntimeError(error_msg)

    # --- per-layer tiles (export cache) ---

    @staticmethod
    @gdal_guard.shared_section
    def _dataset_table(path: str) -> Optional[str]:
        ds = _open_gpkg(path)
        if ds is None or ds.GetLayerCount() == 0:
            return None
        name = ds.GetLayer(0).GetName()
        ds = None
        return name

    def _table_of(self, path: str) -> Optional[str]:
        known = self._datasets.get(path)
        return known[0] if known else self._dataset_table(path)

    @gdal_guard.shared_section
    def _dataset_fields(self, layer: QgsVectorLayer) -> List[str]:
        path = layer.source().split("|layername=")[0]
        if path in self._datasets:
            return list(self._datasets[path][1])
        ds = _open_gpkg(path)
        if ds is None:
            return []
        defn = ds.GetLayer(0).GetLayerDefn()
        names = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]
        ds = None
        return names

    def _tile_groups(self) -> List[Tuple[str, Optional[str], List[QgsVectorLayer]]]:
        """[(QGIS layer id, cache key or None, datasets)] — one group per QGIS
        layer, in the order of the datasets (the order of one combined export)."""
        by_name = {self._layer_name(layer): layer for layer in self.layers}
        owner = {name: lid for lid, names in self.layer_groups.items() for name in names}
        groups: Dict[Tuple[str, bool], List[QgsVectorLayer]] = {}
        for name, layer in by_name.items():
            groups.setdefault((owner.get(name, f"dataset:{name}"), name in self.exact_datasets),
                              []).append(layer)
        out = []
        for (owner_id, exact), members in groups.items():
            if self.cache is None:
                out.append((owner_id, None, members))
                continue
            parts = []
            for layer in members:
                name = self._layer_name(layer)
                key = self.dataset_keys.get(name)
                if key is None:
                    parts = None
                    break
                parts.append([name, key, list(self._layer_zoom_range(layer)),
                              self._dataset_fields(layer)])
            out.append((owner_id, export_cache.make_key("tiles", self._zooms, parts,
                                                        self._simplification(members),
                                                        _SIMPLIFICATION_MAX_ZOOM,
                                                        self._buffer(members),
                                                        *self._small_key(members),
                                                        *([["merged", self.merged[owner_id]]]
                                                          if owner_id in self.merged else []))
                        if parts is not None else None, members))
        return out

    def _small_key(self, members: List[QgsVectorLayer]) -> list:
        """The part of a tile group's cache key for leaving out small
        features: nothing (keys as before) when none can be."""
        if self.min_feature_px <= 0:
            return []
        # Which are filtered depends on their style too (a wider line is not
        # left out), which the datasets' keys do not cover.
        names = []
        for member in members:
            name = self._layer_name(member)
            low, high = self._layer_zoom_range(member)
            if name in self.small_datasets and self._drawn_small(name, max(low, high - 1)):
                names.append(name)
        return [self.min_feature_px, sorted(names)] if names else []

    # SIMPLIFICATION (tile units, 8 a CSS px) of lighter tiles (with
    # ``min_feature_px``): a quarter pixel at the tile's zoom, fewer points
    # in the tiles of the zooms below a dataset's last (that one stays
    # exact: SIMPLIFICATION_MAX_ZOOM). Neighbours simplified apart open
    # cracks of up to half a pixel where the tile is magnified most, which
    # MapLibre's antialiased fill edges cover.
    _LIGHT_SIMPLIFICATION = 2

    def _simplification(self, members: List[QgsVectorLayer]) -> float:
        """SIMPLIFICATION of a tile group (see ``exact_datasets``)."""
        if members and all(self._layer_name(m) in self.exact_datasets for m in members):
            return 0
        if self.min_feature_px > 0:
            return self._LIGHT_SIMPLIFICATION
        return _SIMPLIFICATION

    def _generate_per_layer(self, output: str, min_zoom: int, max_zoom: int):
        """Tiles of each QGIS layer's datasets (from the cache when unchanged),
        merged into ``output``."""
        self._zooms = [min_zoom, max_zoom]
        work = join(self.output_dir, "layer_tiles")
        os.makedirs(work, exist_ok=True)
        parts, groups = [], []
        for number, (owner, key, members) in enumerate(self._tile_groups()):
            cached = self.cache.get_tiles(key) if key and self.cache is not None else None
            if cached:
                parts.append(cached)
                continue
            target = join(work, f"group_{number:04d}.mbtiles")
            vrt = join(work, f"group_{number:04d}.vrt")
            conf = join(work, f"group_{number:04d}.json")
            # Of the datasets' whole zoom ranges (before the overrides below).
            buffer, simplification = self._buffer(members), self._simplification(members)
            long_lines = self._long_lines(members)
            cuts = self._small_cuts(members)
            small = dict(cuts)  # their zooms from the long lines' first on: in the cut copies
            merged = self._merged_members(owner, members)
            for name, (_low, last, _outline) in merged.items():  # those zooms: the merged copies
                if name in cuts and max(cuts[name][0], last + 1) <= cuts[name][1]:
                    cuts[name] = (max(cuts[name][0], last + 1),) + tuple(cuts[name][1:])
                elif name in cuts:
                    del cuts[name]
                if name in long_lines:
                    first, top = long_lines[name]
                    if max(first, last + 1) <= top:
                        long_lines[name] = (max(first, last + 1), top)
                    else:
                        del long_lines[name]
            for name, (first, _high) in long_lines.items():
                if name in cuts:
                    low, last, largest = cuts[name]
                    if min(last, first - 1) >= low:
                        cuts[name] = (low, min(last, first - 1), largest)
                    else:
                        del cuts[name]
            plain = []
            for layer in members:
                name = self._layer_name(layer)
                low, high = self._layer_zoom_range(layer)
                if name in small:  # the unfiltered tiles: the zooms after the cut
                    low = small[name][1] + 1
                if name in merged:  # and after the merged zooms
                    low = max(low, merged[name][1] + 1)
                if name in long_lines:  # whole lines below the first long zoom only
                    high = long_lines[name][0] - 1
                if (low, high) != self._layer_zoom_range(layer):
                    self._zoom_override[name] = (low, high)
                if low <= high:
                    plain.append(layer)
            self._build_vrt(vrt, plain)
            self._write_layer_conf(conf, plain)
            groups.append((key, target, vrt, conf, members, owner, cuts, plain, long_lines, small,
                           buffer, simplification, merged))
            parts.append(target)
        if self.feedback is not None and self.cache is not None:
            self.feedback.pushInfo(f"   Tiles: {len(parts) - len(groups)} of {len(parts)} layers "
                                   "reused from earlier exports, " f"{len(groups)} to generate")
        # A layer's tiles in several pieces (bands of zoom levels) when it alone
        # would keep one core busy after the others are done.
        cpu = self._cpu_num()
        target_cost = sum(self._job_cost(g[7]) for g in groups) / max(1, cpu) / 2
        jobs = []  # (group index, piece file, command, cost, owner)
        for index, (key, target, vrt, conf, members, owner, cuts, plain, long_lines, small,
                    buffer, simplification, merged) in enumerate(groups):
            filtered = self._filtered_jobs(index, target, members, cuts, owner, buffer, simplification)
            filtered += self._long_line_jobs(index, target, members, long_lines, small, owner,
                                             buffer, simplification)
            filtered += self._merged_jobs(index, target, members, merged, owner, buffer, simplification)
            jobs += filtered
            if not plain:
                continue  # every zoom of every dataset in the jobs above
            members = plain
            pieces = self._pieces(members, target_cost) if cpu > 1 else [(min_zoom, max_zoom, 0.0)]
            if filtered:  # merged with them: not the group's file itself
                target = f"{target[:-8]}_all.mbtiles"
            if len(pieces) == 1:
                jobs.append((index, target, self._ogr2ogr_command(vrt, target, min_zoom, max_zoom, conf,
                                                                  buffer=buffer,
                                                                  simplification=simplification),
                             pieces[0][2] or self._job_cost(members), owner))
                continue
            number = 0
            for low, high, cost in pieces:
                # The datasets of the band, their zooms cut to it. The writer
                # simplifies a dataset's last CONF zoom as its highest: those
                # that end in the band apart from those that go on above it.
                inside = [m for m in members if self._layer_zoom_range(m)[0] <= high
                          and self._layer_zoom_range(m)[1] >= low]
                ending = [m for m in inside if self._layer_zoom_range(m)[1] <= high]
                going_on = [m for m in inside if self._layer_zoom_range(m)[1] > high]
                for part, top in ((ending, _SIMPLIFICATION_MAX_ZOOM), (going_on, simplification)):
                    if not part:
                        continue
                    piece = f"{target[:-8]}_{number:02d}.mbtiles"
                    number += 1
                    piece_vrt, piece_conf = piece[:-8] + ".vrt", piece[:-8] + ".json"
                    self._build_vrt(piece_vrt, part)
                    self._write_layer_conf(piece_conf, part, (low, high))
                    command = self._ogr2ogr_command(piece_vrt, piece, low, high, piece_conf,
                                                    top_simplification=top, buffer=buffer,
                                                    simplification=simplification)
                    jobs.append((index, piece, command, cost * len(part) / max(1, len(inside)), owner))
        try:
            self._run_parallel([job[2] for job in jobs], [job[3] for job in jobs], [job[4] for job in jobs])
            for index, (key, target, *_rest) in enumerate(groups):
                # (A job may write no file: a merged copy without features.)
                pieces = [job for job in jobs if job[0] == index and os.path.exists(job[1])]
                if len(pieces) > 1 or (pieces and pieces[0][1] != target):  # one piece: as it is
                    self._check_cancelled()
                    merge_mbtiles([job[1] for job in pieces], target, min_zoom, max_zoom, workers=cpu)
            self._check_cancelled()
            # A group without a single tile has no file: left out (not cached).
            stored = {target: self.cache.put_tiles(key, target)
                      for key, target, *_ in groups if key and self.cache is not None
                      and os.path.exists(target)}
            merge_mbtiles([stored.get(path, path) for path in parts
                           if path in stored or os.path.exists(path)], output, min_zoom, max_zoom,
                          workers=cpu)
        finally:
            # Kept in the cache; not needed here (nor the pieces of a failed
            # or cancelled run).
            shutil.rmtree(work, ignore_errors=True)

    def _filtered_jobs(self, index: int, target: str, members: List[QgsVectorLayer],
                       cuts: Dict[str, Tuple[int, int, float]], owner: str, buffer: int,
                       simplification: float) -> list:
        """Jobs (as _generate_per_layer's) making the tiles of the zooms of
        ``cuts``: one zoom each, the datasets' features under
        ``min_feature_px`` there left out. Each zoom is simplified as one
        below the datasets' last (not SIMPLIFICATION_MAX_ZOOM)."""
        jobs = []
        by_name = {self._layer_name(m): m for m in members}
        zooms = sorted({z for low, last, _ in cuts.values() for z in range(low, last + 1)})
        for zoom in zooms:
            limit = self._min_size(zoom)
            part = [by_name[name] for name, (low, last, largest) in cuts.items()
                    if low <= zoom <= last and largest >= limit]
            if not part:
                continue  # every feature under the limit: none in these tiles
            piece = f"{target[:-8]}_z{zoom:02d}.mbtiles"
            piece_vrt, piece_conf = piece[:-8] + ".vrt", piece[:-8] + ".json"
            self._build_vrt(piece_vrt, part, min_size=limit)
            with open(piece_conf, "w", encoding="utf-8") as handle:
                json.dump({self._layer_name(m): {"minzoom": zoom, "maxzoom": zoom} for m in part}, handle)
            command = self._ogr2ogr_command(piece_vrt, piece, zoom, zoom, piece_conf,
                                            top_simplification=simplification, buffer=buffer,
                                            simplification=simplification)
            cost = sum(self._job_cost([m]) for m in part) / max(1, len(zooms))
            jobs.append((index, piece, command, cost, owner))
        return jobs

    _DATASET = re.compile(r"t(\d+)d\d+r\d+g(\d+)c(\d+)")  # (2 digits, more when needed)

    def _merged_members(self, owner: str, members: List[QgsVectorLayer]) -> Dict[str, Tuple[int, int, bool]]:
        """{dataset: (first, last merged zoom, outline)} of a merged layer's
        fills and their outlines (renderer datasets of polygons), at the
        zooms below its LayerConfig.zoomed_out_below."""
        below = self.merged.get(owner)
        if below is None:
            return {}
        out = {}
        for layer in members:
            name = self._layer_name(layer)
            match = self._DATASET.search(name)
            if not match or name.endswith(("_vp", "_vl")) or name in self.exact_datasets:
                continue
            kind, geometry, target = (int(match.group(i)) for i in (1, 2, 3))
            if kind != 0 or geometry != 2 or target not in (1, 2):
                continue  # labels, points, lines: as they are
            low, high = self._layer_zoom_range(layer)
            last = min(high, below - 1)
            if last >= low:
                out[name] = (low, last, target == 1)
        return out

    def _merged_jobs(self, index: int, target: str, members: List[QgsVectorLayer],
                     merged: Dict[str, Tuple[int, int, bool]], owner: str, buffer: int,
                     simplification: float) -> list:
        """Jobs (as _generate_per_layer's) making the merged zooms' tiles: one
        zoom each, from the copies of merge_per_tile."""
        if not merged:
            return []
        by_name = {self._layer_name(m): m for m in members}
        copies: Dict[str, Dict[int, str]] = {}
        for number, (name, (low, last, outline)) in enumerate(sorted(merged.items())):
            source = by_name[name].source().split("|layername=")[0]
            outputs = {z: f"{target[:-8]}_m{number:02d}_z{z:02d}.gpkg" for z in range(low, last + 1)}
            written = merge_per_tile(source, self._table_of(source), outputs, outline,
                                     cancelled=lambda: self.feedback is not None and self.feedback.isCanceled())
            copies[name] = {z: path for z, path in outputs.items() if written.get(z)}
        jobs = []
        for zoom in sorted({z for paths in copies.values() for z in paths}):
            names = [name for name, paths in copies.items() if zoom in paths]
            piece = f"{target[:-8]}_mz{zoom:02d}.mbtiles"
            piece_vrt, piece_conf = piece[:-8] + ".vrt", piece[:-8] + ".json"
            root = ET.Element("OGRVRTDataSource")
            conf, cost = {}, 0.0
            for name in names:
                source = by_name[name].source().split("|layername=")[0]
                table = self._table_of(source)
                node = ET.SubElement(root, "OGRVRTLayer", name=name)
                ET.SubElement(node, "SrcDataSource").text = copies[name][zoom]
                if table and table != name:
                    ET.SubElement(node, "SrcLayer").text = table
                ET.SubElement(node, "LayerSRS").text = f"EPSG:{_EPSG_CRS}"
                ET.SubElement(node, "GeometryType").text = "wkbUnknown"
                conf[name] = {"minzoom": zoom, "maxzoom": zoom}
                cost += os.path.getsize(copies[name][zoom]) + _TILE_COST * self._tiles_at(zoom)
            ET.ElementTree(root).write(piece_vrt, encoding="utf-8", xml_declaration=True)
            with open(piece_conf, "w", encoding="utf-8") as handle:
                json.dump(conf, handle)
            last = all(self._layer_zoom_range(by_name[name])[1] == zoom for name in names)
            command = self._ogr2ogr_command(
                piece_vrt, piece, zoom, zoom, piece_conf,
                top_simplification=_SIMPLIFICATION_MAX_ZOOM if last else simplification,
                buffer=buffer, simplification=simplification)
            jobs.append((index, piece, command, cost, owner))
        if jobs and self.feedback is not None:
            self.feedback.pushInfo("   Merged per tile below zoom {}: {}".format(
                self.merged.get(owner), ", ".join(sorted(copies))))
        return jobs

    def _long_lines(self, members: List[QgsVectorLayer]) -> Dict[str, Tuple[int, int]]:
        """{dataset: (first zoom tiled from grid-cut copies, last zoom)} of
        the line datasets whose features' boxes span far more tiles than the
        lines pass (long_line_zoom)."""
        out: Dict[str, Tuple[int, int]] = {}
        for layer in members:
            low, high = self._layer_zoom_range(layer)
            source = layer.source().split("|layername=")[0]
            try:
                first = long_line_zoom(source, self._table_of(source), low, high)
            except RuntimeError:  # unreadable (GDAL exceptions on): tiled as it is
                first = None
            if first is not None:
                out[self._layer_name(layer)] = (first, high)
        return out

    def _long_line_jobs(self, index: int, target: str, members: List[QgsVectorLayer],
                        long_lines: Dict[str, Tuple[int, int]],
                        small: Dict[str, Tuple[int, int, float]], owner: str, buffer: int,
                        simplification: float) -> list:
        """Jobs (as _generate_per_layer's) making the tiles of the long line
        datasets from their first long zoom on: one zoom each, from a copy
        cut along the tile grid _LONG_LINE_GRID_UP zooms up (grid_cut_lines),
        the features under ``min_feature_px`` left out where ``small`` says
        so (as _filtered_jobs)."""
        if not long_lines:
            return []
        jobs = []
        by_name = {self._layer_name(m): m for m in members}
        zooms = sorted({z for first, last in long_lines.values() for z in range(first, last + 1)})
        for zoom in zooms:
            names = [name for name, (first, last) in long_lines.items() if first <= zoom <= last]
            piece = f"{target[:-8]}_l{zoom:02d}.mbtiles"
            piece_vrt, piece_conf = piece[:-8] + ".vrt", piece[:-8] + ".json"
            root = ET.Element("OGRVRTDataSource")
            conf, cost = {}, 0.0
            for number, name in enumerate(names):
                source = by_name[name].source().split("|layername=")[0]
                table = self._table_of(source)
                cut = f"{piece[:-8]}_{number:02d}.gpkg"
                limit = 0.0
                if name in small and small[name][0] <= zoom <= small[name][1]:
                    limit = self._min_size(zoom)
                written = grid_cut_lines(source, table, cut, zoom, limit,
                                         cancelled=lambda: self.feedback is not None
                                         and self.feedback.isCanceled())
                if not written:
                    continue
                node = ET.SubElement(root, "OGRVRTLayer", name=name)
                ET.SubElement(node, "SrcDataSource").text = cut
                if table and table != name:
                    ET.SubElement(node, "SrcLayer").text = table
                ET.SubElement(node, "LayerSRS").text = f"EPSG:{_EPSG_CRS}"
                ET.SubElement(node, "GeometryType").text = "wkbUnknown"
                conf[name] = {"minzoom": zoom, "maxzoom": zoom}
                cost += os.path.getsize(cut) + _TILE_COST * written
            if not conf:
                continue
            ET.ElementTree(root).write(piece_vrt, encoding="utf-8", xml_declaration=True)
            with open(piece_conf, "w", encoding="utf-8") as handle:
                json.dump(conf, handle)
            # Simplified as the zoom is in the whole run: the datasets' last
            # zoom less (SIMPLIFICATION_MAX_ZOOM), the others as below it.
            last = all(long_lines[name][1] == zoom for name in conf)
            command = self._ogr2ogr_command(
                piece_vrt, piece, zoom, zoom, piece_conf,
                top_simplification=_SIMPLIFICATION_MAX_ZOOM if last else simplification,
                buffer=buffer, simplification=simplification)
            jobs.append((index, piece, command, cost, owner))
        if jobs and self.feedback is not None:
            self.feedback.pushInfo("   Long lines tiled in pieces from zoom {}: {}".format(
                min(first for first, _ in long_lines.values()), ", ".join(sorted(long_lines))))
        return jobs

    def _check_cancelled(self) -> None:
        if self.feedback is not None and self.feedback.isCanceled():
            raise TilesGenerationCancelled("Tile generation cancelled")

    def _zoom_costs(self, members: List[QgsVectorLayer]) -> Dict[int, float]:
        """TileProgress cost of each zoom level of a layer's datasets."""
        costs: Dict[int, float] = {}
        for layer in members:
            try:
                size = os.path.getsize(layer.source().split("|")[0])
            except OSError:
                size = 0
            low, high = self._layer_zoom_range(layer)
            for zoom in range(low, high + 1):
                costs[zoom] = costs.get(zoom, 0.0) + size + _TILE_COST * self._tiles_at(zoom)
        return costs

    def _pieces(self, members: List[QgsVectorLayer], target: float) -> List[Tuple[int, int, float]]:
        """[(min zoom, max zoom, cost)]: one layer's tile job in bands of zoom
        levels of about ``target`` cost, the highest zooms (most tiles)
        first. The MVT writer makes each zoom level on its own: a band's
        tiles are those of one run with its CONF cut to the band (datasets
        that end in the band apart from those that go on: _generate_per_layer).
        Not cut into areas: a spatial filter reads the features in another
        order."""
        costs = self._zoom_costs(members)
        whole = sum(costs.values())
        if not costs or whole <= 1.2 * target:
            return [(self._zooms[0], self._zooms[1], whole)]
        bands, band = [], []
        for zoom in sorted(costs, reverse=True):
            if band and sum(costs[z] for z in band) + costs[zoom] > target:
                bands.append(band)
                band = []
            band.append(zoom)
        bands.append(band)
        return [(min(band), max(band), sum(costs[z] for z in band)) for band in bands]

    def _run_parallel(self, commands: List[List[str]], costs: Optional[List[float]] = None,
                      labels: Optional[List[str]] = None):
        """Run ogr2ogr commands, several at a time, polled from this (main)
        thread so QGIS stays responsive and Cancel works. The biggest jobs
        (``costs``) start first, so none of them is left running alone at
        the end; the progress bar follows TileProgress (ogr2ogr -progress).
        A job that fails is run once more before the export fails."""
        if not commands:
            self._report(1.0)
            return
        costs = list(costs) if costs and len(costs) == len(commands) else [1.0] * len(commands)
        tracker = TileProgress(costs, reporting=True)
        cpu = self._cpu_num()
        slots = max(1, min(len(commands), cpu))
        env = os.environ.copy()
        env["GDAL_NUM_THREADS"] = str(max(1, cpu // slots))
        waiting = sorted(range(len(commands)), key=lambda j: -costs[j])
        running: Dict[int, Tuple[subprocess.Popen, _OutputReader, _OutputReader]] = {}
        # A layer's tiles may be made in several pieces: count layers, not pieces.
        owners = list(labels) if labels and len(labels) == len(commands) else list(range(len(commands)))
        retried = set()
        free = available_memory()
        budget = free // 2 if free else 0
        in_memory: Dict[int, int] = {}  # running in memory: bytes it may take
        started = last_message = last_report = time.monotonic()
        try:
            while waiting or running:
                while waiting and len(running) < slots:
                    job = waiting.pop(0)
                    extra = []
                    need = _MEMORY_DB_FACTOR * vrt_input_bytes(commands[job][4]) if budget else 0
                    if need and job not in retried and need <= budget - sum(in_memory.values()):
                        in_memory[job] = need
                        extra = ["-dsco", f"TEMPORARY_DB=/vsimem/q2vt_{job}.db"]
                    proc = subprocess.Popen(
                        commands[job] + extra + ["-progress"], env=env, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, text=True, errors="replace", **self._popen_options())
                    readers = (_OutputReader(proc.stdout, True), _OutputReader(proc.stderr, False))
                    for reader in readers:
                        reader.start()
                    running[job] = (proc, *readers)
                    tracker.start(job, time.monotonic())
                for job, (proc, progress, errors) in [(j, r) for j, r in running.items()
                                                      if r[0].poll() is not None]:
                    del running[job]
                    in_memory.pop(job, None)
                    progress.join(timeout=5)
                    errors.join(timeout=5)
                    proc.stdout.close()
                    proc.stderr.close()
                    now = time.monotonic()
                    if labels and job < len(labels):
                        self.layer_seconds[labels[job]] = \
                            self.layer_seconds.get(labels[job], 0.0) + now - tracker.started[job]
                    if proc.returncode != 0 and job not in retried:
                        # Once seen: ogr2ogr stopped on a dataset that it tiled
                        # in every other run (GEOS "NaN/Inf numbers"); run once more.
                        retried.add(job)
                        first = next((line for line in errors.text.splitlines() if line.strip()), "")
                        if self.feedback is not None:
                            self.feedback.pushInfo(f"   A tile job stopped with an error ({first[:200]}); "
                                                   "running it once more (its work database on disk).")
                        if os.path.exists(commands[job][3]):
                            os.remove(commands[job][3])  # its partial tiles
                        tracker.forget(job)
                        waiting.insert(0, job)
                        continue
                    tracker.finish(job, now)
                    if labels and job < len(labels):
                        self.layer_pieces[labels[job]] = self.layer_pieces.get(labels[job], 0) + 1
                    if proc.returncode != 0:
                        error_msg = f"ogr2ogr failed.\nError: {errors.text}"
                        if self.feedback:
                            self.feedback.reportError(error_msg)
                        raise RuntimeError(error_msg)
                if self.feedback is not None and self.feedback.isCanceled():
                    raise TilesGenerationCancelled("Tile generation cancelled")
                now = time.monotonic()
                for job, (_proc, progress, _errors) in running.items():
                    if progress.fraction > 0:
                        tracker.report(job, progress.fraction, now)
                if now - last_report > 1:
                    last_report = now
                    self._report(tracker.fraction(now))
                if self.feedback is not None and now - last_message > 15:
                    last_message = now
                    left = len({owners[j] for j in itertools.chain(waiting, running)})
                    self.feedback.pushInfo(
                        f"   Still generating tiles ({(now - started) / 60:.1f} minutes, "
                        f"{left} of {len(set(owners))} layers left, "
                        f"about {100 * tracker.fraction(now):.0f}% done)...")
                time.sleep(0.05)
                main_thread.keep_responsive()
            self._report(1.0)
        finally:
            for proc, *readers in running.values():
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                for reader in readers:
                    reader.join(timeout=5)
                proc.stdout.close()
                proc.stderr.close()

    def _prune_tiles_outside_extent(self, output: str):
        """Drop tiles that do not intersect the requested extent.

        Source features are selected with a symbol-reach buffer so symbols
        of features just outside the extent still reach into it; the tiles
        created only for that buffer ring are removed again.
        """
        extent = self.extent
        if extent is None or extent.isEmpty() or not os.path.exists(output):
            return
        half = 20037508.342789244
        with contextlib.closing(sqlite3.connect(output)) as conn, conn:
            zooms = [row[0] for row in conn.execute("SELECT DISTINCT zoom_level FROM tiles")]
            for zoom in zooms:
                n = 2 ** zoom
                size = 2 * half / n

                def column(x):
                    return min(n - 1, max(0, int(math.floor((x + half) / size))))
                x0, x1 = column(extent.xMinimum()), column(extent.xMaximum())
                # XYZ rows grow southwards; MBTiles stores TMS rows (from the south).
                tms = sorted((n - 1 - column(-extent.yMinimum()),
                              n - 1 - column(-extent.yMaximum())))
                conn.execute(
                    "DELETE FROM tiles WHERE zoom_level = ? AND (tile_column < ? OR "
                    "tile_column > ? OR tile_row < ? OR tile_row > ?)",
                    (zoom, x0, x1, tms[0], tms[1]))
            conn.commit()
        with contextlib.closing(sqlite3.connect(output)) as conn, conn:
            conn.execute("VACUUM")

    # --- Helpers ---

    def _prepare_output_paths(self) -> Tuple[str, str]:
        output = join(self.output_dir, "tiles.mbtiles")
        return output, mbtiles_uri(output)

    def _layer_zoom_range(self, layer: QgsVectorLayer) -> Tuple[int, int]:
        name = self._layer_name(layer)
        override = getattr(self, "_zoom_override", {})  # set in __init__
        if name in override:
            return override[name]
        if name in self.layer_zooms:
            low, high = self.layer_zooms[name]
        else:
            low, high = self._parse_layer_zoom(layer, "o"), self._parse_layer_zoom(layer, "i")
        low = max(0, min(_MVT_MAX_ZOOM, int(low)))
        return low, max(low, min(_MVT_MAX_ZOOM, int(high)))

    def _parse_layer_zoom(self, layer: QgsVectorLayer, marker: str) -> int:
        """Legacy fallback: zoom level encoded in the dataset filename."""
        match = re.search(f"{marker}(\\d+)", self._layer_name(layer))
        return int(match.group(1)) if match else 0

    def _get_global_min_zoom(self) -> int:
        return min((self._layer_zoom_range(layer)[0] for layer in self.layers), default=0)

    def _get_global_max_zoom(self) -> int:
        return max((self._layer_zoom_range(layer)[1] for layer in self.layers), default=14)


def _tile_layers(data: bytes) -> bytes:
    """An MVT tile's bytes (gzip or raw) without compression."""
    return zlib.decompress(data, 47) if data[:2] == b"\x1f\x8b" else data


def _tile_rows(path: str):
    """A part's tiles in (zoom, column, row) order (its UNIQUE index)."""
    part = sqlite3.connect(path)
    try:
        yield from part.execute("SELECT zoom_level, tile_column, tile_row, tile_data FROM tiles "
                                "ORDER BY zoom_level, tile_column, tile_row")
    finally:
        part.close()


def _merged_tile(chunks: List[bytes]) -> bytes:
    """One tile of the parts' tiles at the same address (their layers, in
    the parts' order); a tile of one part as it is when already gzipped."""
    if len(chunks) == 1 and chunks[0][:2] == b"\x1f\x8b":
        return chunks[0]
    return _gzip(b"".join(_tile_layers(data) for data in chunks))


def _quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


# --- merged zoomed out (LayerConfig.zoomed_out "merged") --------------------
# Below a layer's chosen zoom, each of its fill and outline datasets is tiled
# from copies whose features of one style - equal values in every field the
# tiles keep, but for ids, keys and label fields - are joined per tile of the
# zoom: a dense layer (parcels) becomes a few shapes a tile. The pieces join
# whole features (grouped by the tile of their middle), so their edges are
# the features' own: no new seams at tile edges.
_MERGE_IDS = {"q2vt_orig_id", "q2vt_feature_key", "q2vt_part", "fid", "ogc_fid"}


def _merge_key_fields(definition) -> List[int]:
    """Indexes of the fields a merged feature keeps (and is grouped by)."""
    keep = []
    for index in range(definition.GetFieldCount()):
        name = definition.GetFieldDefn(index).GetName().lower()
        if name in _MERGE_IDS or name.startswith("q2vt_label") or name.startswith("q2vt_vertex"):
            continue
        keep.append(index)
    return keep


def _as_polygons(geometry, outline: bool):
    """A fill's polygon(s), or the polygon(s) an outline's closed rings
    enclose (None when they do not close: kept as lines)."""
    if geometry is None or geometry.IsEmpty():
        return None
    if not outline:
        polygon = geometry
    else:
        try:
            polygon = ogr.BuildPolygonFromEdges(geometry, bBestEffort=1, bAutoClose=0)
        except RuntimeError:
            return None
        if polygon is None or polygon.IsEmpty() or abs(polygon.GetArea()) <= 0:
            return None
    if not polygon.IsValid():
        try:
            polygon = polygon.MakeValid()
        except (RuntimeError, AttributeError):
            polygon = polygon.Buffer(0)
    return polygon


def _union(geometries):
    collection = ogr.Geometry(ogr.wkbMultiPolygon)
    for geometry in geometries:
        flat = ogr.GT_Flatten(geometry.GetGeometryType())
        if flat == ogr.wkbPolygon:
            collection.AddGeometry(geometry)
        elif flat in (ogr.wkbMultiPolygon, ogr.wkbGeometryCollection):
            for index in range(geometry.GetGeometryCount()):
                part = geometry.GetGeometryRef(index)
                if ogr.GT_Flatten(part.GetGeometryType()) == ogr.wkbPolygon:
                    collection.AddGeometry(part)
    if collection.GetGeometryCount() == 0:
        return None
    try:
        return collection.UnionCascaded()
    except RuntimeError:
        return collection.Buffer(0)


@gdal_guard.shared_section
def merge_per_tile(path: str, table: Optional[str], outputs: Dict[int, str], outline: bool,
                   cancelled=None) -> Dict[int, int]:
    """Write, for each zoom of ``outputs`` ({zoom: GeoPackage path}), the
    dataset ``path`` with its features of one style merged per tile of
    that zoom (outlines: the merged shapes' boundaries; rings that do not
    close stay as they are). The highest zoom merges the features, each
    lower one the pieces of the zoom above. Returns {zoom: features written}."""
    source = _open_gpkg(path)
    layer = source.GetLayerByName(table) if table else source.GetLayer(0)
    definition = layer.GetLayerDefn()
    keep = _merge_key_fields(definition)
    srs = layer.GetSpatialRef()
    top = max(outputs)
    cell = _tile_size(top)
    groups: Dict[tuple, list] = collections.defaultdict(list)
    loose = []  # (key, geometry) of outlines that do not close
    for count, feature in enumerate(layer):
        if cancelled is not None and count % 2000 == 0 and cancelled():
            raise TilesGenerationCancelled("Tile generation cancelled")
        geometry = feature.GetGeometryRef()
        if geometry is None or geometry.IsEmpty():
            continue
        key = tuple(feature.GetField(i) for i in keep)
        polygon = _as_polygons(geometry, outline)
        if polygon is None:
            if outline:
                loose.append((key, geometry.Clone()))
            continue
        x0, x1, y0, y1 = polygon.GetEnvelope()
        cx = math.floor(((x0 + x1) / 2 + WORLD_HALF) / cell)
        cy = math.floor(((y0 + y1) / 2 + WORLD_HALF) / cell)
        groups[(key, cx, cy)].append(polygon.Clone())
    written = {}
    pieces = {group: _union(members) for group, members in groups.items()}
    for zoom in range(top, min(outputs) - 1, -1):
        if zoom != top:
            parents: Dict[tuple, list] = collections.defaultdict(list)
            for (key, cx, cy), geometry in pieces.items():
                if geometry is not None:
                    parents[(key, cx // 2, cy // 2)].append(geometry)
            pieces = {group: _union(members) for group, members in parents.items()}
        if zoom not in outputs:
            continue
        driver = ogr.GetDriverByName("GPKG")
        if os.path.exists(outputs[zoom]):
            driver.DeleteDataSource(outputs[zoom])
        target = driver.CreateDataSource(outputs[zoom])
        out = target.CreateLayer(table or layer.GetName(), srs,
                                 ogr.wkbMultiLineString if outline else ogr.wkbMultiPolygon,
                                 ["SPATIAL_INDEX=NO"])
        for index in keep:
            out.CreateField(definition.GetFieldDefn(index))
        out_definition = out.GetLayerDefn()
        out.StartTransaction()
        number = 0
        shapes = [(key, geometry, True) for (key, _cx, _cy), geometry in pieces.items()]
        shapes += [(key, geometry, False) for key, geometry in loose]
        for key, geometry, merged in shapes:
            if geometry is None or geometry.IsEmpty():
                continue
            shape = geometry.Boundary() if outline and merged else geometry
            if outline:
                shape = ogr.ForceToMultiLineString(shape)
            else:
                shape = ogr.ForceToMultiPolygon(shape)
            copy = ogr.Feature(out_definition)
            for position, value in enumerate(key):
                if value is not None:
                    copy.SetField(position, value)
            copy.SetGeometry(shape)
            out.CreateFeature(copy)
            number += 1
        out.CommitTransaction()
        target = None
        written[zoom] = number
    return written


# --- long lines -----------------------------------------------------------
# GDAL's MVT writer cuts each feature at every tile of its bounding box at
# every zoom (OGRMVTWriterDataset::PreGenerateForTile, a GEOS intersection
# of the whole geometry each time): a long diagonal line (a sea route, the
# outline of a large polygon) has hundreds of millions of zoom-16 tiles in
# its box, nearly all empty. At those zooms the lines are tiled from a copy
# cut along the tile grid two zooms up: each piece's box spans a few tiles.
# The cuts are tile edges at the zoom tiled, where MapLibre clips each
# tile's drawing anyway: the map looks the same.
WORLD_HALF = 20037508.342789244
# A zoom whose features' boxes cover this many tiles in all, and many
# times the tiles the lines pass through, is tiled from the cut copy.
_LONG_LINE_TILES = 200_000
_LONG_LINE_WASTE = 4
# The grid of the cut copy: this many zooms above the zoom tiled.
_LONG_LINE_GRID_UP = 2


def _tile_size(zoom: int) -> float:
    return 2 * WORLD_HALF / (1 << zoom)


@gdal_guard.shared_section
def long_line_zoom(path: str, table: Optional[str], low: int, high: int) -> Optional[int]:
    """The first zoom in [low, high] at which the line dataset ``path`` is
    to be tiled from a grid-cut copy (see above), or None."""
    source = _open_gpkg(path)
    if source is None:
        return None
    layer = source.GetLayerByName(table) if table else source.GetLayer(0)
    if layer is None or ogr.GT_Flatten(layer.GetGeomType()) not in (
            ogr.wkbLineString, ogr.wkbMultiLineString, ogr.wkbUnknown):
        return None
    layer.SetIgnoredFields([layer.GetLayerDefn().GetFieldDefn(i).GetName()
                            for i in range(layer.GetLayerDefn().GetFieldCount())])
    boxes, length = [], 0.0
    for feature in layer:
        geometry = feature.GetGeometryRef()
        if geometry is None or ogr.GT_Flatten(geometry.GetGeometryType()) not in (
                ogr.wkbLineString, ogr.wkbMultiLineString):
            continue
        min_x, max_x, min_y, max_y = geometry.GetEnvelope()
        boxes.append((max_x - min_x, max_y - min_y))
        length += geometry.Length()
    if not boxes:
        return None
    for zoom in range(low, high + 1):
        size = _tile_size(zoom)
        in_boxes = sum((w / size + 2) * (h / size + 2) for w, h in boxes)
        passed = length / size + 2 * len(boxes)
        if in_boxes > _LONG_LINE_TILES and in_boxes > _LONG_LINE_WASTE * passed:
            return zoom
    return None


def _cut_on_grid(points: List[Tuple[float, float]], size: float) -> List[List[Tuple[float, float]]]:
    """A line (its vertices) cut where it crosses the grid of cells
    ``size`` wide (from the Web Mercator origin): each piece in one cell."""
    pieces, piece = [], [points[0]]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        dx, dy = x1 - x0, y1 - y0
        crossings = set()
        for start, delta in ((x0, dx), (y0, dy)):
            if delta == 0:
                continue
            first = math.floor((min(start, start + delta) + WORLD_HALF) / size) + 1
            last = math.ceil((max(start, start + delta) + WORLD_HALF) / size) - 1
            for line in range(first, last + 1):
                t = (line * size - WORLD_HALF - start) / delta
                if 0 < t < 1:
                    crossings.add(t)
        for t in sorted(crossings):
            point = (x0 + t * dx, y0 + t * dy)
            piece.append(point)
            pieces.append(piece)
            piece = [point]
        piece.append((x1, y1))
    pieces.append(piece)
    return [p for p in pieces if len(p) > 1 and any(q != p[0] for q in p[1:])]


@gdal_guard.shared_section
def grid_cut_lines(path: str, table: Optional[str], output: str, zoom: int,
                   min_size: float = 0.0, cancelled=None) -> int:
    """Write the lines of ``path`` cut along the tile grid
    _LONG_LINE_GRID_UP zooms above ``zoom`` into the GeoPackage ``output``
    (same table name, fields and values: one feature per piece). With
    ``min_size`` (metres) features whose whole box is smaller are left out,
    as the zoom's tiles leave them out (_filtered_jobs). Returns the
    pieces written. ``cancelled()``: True stops (TilesGenerationCancelled)."""
    size = _tile_size(max(0, zoom - _LONG_LINE_GRID_UP))
    source = _open_gpkg(path)
    layer = source.GetLayerByName(table) if table else source.GetLayer(0)
    definition = layer.GetLayerDefn()
    driver = ogr.GetDriverByName("GPKG")
    if os.path.exists(output):
        driver.DeleteDataSource(output)
    target = driver.CreateDataSource(output)
    out = target.CreateLayer(table or layer.GetName(), layer.GetSpatialRef(), ogr.wkbLineString,
                             ["SPATIAL_INDEX=NO"])
    for index in range(definition.GetFieldCount()):
        out.CreateField(definition.GetFieldDefn(index))
    out_definition = out.GetLayerDefn()
    written = 0
    out.StartTransaction()
    for count, feature in enumerate(layer):
        if cancelled is not None and count % 2000 == 0 and cancelled():
            out.RollbackTransaction()
            target = None
            raise TilesGenerationCancelled("Tile generation cancelled")
        geometry = feature.GetGeometryRef()
        if geometry is None:
            continue
        if min_size > 0:
            min_x, max_x, min_y, max_y = geometry.GetEnvelope()
            if max(max_x - min_x, max_y - min_y) < min_size:
                continue
        flat = ogr.GT_Flatten(geometry.GetGeometryType())
        parts = [geometry] if flat == ogr.wkbLineString else \
            [geometry.GetGeometryRef(i) for i in range(geometry.GetGeometryCount())] \
            if flat == ogr.wkbMultiLineString else []
        for part in parts:
            points = [(x, y) for x, y, *_ in part.GetPoints() or []]
            if len(points) < 2:
                continue
            for piece in _cut_on_grid(points, size):
                line = ogr.Geometry(ogr.wkbLineString)
                for x, y in piece:
                    line.AddPoint_2D(x, y)
                copy = ogr.Feature(out_definition)
                copy.SetFrom(feature)  # every field, NULLs too
                copy.SetGeometry(line)
                out.CreateFeature(copy)
                written += 1
    out.CommitTransaction()
    target = None
    return written


def merge_mbtiles(parts: List[str], output: str, min_zoom: int, max_zoom: int,
                  workers: int = 1) -> None:
    """One MBTiles of several MVT MBTiles with distinct layers: a tile's
    layers are concatenated (an MVT tile is a list of layer messages, so the
    concatenation of tiles is a tile with all their layers) and gzipped.

    The parts are read side by side in tile order (a few tiles in memory at
    a time, not all of them), and the tiles of several parts are gzipped
    ``workers`` at a time (zlib runs outside the GIL)."""
    if os.path.exists(output):
        os.remove(output)
    vector_layers, stats, bounds = [], [], None
    with contextlib.closing(sqlite3.connect(output)) as out, out:
        out.execute("CREATE TABLE metadata (name text, value text)")
        out.execute("CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, "
                    "tile_data blob, UNIQUE (zoom_level, tile_column, tile_row))")
        if len(parts) == 1:  # nothing to merge: copy as is
            out.execute("ATTACH DATABASE ? AS part", (parts[0],))
            out.execute("INSERT INTO tiles SELECT zoom_level, tile_column, tile_row, tile_data FROM part.tiles")
            out.execute("INSERT INTO metadata SELECT name, value FROM part.metadata")
            out.commit()
            out.execute("DETACH DATABASE part")
            return
        for path in parts:
            with contextlib.closing(sqlite3.connect(path)) as part, part:
                meta = dict(part.execute("SELECT name, value FROM metadata"))
            try:
                info = json.loads(meta.get("json") or "{}")
            except ValueError:
                info = {}
            vector_layers += info.get("vector_layers") or []
            stats += (info.get("tilestats") or {}).get("layers") or []
            try:
                west, south, east, north = (float(v) for v in meta["bounds"].split(","))
                bounds = [west, south, east, north] if bounds is None else [
                    min(bounds[0], west), min(bounds[1], south), max(bounds[2], east), max(bounds[3], north)]
            except (KeyError, ValueError):
                pass
        # heapq.merge is stable: tiles at the same address come in the parts' order.
        rows = heapq.merge(*(_tile_rows(path) for path in parts), key=lambda row: row[:3])
        tiles = ((address, [row[3] for row in group])
                 for address, group in itertools.groupby(rows, key=lambda row: row[:3]))
        with ThreadPoolExecutor(max(1, workers)) as pool:
            while True:
                batch = list(itertools.islice(tiles, 256))
                if not batch:
                    break
                data = pool.map(_merged_tile, [chunks for _, chunks in batch])
                out.executemany("INSERT INTO tiles VALUES (?, ?, ?, ?)",
                                ((z, x, y, blob) for ((z, x, y), _), blob in zip(batch, data)))
        vector_layers, stats = _unique_layers(vector_layers, "id"), _unique_layers(stats, "layer")
        bounds = bounds or [-180.0, -85.0511, 180.0, 85.0511]
        center = [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2, min_zoom]
        metadata = {
            "name": "tiles", "description": "", "version": "2", "minzoom": str(min_zoom),
            "maxzoom": str(max_zoom), "center": ",".join(f"{v:.7g}" if i < 2 else str(v)
                                                          for i, v in enumerate(center)),
            "bounds": ",".join(f"{v:.7f}" for v in bounds), "type": "overlay", "format": "pbf",
            "scheme": "tms",
            "json": json.dumps({"vector_layers": vector_layers,
                                "tilestats": {"layerCount": len(stats), "layers": stats}},
                               ensure_ascii=False),
        }
        out.executemany("INSERT INTO metadata VALUES (?, ?)", metadata.items())
        out.commit()


def _unique_layers(entries: List[dict], key: str) -> List[dict]:
    """Metadata entries of the same layer from several pieces (zoom bands,
    columns) as one: the widest zoom range, every field."""
    out: Dict[str, dict] = {}
    for entry in entries:
        name = entry.get(key) if isinstance(entry, dict) else None
        if name is None or name not in out:
            out[name if name is not None else f"#{len(out)}"] = dict(entry) if isinstance(entry, dict) else entry
            continue
        merged = out[name]
        for bound, pick in (("minzoom", min), ("maxzoom", max)):
            if bound in entry and bound in merged:
                merged[bound] = pick(merged[bound], entry[bound])
        if isinstance(entry.get("fields"), dict) and isinstance(merged.get("fields"), dict):
            merged["fields"] = dict(entry["fields"], **merged["fields"])
    return list(out.values())


def _gzip(data: bytes) -> bytes:
    compressor = zlib.compressobj(6, zlib.DEFLATED, 31)
    return compressor.compress(data) + compressor.flush()
