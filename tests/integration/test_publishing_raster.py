"""QGIS raster layers in a publication: rendered by QGIS into their own
raster PMTiles archive (PNG/JPEG/WebP), drawn at their layer-tree position
under the vector layers above them and under all labels; vector layers stay
MVT; empty rasters are dropped; the style contract only accepts the
release's own image archives."""

import json
import os
import sys

import numpy as np
import pytest
from osgeo import gdal, osr
from qgis.core import QgsProject, QgsRasterLayer, QgsRectangle

from publishing.controller import export_local
from publishing.errors import PublishingError
from publishing.models import LayerConfig
from publishing.provenance import layer_logical_id
from publishing.validation import open_pmtiles, validate_pmtiles, vector_only_violations
from q2vt_fixtures import reset_project

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_publishing_pipeline import _parcels, _profile  # noqa: E402  pylint: disable=wrong-import-position

SCHEMA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                      "schemas", "publishing", "manifest-v1.schema.json")


def _validate_manifest(manifest):
    jsonschema = pytest.importorskip("jsonschema")
    with open(SCHEMA, encoding="utf-8") as handle:
        jsonschema.validate(manifest, json.load(handle))


EXTENT = QgsRectangle(2119000, 6019000, 2123000, 6023000)


def make_raster(path, origin=(2119000, 6023000), size=400, pixel=10.0, alpha=False):
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(str(path), size, size, 4 if alpha else 3, gdal.GDT_Byte)
    ds.SetGeoTransform([origin[0], pixel, 0, origin[1], 0, -pixel])
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3857)
    ds.SetProjection(srs.ExportToWkt())
    yy, xx = np.mgrid[0:size, 0:size]
    bands = [xx % 256, yy % 256, (xx + yy) % 256]
    if alpha:
        bands.append(np.where(xx < size // 2, 255, 0))
    for index, band in enumerate(bands, 1):
        ds.GetRasterBand(index).WriteArray(band.astype(np.uint8))
    ds = None
    return str(path)


def _project(tmp_path, raster_above=False, **raster_kwargs):
    project = reset_project()
    parcels = _parcels(str(tmp_path / "parcels.gpkg"))
    ortho = QgsRasterLayer(make_raster(tmp_path / "ortho.tif", **raster_kwargs), "Ortofotó")
    assert ortho.isValid()
    root = project.layerTreeRoot()
    project.addMapLayer(parcels, False)
    project.addMapLayer(ortho, False)
    if raster_above:
        root.addLayer(ortho)
        root.addLayer(parcels)
    else:
        root.addLayer(parcels)
        root.addLayer(ortho)
    profile = _profile(parcels, tmp_path)
    profile.layers.append(LayerConfig(ortho.id(), raster_format="webp", raster_max_zoom=15))
    return project, profile, parcels, ortho


def test_raster_layer_gets_its_own_image_archive_under_the_vectors(tmp_path):
    project, profile, parcels, ortho = _project(tmp_path)
    result = export_local(project, profile, EXTENT)
    rel = result.release.release_dir
    manifest = json.load(open(os.path.join(rel, "manifest.json"), encoding="utf-8"))
    _validate_manifest(manifest)
    style = json.load(open(os.path.join(rel, "style.json"), encoding="utf-8"))
    lid = layer_logical_id(ortho.id())
    raster = [s for s in manifest["sources"] if s.get("role") == "raster"]
    assert manifest["sources"][0]["tileType"] == "mvt" and len(raster) == 1
    from publishing.raster_tiles import tile_format  # WebP, or PNG where this QGIS cannot write it
    image = tile_format("webp")
    assert raster[0]["tileType"] == image and raster[0]["href"] == f"data/raster-{lid}.pmtiles"
    summary = validate_pmtiles(os.path.join(rel, raster[0]["href"]), sample=0, kind="image")
    assert summary["tileType"] == image and summary["maxZoom"] == 15
    with open_pmtiles(os.path.join(rel, raster[0]["href"])) as archive:
        assert archive.metadata()["format"] == image
    # The vector map is still MVT only and the raster sits under the parcels.
    validate_pmtiles(os.path.join(rel, "data", "map.pmtiles"), sample=0)
    ids = [layer["id"] for layer in style["layers"]]
    raster_index = ids.index(f"q2vt-raster-{lid}")
    parcel_layers = [c for c in manifest["components"] if c["layerId"] == layer_logical_id(parcels.id())]
    first_parcel = min(ids.index(i) for c in parcel_layers for i in c["styleLayerIds"] if i in ids)
    assert raster_index < first_parcel
    entry = next(layer for layer in manifest["layers"] if layer["id"] == lid)
    assert entry["geometry"] == "raster" and entry["componentIds"] == [f"c-raster-{lid}"]
    assert not vector_only_violations(style, raster_sources={raster[0]["id"]})
    assert vector_only_violations(style)  # without the release's own archives: refused
    # The project is untouched.
    assert project.layerTreeRoot().findLayer(ortho.id()).isVisible()


def test_raster_above_vectors_stays_under_labels(tmp_path):
    project, profile, parcels, ortho = _project(tmp_path, raster_above=True, alpha=True)
    profile.layers[-1].raster_format = "png"
    result = export_local(project, profile, EXTENT)
    rel = result.release.release_dir
    manifest = json.load(open(os.path.join(rel, "manifest.json"), encoding="utf-8"))
    _validate_manifest(manifest)
    style = json.load(open(os.path.join(rel, "style.json"), encoding="utf-8"))
    ids = [layer["id"] for layer in style["layers"]]
    lid = layer_logical_id(ortho.id())
    raster_index = ids.index(f"q2vt-raster-{lid}")
    labels = [i for c in manifest["components"] if c["role"] == "label" for i in c["styleLayerIds"] if i in ids]
    geometry = [i for c in manifest["components"] if c["role"] == "geometry" for i in c["styleLayerIds"] if i in ids]
    assert labels and all(ids.index(i) > raster_index for i in labels)
    assert all(ids.index(i) < raster_index for i in geometry)
    # Half of the image is transparent: those tiles are not stored.
    source = next(s for s in manifest["sources"] if s.get("role") == "raster")
    with open_pmtiles(os.path.join(rel, source["href"])) as archive:
        stored = list(archive.entries())
    from publishing.raster_tiles import count_tiles
    full = count_tiles((2119000, 6019000, 2123000, 6023000), profile.view.min_zoom, 15)
    assert 0 < len(stored) < full


def test_raster_outside_the_extent_is_dropped(tmp_path):
    project, profile, parcels, ortho = _project(tmp_path, origin=(3000000, 7000000))
    result = export_local(project, profile, EXTENT)
    manifest = json.load(open(os.path.join(result.release.release_dir, "manifest.json"), encoding="utf-8"))
    assert all(s.get("role") != "raster" for s in manifest["sources"])
    assert layer_logical_id(ortho.id()) not in {layer["id"] for layer in manifest["layers"]}
    assert any("draws nothing" in w for w in result.warnings)


def test_a_very_large_raster_is_warned_about_not_refused(tmp_path):
    """No tile limit: a raster of hours of rendering gets a warning, and the
    advice names the setting that sets its size and what brings it down."""
    from publishing.controller import _plan_rasters
    from publishing.qgis_model import split_profile
    from publishing.raster_tiles import LARGE_TILES_PER_LAYER, count_tiles, large_raster_advice
    project, profile, parcels, ortho = _project(tmp_path, size=20, pixel=2000)
    config = profile.layers[-1]
    config.raster_max_zoom = 20
    extent = QgsRectangle(2119000, 5983000, 2159000, 6023000)  # the raster: 40 × 40 km
    plan = _plan_rasters(project, profile, split_profile(profile, project)[1], extent)[ortho.id()]
    assert plan.tiles > LARGE_TILES_PER_LAYER
    assert any("can take hours" in w and "Ortofotó" in w for w in plan.warnings)
    advice = large_raster_advice(plan, ortho.name(), config, profile.view.max_zoom)
    assert '"Sharpest detail"' in advice and "(zoom 20)" in advice
    fits = max(z for z in range(plan.min_zoom, 20) if count_tiles(plan.extent_3857, plan.min_zoom, z)
               <= LARGE_TILES_PER_LAYER)
    assert f"(zoom {fits}):" in advice and "smaller extent" in advice
    config.raster_max_zoom, config.raster_match_native = None, False
    plan = _plan_rasters(project, profile, [config], extent)[ortho.id()]
    if plan.tiles > LARGE_TILES_PER_LAYER:
        assert "Maximum tile zoom" in large_raster_advice(plan, ortho.name(), config, profile.view.max_zoom)


def _image(rgba):
    """QImage (ARGB32) from an (h, w, 4) uint8 RGBA array."""
    from qgis.PyQt.QtGui import QImage
    h, w = rgba.shape[:2]
    bgra = np.ascontiguousarray(rgba[..., [2, 1, 0, 3]])
    return QImage(bgra.tobytes(), w, h, w * 4, QImage.Format.Format_ARGB32).copy()


def _pixels(image):
    from qgis.PyQt.QtGui import QImage
    image = image.convertToFormat(QImage.Format.Format_ARGB32)
    ptr = image.constBits()
    ptr.setsize(image.sizeInBytes())
    bgra = np.frombuffer(ptr, dtype=np.uint8).reshape(image.height(), image.bytesPerLine())
    bgra = bgra[:, :image.width() * 4].reshape(image.height(), image.width(), 4)
    return bgra[..., [2, 1, 0, 3]].astype(float)


def test_blend_modes_become_the_same_normal_image():
    """Multiply by grey g = black with alpha 1 - g; screen = white with
    alpha g: drawn normally over any colour, the result is the blend."""
    from publishing.raster_tiles import blend_to_alpha
    grey = np.linspace(0, 255, 16).round().astype(np.uint8)
    rgba = np.zeros((1, 16, 4), np.uint8)
    rgba[0, :, 0] = rgba[0, :, 1] = rgba[0, :, 2] = grey
    rgba[0, :, 3] = 255
    below = np.array([200.0, 120.0, 40.0])  # a DEM colour
    g = grey.astype(float)[:, None] / 255
    for mode, expected in (("multiply", below * g), ("screen", 255 - (255 - below) * (1 - g))):
        image, is_grey = blend_to_alpha(_image(rgba), mode)
        px = _pixels(image)[0]
        a = px[:, 3:4] / 255
        drawn = px[:, :3] * a + below * (1 - a)
        assert is_grey and np.abs(drawn - expected).max() <= 1.0, mode
    rgba[0, :, 0] = 255  # a colour layer: approximated by its brightness
    assert blend_to_alpha(_image(rgba), "multiply")[1] is False


def test_hillshade_multiply_over_a_dem_is_published_as_shading(tmp_path):
    """The TerrainForge case: a grey hillshade in multiply mode over a colour
    DEM (also multiply, lowest, on a white map). The hillshade tiles become
    black with alpha 1 - grey; the DEM is drawn normally (the same over
    white); a vector layer's blend mode is reported, not silently dropped."""
    from qgis.PyQt.QtGui import QImage, QPainter
    project, profile, parcels, dem = _project(tmp_path)
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(str(tmp_path / "hillshade.tif"), 400, 400, 1, gdal.GDT_Byte)
    ds.SetGeoTransform([2119000, 10.0, 0, 6023000, 0, -10.0])
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3857)
    ds.SetProjection(srs.ExportToWkt())
    ds.GetRasterBand(1).WriteArray((np.mgrid[0:400, 0:400][1] * 255 // 399).astype(np.uint8))
    ds = None
    shade = QgsRasterLayer(str(tmp_path / "hillshade.tif"), "Hillshade")
    assert shade.isValid() and shade.renderer().type() == "singlebandgray"
    multiply = QPainter.CompositionMode.CompositionMode_Multiply
    shade.setBlendMode(multiply)
    dem.setBlendMode(multiply)
    parcels.setBlendMode(multiply)
    project.addMapLayer(shade, False)
    project.layerTreeRoot().insertLayer(1, shade)  # parcels, hillshade, DEM (bottom)
    profile.layers.append(LayerConfig(shade.id(), raster_format="png", raster_max_zoom=13))
    profile.layers[-2].raster_format = "png"
    result = export_local(project, profile, EXTENT)
    rel = result.release.release_dir
    manifest = json.load(open(os.path.join(rel, "manifest.json"), encoding="utf-8"))
    href = {s["id"]: s["href"] for s in manifest["sources"] if s.get("role") == "raster"}
    shade_href = next(h for h in href.values() if layer_logical_id(shade.id()) in h)
    dem_href = next(h for h in href.values() if layer_logical_id(dem.id()) in h)
    with open_pmtiles(os.path.join(rel, shade_href)) as archive:
        _, data = next(iter(archive.tiles()))
    px = _pixels(QImage.fromData(data))
    assert px[..., :3].max() == 0 and 0 < px[..., 3].max() <= 255  # black shading only
    with open_pmtiles(os.path.join(rel, dem_href)) as archive:
        _, data = next(iter(archive.tiles()))
    px = _pixels(QImage.fromData(data))
    visible = px[px[..., 3] > 0]
    assert len(visible) and visible[:, 3].min() == 255 and visible[:, :3].max() > 0  # the DEM's own colours
    assert any("Földrészletek" in w and "multiply" in w for w in result.warnings)
    assert not any("Hillshade" in w or "Ortofotó" in w for w in result.warnings)


def test_unchanged_raster_layers_are_reused_from_the_export_cache(tmp_path, monkeypatch):
    """Rendering rasters is slow and they rarely change: a second export with
    the same raster, style and settings reuses the archive; a style or image
    setting change renders it again."""
    from q2vt_plugin.src.publishing import raster_tiles  # pylint: disable=import-error
    rendered = []
    original = raster_tiles.render_layer

    def counting(*args, **kwargs):
        rendered.append(args[1].id())
        return original(*args, **kwargs)
    monkeypatch.setattr(raster_tiles, "render_layer", counting)
    project, profile, parcels, ortho = _project(tmp_path)
    profile.output.reuse_unchanged = True
    lid = layer_logical_id(ortho.id())

    def export():
        rel = export_local(project, profile, EXTENT).release.release_dir
        with open(os.path.join(rel, "data", f"raster-{lid}.pmtiles"), "rb") as handle:
            return handle.read()
    first = export()
    second = export()
    assert len(rendered) == 1 and first == second  # reused, same archive
    ortho.renderer().setOpacity(0.5)  # style changed
    export()
    assert len(rendered) == 2
    profile.layer(ortho.id()).raster_quality = 60  # image setting changed
    export()
    assert len(rendered) == 3


def test_raster_tiles_are_the_same_with_any_number_of_threads(tmp_path):
    """Metatiles are rendered and encoded in parallel, then written in a
    fixed order: the archive is byte for byte the one a single thread makes
    (so the export cache and unchanged-file uploads keep working)."""
    from q2vt_plugin.src.publishing import raster_tiles  # pylint: disable=import-error
    project, profile, parcels, ortho = _project(tmp_path)
    config = profile.layer(ortho.id())
    archives = []
    for threads in (1, 4):
        plan = raster_tiles.plan_layer(project, ortho, config, profile, EXTENT)
        out = str(tmp_path / f"r{threads}.pmtiles")
        raster_tiles.render_layer(project, ortho, config, plan, out, metatile=2, threads=threads)
        with open(out, "rb") as handle:
            archives.append(handle.read())
    assert archives[0] == archives[1] and len(archives[0]) > 1000


def test_webp_falls_back_to_png_where_qgis_cannot_write_it(tmp_path, monkeypatch):
    """WebP is the default image format; a QGIS without a WebP writer makes
    PNG tiles (also transparent) with a warning instead of failing."""
    from q2vt_plugin.src.publishing import raster_tiles  # pylint: disable=import-error
    from q2vt_plugin.src.publishing.vendor.pmtiles.tile import TileType  # pylint: disable=import-error
    assert LayerConfig("x").raster_format == "webp"
    project, profile, parcels, ortho = _project(tmp_path)
    config = profile.layer(ortho.id())

    class NoWebp:  # pylint: disable=too-few-public-methods
        @staticmethod
        def supportedImageFormats():
            return [b"png", b"jpeg"]
    monkeypatch.setattr(raster_tiles, "QImageWriter", NoWebp)
    plan = raster_tiles.plan_layer(project, ortho, config, profile, EXTENT)
    out = str(tmp_path / "fallback.pmtiles")
    raster_tiles.render_layer(project, ortho, config, plan, out)
    with open_pmtiles(out) as archive:
        assert archive.header["tile_type"] == TileType.PNG and archive.metadata()["format"] == "png"
    assert any("cannot write WebP" in warning for warning in plan.warnings)


def test_matching_the_image_resolution_sets_the_maximum_zoom(tmp_path):
    """Ground resolution of the image (one pixel measured on the ellipsoid:
    10 Web Mercator m at 47.5° N are 6.76 m) and of the tiles; matching picks
    one zoom finer than the lowest as fine as the image (sharp_zoom: as sharp
    as QGIS zoomed in), one less with 512 px tiles; an online service's own
    finest zoom."""
    import math
    from q2vt_plugin.src.publishing import raster_tiles  # pylint: disable=import-error
    assert raster_tiles.native_zoom(0.4, 47.97) == 18 and raster_tiles.native_zoom(0.4, 47.97, True) == 17
    assert raster_tiles.ground_resolution(18, 47.97) == pytest.approx(0.4, rel=0.01)
    project, profile, parcels, ortho = _project(tmp_path)
    config = profile.layer(ortho.id())
    assert config.raster_max_zoom == 15  # an explicit zoom wins
    assert raster_tiles.plan_layer(project, ortho, config, profile, EXTENT).max_zoom == 15
    config.raster_max_zoom, config.raster_match_native = None, False  # like the map
    plan = raster_tiles.plan_layer(project, ortho, config, profile, EXTENT)
    assert plan.native_m == pytest.approx(10 * math.cos(math.radians(plan.latitude)), rel=0.01)
    assert plan.max_zoom == profile.view.max_zoom == 13
    config.raster_match_native = True  # like the image (the default): one zoom finer than it
    plan = raster_tiles.plan_layer(project, ortho, config, profile, EXTENT)
    assert plan.max_zoom == 15 and plan.resolution(14) <= plan.native_m * 1.04 < plan.resolution(13)
    assert raster_tiles.sharp_zoom(0.4, 47.97) == 19 and raster_tiles.sharp_zoom(0.4, 47.97, online=True) == 18
    config.raster_hidpi = True
    assert raster_tiles.plan_layer(project, ortho, config, profile, EXTENT).max_zoom == 14


def test_tiled_online_layer_is_as_sharp_as_its_finest_tiles(tmp_path):
    """An XYZ layer (an online service: no image resolution of its own) gets
    image tiles down to its source's max zoom ("zmax"), not only to the
    vector tiles' maximum zoom; plain online layers without tile levels keep
    the map's zooms."""
    from q2vt_plugin.src.publishing import raster_tiles  # pylint: disable=import-error
    project, profile, parcels, _ortho = _project(tmp_path)
    profile.view.max_zoom = 16
    xyz = QgsRasterLayer("crs=EPSG:3857&format&type=xyz&url=http://tiles.example.invalid/%7Bz%7D/%7Bx%7D/%7By%7D.png"
                         "&zmax=18&zmin=0", "Műhold", "wms")
    assert xyz.isValid()
    project.addMapLayer(xyz)
    config = LayerConfig(xyz.id())  # defaults: "like the image"
    plan = raster_tiles.plan_layer(project, xyz, config, profile, EXTENT)
    assert plan.online and plan.max_zoom == 18 and plan.native_m
    assert raster_tiles._xyz_zmax_resolution(xyz) == pytest.approx(0.5971642834779395)  # pylint: disable=protected-access
    config.raster_match_native = False  # "like the map"
    assert raster_tiles.plan_layer(project, xyz, config, profile, EXTENT).max_zoom == 16


def test_raster_tiles_are_rendered_with_opencl_off_and_it_is_restored(tmp_path, monkeypatch):
    """QGIS's OpenCL hillshade crashes QGIS on a block one pixel high (it
    copies a second row that is not there; QgsHillshadeRenderer::block), as
    the export's small reprojected renders ask for: OpenCL is off while the
    tiles render (QgsOpenClUtils reads core/OpenClEnabled on every block)
    and back on afterwards, also when the render fails."""
    from qgis.core import QgsHillshadeRenderer, QgsSettings
    from q2vt_plugin.src.publishing import raster_tiles  # pylint: disable=import-error
    project, profile, parcels, ortho = _project(tmp_path)
    ortho.setRenderer(QgsHillshadeRenderer(ortho.dataProvider(), 1, 315, 45))
    config = profile.layer(ortho.id())
    settings = QgsSettings()
    before = settings.value(raster_tiles.OPENCL_SETTING)
    seen = []
    original = raster_tiles._render_layer  # pylint: disable=protected-access

    def spy(*args, **kwargs):
        seen.append(QgsSettings().value(raster_tiles.OPENCL_SETTING, False))
        return original(*args, **kwargs)

    monkeypatch.setattr(raster_tiles, "_render_layer", spy)
    try:
        settings.setValue(raster_tiles.OPENCL_SETTING, True)
        plan = raster_tiles.plan_layer(project, ortho, config, profile, EXTENT)
        out = str(tmp_path / "shade.pmtiles")
        assert raster_tiles.render_layer(project, ortho, config, plan, out, metatile=2, threads=4)
        assert str(seen[0]).lower() in ("0", "false")
        assert str(settings.value(raster_tiles.OPENCL_SETTING)).lower() in ("1", "true")

        def fail(*args, **kwargs):
            raise RuntimeError("render failed")
        monkeypatch.setattr(raster_tiles, "_render_layer", fail)
        with pytest.raises(RuntimeError):
            raster_tiles.render_layer(project, ortho, config, plan, out)
        assert str(settings.value(raster_tiles.OPENCL_SETTING)).lower() in ("1", "true")
        settings.remove(raster_tiles.OPENCL_SETTING)  # off: nothing set, nothing written
        with raster_tiles.opencl_off():
            pass
        assert not settings.contains(raster_tiles.OPENCL_SETTING)
    finally:
        if before is None:
            settings.remove(raster_tiles.OPENCL_SETTING)
        else:
            settings.setValue(raster_tiles.OPENCL_SETTING, before)


@pytest.mark.parametrize("kind", ["nodata", "int16", "rgb"])
def test_a_reprojected_raster_is_warped_once_with_the_same_tiles(tmp_path, monkeypatch, kind):
    """QGIS reprojects a raster for every tile; a polar image (EPSG:3413) is
    warped once to Web Mercator instead (GDAL), with the layer's style: the
    tiles are those rendered from the layer itself (but at the image's rim,
    where QGIS's reprojection is approximate), the area around the image
    stays transparent with or without nodata, and the copy is removed. An
    image already in Web Mercator is rendered as it is."""
    from io import BytesIO
    from PIL import Image
    from q2vt_plugin.src.publishing import raster_tiles  # pylint: disable=import-error
    from q2vt_plugin.src.publishing.models import PublicationProfile  # pylint: disable=import-error
    path = str(tmp_path / "polar.tif")
    size = 600
    rgb = kind == "rgb"
    ds = gdal.GetDriverByName("GTiff").Create(path, size, size, 3 if rgb else 1,
                                              gdal.GDT_Byte if rgb else gdal.GDT_Int16)
    ds.SetGeoTransform([-1500000, 5000, 0, 1500000, 0, -5000])
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3413)
    ds.SetProjection(srs.ExportToWkt())
    yy, xx = np.mgrid[0:size, 0:size]
    if rgb:  # every byte value used: no nodata value would be free
        for index, band in enumerate((xx % 256, yy % 256, (xx + yy) % 256), 1):
            ds.GetRasterBand(index).WriteArray(band.astype(np.uint8))
    else:
        ds.GetRasterBand(1).WriteArray((xx * 3 + yy * 2).astype(np.int16) % 1000 + 1)
    if kind == "nodata":
        ds.GetRasterBand(1).SetNoDataValue(-32768)
    ds = None
    project = reset_project()
    layer = QgsRasterLayer(path, "Polar")
    assert layer.isValid()
    project.addMapLayer(layer)
    profile = PublicationProfile(title="t", slug="t")
    profile.view.min_zoom, profile.view.max_zoom = 0, 16
    config = LayerConfig(layer.id(), raster_format="png", raster_match_native=True)
    extent = QgsRectangle(-8000000, 9000000, 3000000, 20037508)
    original, used = raster_tiles.warped_copy, []

    def tiles(label, warp):
        monkeypatch.setattr(raster_tiles, "warped_copy",
                            (lambda *a: used.append(original(*a)) or used[-1]) if warp else (lambda *a: None))
        plan = raster_tiles.plan_layer(project, layer, config, profile, extent)
        out = str(tmp_path / f"{label}.pmtiles")
        raster_tiles.render_layer(project, layer, config, plan, out, threads=2)
        with open_pmtiles(out) as archive:
            return plan, {tuple(a): np.asarray(Image.open(BytesIO(d)).convert("RGBA")).astype(int)
                          for a, d in archive.tiles()}

    plan, plain = tiles("plain", False)
    _, warped = tiles("warped", True)
    assert used and used[0] is not None and plan.max_zoom >= 4
    assert not [name for name in os.listdir(tmp_path) if ".warp.tif" in name]  # removed
    common = set(plain) & set(warped)
    assert len(common) >= 0.98 * len(plain)
    for address in common:
        if address[0] < 3:
            continue
        a, b = (np.concatenate([t[..., :3] * t[..., 3:] // 255, t[..., 3:]], axis=2)  # premultiplied
                for t in (plain[address], warped[address]))
        assert (np.abs(a - b).max(axis=2) > 24).mean() < 0.02, address
    # Outside the image: transparent in both (no black frame without nodata).
    corner = max(common, key=lambda k: (k[0], k[2]))  # a low row of the deepest zoom
    assert warped[corner][..., 3].min() == plain[corner][..., 3].min()
    # Web Mercator: nothing to warp.
    flat = QgsRasterLayer(make_raster(tmp_path / "flat.tif"), "Flat")
    assert raster_tiles.warped_copy(flat, plan, 256, str(tmp_path / "x.tif")) is None
    # A hillshade: shaded by its pixels' size in its own CRS, never from a copy.
    if kind == "nodata":
        from qgis.core import QgsHillshadeRenderer
        layer.setRenderer(QgsHillshadeRenderer(layer.dataProvider(), 1, 315, 45))
        assert raster_tiles.warped_copy(layer, plan, 256, str(tmp_path / "h.tif")) is None


def test_no_copy_where_qgis_reprojects_a_raster_fast(tmp_path):
    """A national grid over a town (EOV) is nearly linear to Web Mercator:
    QGIS reprojects it fast, and a copy at the finest zoom (a 1 m DEM: zoom
    18) took longer than it saved. Only curved reprojections are warped."""
    from q2vt_plugin.src.publishing import raster_tiles  # pylint: disable=import-error
    path = str(tmp_path / "eov.tif")
    ds = gdal.GetDriverByName("GTiff").Create(path, 200, 200, 1, gdal.GDT_Float32)
    ds.SetGeoTransform([727000, 5, 0, 285000, 0, -5])
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(23700)
    ds.SetProjection(srs.ExportToWkt())
    ds.GetRasterBand(1).Fill(120)
    ds = None
    layer = QgsRasterLayer(path, "EOV")
    assert layer.isValid() and not raster_tiles._curved_to_mercator(layer)  # pylint: disable=protected-access
    plan = raster_tiles.RasterPlan(layer.id(), 10, 16, 100, (8.2e6, 6.0e6, 8.3e6, 6.1e6))
    assert raster_tiles.warped_copy(layer, plan, 256, str(tmp_path / "w.tif")) is None
