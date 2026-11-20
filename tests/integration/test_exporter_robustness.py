"""RulesExporter under conditions the other tests do not make: a world map
past the antimeridian, Cancel while the layers are read, a layer's own
"fid", the disk filling with step files, rounding at the end of a line,
file chains, long layer names, failing writes and file locks, measures
and repeated fields, keyword-like columns and threads."""

import ast
import glob
import math
import os
import random
import re
import types
import warnings

import pytest
from qgis.core import (QgsCoordinateReferenceSystem, QgsFeature, QgsField, QgsFields, QgsGeometry,
                       QgsMarkerSymbol, QgsProcessingFeedback, QgsRectangle, QgsRuleBasedRenderer,
                       QgsVectorFileWriter, QgsVectorLayer, QgsWkbTypes)
from qgis.PyQt.QtCore import QVariant

from q2vt_fixtures import reset_project, to_geopackage

WORLD = 20037508.342789244
HERE = os.path.dirname(os.path.abspath(__file__))


def _module():
    from q2vt_plugin.src.core import rules_exporter  # pylint: disable=import-error
    return rules_exporter


def _points(crs, rows, fields="&field=name:string", name="pts"):
    """A memory point layer: rows of (attributes, x, y)."""
    layer = QgsVectorLayer(f"Point?crs={crs}{fields}", name, "memory")
    for attributes, x, y in rows:
        feature = QgsFeature(layer.fields())
        feature.setAttributes(list(attributes))
        feature.setGeometry(QgsGeometry.fromWkt(f"POINT({x} {y})"))
        layer.dataProvider().addFeatures([feature])
    return layer


def _ruled(layer, expression=""):
    root = QgsRuleBasedRenderer.Rule(None)
    root.appendChild(QgsRuleBasedRenderer.Rule(QgsMarkerSymbol.createSimple({}), filterExp=expression))
    layer.setRenderer(QgsRuleBasedRenderer(root))
    return layer


def _exporter(tmp_path, layers, extent, include_fields=0, feedback=None, **kwargs):
    from q2vt_plugin.src.core.rules_flattener import RulesFlattener  # pylint: disable=import-error
    from fidelity.diagnostics import DiagnosticCollector
    reset_project(*layers)
    diags = DiagnosticCollector()
    rules = RulesFlattener(0, 16, str(tmp_path), QgsProcessingFeedback(), diags).flatten_all_rules()
    utils = tmp_path / "utils"
    utils.mkdir(exist_ok=True)
    return _module().RulesExporter(rules, extent, include_fields, 16, str(utils), 0,
                                   feedback or QgsProcessingFeedback(), diagnostics=diags, **kwargs)


def _rows(layers):
    return sorted(tuple(f[n] for n in ("name",) if f.fields().indexOf(n) >= 0) + (f.geometry().asPoint().x(),)
                  for layer in layers for f in layer.getFeatures())


def _bare(tmp_path):
    """An exporter for calling one worker function."""
    utils = tmp_path / "utils"
    utils.mkdir(exist_ok=True)
    return _module().RulesExporter([], QgsRectangle(-WORLD, -WORLD, WORLD, WORLD), 0, 16, str(utils), 0,
                                   QgsProcessingFeedback())


# -- antimeridian -------------------------------------------------------------

@pytest.mark.parametrize("extent,kept", [
    # A world grown by symbol reach.
    (QgsRectangle(-1.05 * WORLD, -1e6, 1.05 * WORLD, 1e6), ["chukotka", "fiji"]),
    # Pacific-centred (the tiles do not wrap: west of 180 degrees only).
    (QgsRectangle(0.5 * WORLD, -1e6, 1.3 * WORLD, 1e6), ["fiji"]),
])
def test_geographic_layer_keeps_features_at_the_antimeridian(plugin, tmp_path, extent, kept):
    """An extent past +-180 degrees came back narrower than the world in
    EPSG:4326 (the edges wrapped): Fiji and Chukotka left the tiles."""
    layer = _ruled(_points("EPSG:4326", [(["fiji"], 179.5, 0), (["chukotka"], -179.5, 0)]))
    exporter = _exporter(tmp_path, [layer], extent, include_fields=1)
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)  # (the long-id CRS constructor)
        layers, _rules = exporter.export()
    assert sorted(name for name, _x in _rows(layers)) == kept


# -- cancel -------------------------------------------------------------------

def test_cancel_while_reading_layers_returns_nothing(plugin, tmp_path, monkeypatch):
    """Cancel while a layer was read raised the exporter's private _Cancelled
    out of export() (Processing reported a crash)."""
    monkeypatch.setenv("Q2VT_WORKERS", "0")
    layer = to_geopackage(_ruled(_points("EPSG:3857", [(["a"], 0, 0)])), str(tmp_path / "a.gpkg"))
    feedback = QgsProcessingFeedback()
    exporter = _exporter(tmp_path, [_ruled(layer)], QgsRectangle(-1e3, -1e3, 1e3, 1e3), feedback=feedback)
    read = exporter._materialize_one  # pylint: disable=protected-access

    def cancel_then_read(src):
        feedback.cancel()
        return read(src)
    monkeypatch.setattr(exporter, "_materialize_one", cancel_then_read)
    assert exporter.export() == ([], [])


def test_cancel_during_rule_export_returns_nothing(plugin, tmp_path, monkeypatch):
    """Cancelled after the first dataset: the datasets done so far went on to
    the style as if they were the map, and the rules list lost the rest."""
    monkeypatch.setenv("Q2VT_WORKERS", "0")
    layer = to_geopackage(_points("EPSG:3857", [(["a"], 0, 0), (["b"], 10, 0)]), str(tmp_path / "ab.gpkg"))
    root = QgsRuleBasedRenderer.Rule(None)
    for name in ("a", "b"):
        root.appendChild(QgsRuleBasedRenderer.Rule(QgsMarkerSymbol.createSimple({}),
                                                   filterExp=f"\"name\" = '{name}'"))
    layer.setRenderer(QgsRuleBasedRenderer(root))
    feedback = QgsProcessingFeedback()
    exporter = _exporter(tmp_path, [layer], QgsRectangle(-1e3, -1e3, 1e3, 1e3), feedback=feedback)
    rules = list(exporter.flattened_rules)
    assert len({rule.output_dataset for rule in rules}) >= 2
    one = exporter._export_one_rule_group_recorded  # pylint: disable=protected-access

    def then_cancel(grp, source):
        try:
            return one(grp, source)
        finally:
            feedback.cancel()
    monkeypatch.setattr(exporter, "_export_one_rule_group_recorded", then_cancel)
    assert exporter.export() == ([], [])
    assert exporter.flattened_rules == rules


# -- the layer's own "fid" ----------------------------------------------------

@pytest.mark.parametrize("source", ["memory", "gpkg"])
def test_filters_read_the_layers_own_fid(plugin, tmp_path, source):
    """A temporary layer's "fid" (10, 20...) was renumbered 1..n in the copy,
    and every layer's by the split into single parts: a filter on it
    matched nothing."""
    layer = _points("EPSG:3857", [([fid, name], x, 0) for fid, name, x in
                                  ((10, "a", 0), (20, "b", 100), (30, "c", 200), (40, "d", 300))],
                    fields="&field=fid:integer&field=name:string")
    if source == "gpkg":
        layer = to_geopackage(layer, str(tmp_path / "fid.gpkg"))
        assert sorted(f["fid"] for f in layer.getFeatures()) == [10, 20, 30, 40]
    _ruled(layer, '"fid" = 20')
    layers, _rules = _exporter(tmp_path, [layer], QgsRectangle(-1e3, -1e3, 1e3, 1e3), include_fields=1).export()
    assert [name for name, _x in _rows(layers)] == ["b"]


def test_memory_layer_with_repeated_fid_values_still_exports(plugin, tmp_path):
    """A "fid" that cannot be a key (repeated, empty) is left out of the copy
    as before: written as the key it failed the GeoPackage steps."""
    layer = _ruled(_points("EPSG:3857", [([fid, name], x, 0) for fid, name, x in
                                         ((10, "a", 0), (10, "b", 100), (None, "c", 200))],
                           fields="&field=fid:integer&field=name:string"))
    layers, _rules = _exporter(tmp_path, [layer], QgsRectangle(-1e3, -1e3, 1e3, 1e3), include_fields=1).export()
    assert [name for name, _x in _rows(layers)] == ["a", "b", "c"]


# -- step files ---------------------------------------------------------------

_STEP_FILE = re.compile(r"^[a-z]+_[0-9a-f]{32}\.(gpkg|fgb)$")


@pytest.mark.parametrize("file_chains", [False, True])
def test_step_files_are_deleted_after_each_group(plugin, tmp_path, monkeypatch, file_chains):
    """Every step file stayed until the end of the export: with big layers
    (each step a file) tens of GB filled the disk."""
    monkeypatch.setenv("Q2VT_WORKERS", "0")
    if file_chains:
        monkeypatch.setenv("Q2VT_FILE_CHAINS", "1")
    else:
        monkeypatch.delenv("Q2VT_FILE_CHAINS", raising=False)
    monkeypatch.setattr(_module(), "_MEMORY_MAX_FEATURES", 0)  # every step writes a file
    layer = _points("EPSG:3857", [([name], x, 0) for name, x in (("a", 0), ("b", 10), ("c", 20))])
    root = QgsRuleBasedRenderer.Rule(None)
    for name in ("a", "b", "c"):
        root.appendChild(QgsRuleBasedRenderer.Rule(QgsMarkerSymbol.createSimple({}),
                                                   filterExp=f"\"name\" <> '{name}'"))
    layer = to_geopackage(layer, str(tmp_path / "abc.gpkg"))
    layer.setRenderer(QgsRuleBasedRenderer(root))
    exporter = _exporter(tmp_path, [layer], QgsRectangle(-1e3, -1e3, 1e3, 1e3))
    left, made = [], []
    one = exporter._export_one_rule_group_recorded  # pylint: disable=protected-access
    temp_path = exporter._temp_path  # pylint: disable=protected-access

    def checked(grp, source):
        output = one(grp, source)
        left.extend(name for name in os.listdir(exporter.utils_dir) if _STEP_FILE.match(name))
        return output

    def tracked(prefix="temp"):
        made.append(temp_path(prefix))
        return made[-1]
    monkeypatch.setattr(exporter, "_export_one_rule_group_recorded", checked)
    monkeypatch.setattr(exporter, "_temp_path", tracked)
    layers, _rules = exporter.export()
    assert len(layers) == 3 and len(made) > 6
    assert left == []


# -- inner effect strips --------------------------------------------------------

def test_direction_runs_reach_the_end_of_mercator_lines(plugin, tmp_path):
    """The window's end was clamped to a Python sum of the segment lengths,
    an ulp past QGIS's own length for some lines: interpolatePoint gave
    None and the whole strips dataset failed (AttributeError)."""
    from fidelity.materialize import Recipe
    rng = random.Random(7)
    layer = QgsVectorLayer("LineString?crs=EPSG:3857&field=id:integer", "lines", "memory")
    for number in range(300):
        x, y = 2e6 + rng.uniform(0, 1e5), 6e6 + rng.uniform(0, 1e5)
        points = [(x, y)]
        for _ in range(rng.randint(1, 7)):
            points.append((points[-1][0] + rng.uniform(-3e3, 3e3), points[-1][1] + rng.uniform(-3e3, 3e3)))
        feature = QgsFeature(layer.fields())
        feature.setAttributes([number])
        feature.setGeometry(QgsGeometry.fromWkt("LINESTRING(" + ", ".join(f"{a!r} {b!r}" for a, b in points) + ")"))
        layer.dataProvider().addFeatures([feature])
    saved = to_geopackage(layer, str(tmp_path / "lines.gpkg"))
    exporter = _bare(tmp_path)
    out = exporter._direction_runs(saved.source(), Recipe(  # pylint: disable=protected-access
        "direction_runs", (), (("buckets", 8), ("window", 2000.0))), 1)
    runs = QgsVectorLayer(out, "runs", "ogr")
    assert runs.isValid() and {f["id"] for f in runs.getFeatures()} == set(range(300))


# -- file chains ----------------------------------------------------------------

@pytest.mark.parametrize("placements", [("Interval",), ("Interval", "FirstVertex")])
def test_blank_segment_markers_in_file_chains(plugin, tmp_path, placements):
    """QGIS 4 blank segments with interval markers handed a memory layer
    token to Processing when the chain wrote files (parallel export,
    Q2VT_FILE_CHAINS=1, a memory chain redone with files)."""
    from fidelity.materialize import Recipe
    layer = QgsVectorLayer("LineString?crs=EPSG:3857&field=id:integer", "line", "memory")
    feature = QgsFeature(layer.fields())
    feature.setAttributes([1])
    feature.setGeometry(QgsGeometry.fromWkt("LINESTRING(0 0, 0 100)"))
    layer.dataProvider().addFeatures([feature])
    saved = to_geopackage(layer, str(tmp_path / "line.gpkg"))
    exporter = _bare(tmp_path)
    assert not exporter._memory_active  # pylint: disable=protected-access
    recipe = Recipe("marker_points", placements, (("interval", 20.0), ("blank", ("'(((0 30)))'", 1.0)),
                                                  ("crs", "EPSG:3857")))
    out = exporter._materialize_marker_points(saved.source(), recipe, 1)  # pylint: disable=protected-access
    assert isinstance(out, str) and not out.startswith(_module()._MEM_PREFIX)  # pylint: disable=protected-access
    points = QgsVectorLayer(out, "points", "ogr")
    assert points.isValid() and points.featureCount() == 4  # (the first vertex is blanked)
    assert not exporter._mem  # pylint: disable=protected-access


# -- long layer names -----------------------------------------------------------

def test_layer_with_a_long_name_exports(plugin, tmp_path):
    """Work files were named with the whole layer id (name + UUID): a long
    name passed the file-name limit and the layer left the map."""
    name = "Települési_környezet_" * 12
    small = _points("EPSG:3857", [(["a"], 0, 0)], name="kicsi")
    path = str(tmp_path / "long.gpkg")
    to_geopackage(small, path)
    layer = _ruled(QgsVectorLayer(f"{path}|layername=kicsi", name, "ogr"))
    assert len(layer.id()) > 250
    feedback = QgsProcessingFeedback()
    errors = []
    feedback.reportError = lambda text, fatal=False: errors.append(text)
    layers, _rules = _exporter(tmp_path, [layer], QgsRectangle(-1e3, -1e3, 1e3, 1e3), feedback=feedback).export()
    assert len(layers) == 1 and layers[0].featureCount() == 1 and not errors
    assert all(len(name) < 100 for name in os.listdir(str(tmp_path / "utils")))


# -- failing writes and locked files --------------------------------------------

def test_snapshot_that_cannot_be_written_is_not_cached(plugin, tmp_path, monkeypatch):
    """A copy short of features (disk full) was exported and cached under the
    complete layer's fingerprint."""
    layer = _points("EPSG:3857", [(["a"], 0, 0), (["b"], 1, 0)])
    reset_project(layer)
    exporter = _bare(tmp_path)
    errors = []
    monkeypatch.setattr(exporter.feedback, "reportError", lambda text, fatal=False: errors.append(text))
    _uri, fingerprint = exporter._memory_snapshot(layer)  # pylint: disable=protected-access
    assert fingerprint and not errors
    monkeypatch.setattr(QgsVectorFileWriter, "addFeature", lambda self, *args: False)
    _uri, fingerprint = exporter._memory_snapshot(layer)  # pylint: disable=protected-access
    assert fingerprint is None and errors


def test_snapshot_of_a_big_layer_can_be_cancelled(plugin, tmp_path):
    feedback = QgsProcessingFeedback()
    layer = _points("EPSG:3857", [([str(i)], i, 0) for i in range(5)])
    reset_project(layer)
    exporter = _bare(tmp_path)
    exporter.feedback = feedback
    feedback.cancel()
    with pytest.raises(_module()._Cancelled):  # pylint: disable=protected-access
        exporter._memory_snapshot(layer)  # pylint: disable=protected-access


def test_work_file_writer_errors_raise_with_their_message(plugin, tmp_path):
    """The FlatGeobuf steps never checked their writer: a file that could
    not be written surfaced later as "Could not load source layer"."""
    fields = QgsFields()
    fields.append(QgsField("id", QVariant.Int))
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "FlatGeobuf"
    bad = str(tmp_path / "missing" / "dir" / "out.fgb")
    with pytest.raises(RuntimeError, match="Cannot write a work file"):
        _module()._checked(QgsVectorFileWriter.create(  # pylint: disable=protected-access
            bad, fields, QgsWkbTypes.Point, QgsCoordinateReferenceSystem("EPSG:3857"),
            _bare(tmp_path)._transform_context, options))  # pylint: disable=protected-access
    failing = types.SimpleNamespace(hasError=lambda: QgsVectorFileWriter.NoError,
                                    addFeature=lambda *a: False, errorMessage=lambda: "disk full")
    with pytest.raises(RuntimeError, match="disk full"):
        _module()._checked(failing).addFeature(QgsFeature())  # pylint: disable=protected-access


def test_locked_work_file_fails_the_group_instead_of_the_export(plugin, tmp_path, monkeypatch):
    """A half-written dataset still open elsewhere (Windows) could not be
    deleted before the group was redone: PermissionError ended the export."""
    exporter = _bare(tmp_path)
    exporter._memory_chains = True  # pylint: disable=protected-access
    grp = types.SimpleNamespace(output_dataset="l00", layer_id="x")
    open(os.path.join(exporter.utils_dir, "l00.gpkg"), "w").close()
    calls = []

    def failing(group, source):
        calls.append(group)
        raise ValueError("memory chain failed")
    monkeypatch.setattr(exporter, "_export_one_rule_group", failing)

    def locked(path):
        raise PermissionError(32, "used by another process", path)
    monkeypatch.setattr(_module().os, "remove", locked)
    with pytest.raises(ValueError, match="memory chain failed"):
        exporter._export_one_rule_group_recorded(grp, "source")  # pylint: disable=protected-access
    assert len(calls) == 1  # not redone over the half-written file
    assert not _module()._removed(os.path.join(exporter.utils_dir, "l00.gpkg"))  # pylint: disable=protected-access


# -- measures and repeated fields ----------------------------------------------

def test_generator_part_fields_measure_on_the_ellipsoid(plugin, tmp_path):
    """Per-part values of a geometry generator's sub-symbol were measured in
    Web Mercator metres (2x at 60N) where QGIS uses the project ellipsoid."""
    layer = QgsVectorLayer("LineString?crs=EPSG:3857&field=id:integer", "line", "memory")
    feature = QgsFeature(layer.fields())
    feature.setAttributes([1])
    y = 8399737.89  # 60N
    feature.setGeometry(QgsGeometry.fromWkt(f"LINESTRING(0 {y}, 1000 {y})"))
    layer.dataProvider().addFeatures([feature])
    saved = to_geopackage(layer, str(tmp_path / "line.gpkg"))
    project = reset_project(saved)
    project.setEllipsoid("EPSG:7030")
    try:
        exporter = _bare(tmp_path)
        out = exporter._split_parts(saved.source(), [(6, "$length", "len")],  # pylint: disable=protected-access
                                    "$geometry", 1)
    finally:
        project.setEllipsoid("NONE")
    lengths = [f["len"] for f in QgsVectorLayer(out, "parts", "ogr").getFeatures()]
    assert lengths == [pytest.approx(501.26, abs=0.5)]


def test_field_mapping_names_each_field_once(plugin, tmp_path):
    """"Include all fields" mapped a property computed on the lines and the
    source field of the same name: refactorfields kept one field per name
    but one value per entry, so every later column took its neighbour's."""
    layer = _points("EPSG:3857", [([True, 7, "bee"], 0, 0)],
                    fields="&field=x:boolean&field=a:integer&field=b:string")
    saved = to_geopackage(layer, str(tmp_path / "x.gpkg"))
    exporter = _bare(tmp_path)
    grp = types.SimpleNamespace(
        description="d", expression_fields=[(1, '"x"', "x"), (4, '"a"', "a")], include_required_fields_only=1,
        visible_polygons=False, split_label_lines=False, layer_id="x", rule_type=0, source_geometry=0,
        pattern_anchor="", merge=False, anchor_crs="")
    mapping = exporter._build_field_mapping(grp, saved.source())  # pylint: disable=protected-access
    names = [m["name"].lower() for m in mapping]
    assert len(names) == len(set(names)) and {"x", "a", "b"} <= set(names)


# -- threads ------------------------------------------------------------------------

def test_worker_functions_never_read_the_project():
    """Workers use the transform context copied on the main thread: the
    project may be cleared or changed while a parallel export runs."""
    path = os.path.join(HERE, "..", "..", "src", "core", "rules_exporter.py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    readers = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for inner in ast.walk(node):
                if isinstance(inner, ast.Attribute) and inner.attr == "instance" and \
                        isinstance(inner.value, ast.Name) and inner.value.id == "QgsProject":
                    readers.add(node.name)
    # The constructor, the caller-thread layer copy and the cache key (main thread).
    assert readers <= {"__init__", "_memory_snapshot", "_cache_context"}, readers


def test_long_layer_ids_are_shortened_for_file_names(plugin):
    file_id = _module()._file_id  # pylint: disable=protected-access
    short = "utak_0b6e2f6e_4b8c_4c8b_9a43_2a3c4d5e6f70"
    assert file_id(short) == short
    long_id = "x" * 230 + "_0b6e2f6e_4b8c_4c8b_9a43_2a3c4d5e6f70"
    assert len(file_id(long_id)) <= 56 and file_id(long_id) != file_id(long_id[:-1] + "1")
    assert math.isclose(len(file_id(long_id)), 56)
    assert not glob.has_magic(file_id(long_id))
