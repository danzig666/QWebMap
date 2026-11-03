"""Terrain-RGB export (publishing.terrain): heights as GDAL warps them, the
area around the DEM filled without a cliff, and no per-zoom full fill (it
took minutes at the highest zoom of a 1 m DEM)."""

import io
import os

import numpy as np
import pytest
from osgeo import gdal, osr
from qgis.core import QgsRasterLayer

from q2vt_fixtures import reset_project

gdal.UseExceptions()
ORIGIN = 20037508.342789244


def _eov_dem(path, size=1500):
    """A 1 m DEM in EOV (EPSG:23700), heights 100-160 m, with a nodata hole."""
    ds = gdal.GetDriverByName("GTiff").Create(str(path), size, size, 1, gdal.GDT_Float32)
    ds.SetGeoTransform([727000, 1, 0, 285000, 0, -1])
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(23700)
    ds.SetProjection(srs.ExportToWkt())
    yy, xx = np.mgrid[0:size, 0:size]
    heights = (130 + 20 * np.sin(xx / 120) * np.cos(yy / 90) + xx / 150).astype(np.float32)
    heights[600:700, 600:700] = -9999
    band = ds.GetRasterBand(1)
    band.WriteArray(heights)
    band.SetNoDataValue(-9999)
    ds = None
    return str(path)


def test_terrain_heights_fill_and_one_full_fill(plugin, tmp_path, monkeypatch):
    from PIL import Image
    from q2vt_plugin.src.publishing import terrain  # pylint: disable=import-error
    from q2vt_plugin.src.publishing.validation import open_pmtiles  # pylint: disable=import-error
    path = _eov_dem(tmp_path / "dem.tif")
    project = reset_project()
    layer = QgsRasterLayer(path, "Domborzat")
    assert layer.isValid()
    project.addMapLayer(layer)
    # The DEM's box in Web Mercator, grown as the export grows it.
    src, dst = osr.SpatialReference(), osr.SpatialReference()
    src.ImportFromEPSG(23700)
    dst.ImportFromEPSG(3857)
    for srs in (src, dst):
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    to_web = osr.CoordinateTransformation(src, dst)
    corners = [to_web.TransformPoint(x, y)[:2] for x in (727000, 728500) for y in (283500, 285000)]
    xs, ys = [c[0] for c in corners], [c[1] for c in corners]
    area = terrain.grow((min(xs), min(ys), max(xs), max(ys)))
    fills = []
    original = gdal.FillNodata
    monkeypatch.setattr(gdal, "FillNodata", lambda *a, **k: fills.append(1) or original(*a, **k))
    out = str(tmp_path / "terrain.pmtiles")
    assert terrain.render_terrain(layer, area, 12, 16, out) is not None
    assert len(fills) == 1  # only the lowest zoom is filled from the edges
    assert not [n for n in os.listdir(tmp_path) if ".dem.vrt" in n]  # the pyramid is removed
    with open_pmtiles(out) as archive:
        tiles = {tuple(a): d for a, d in archive.tiles()}
    assert {z for z, _, _ in tiles} >= {14, 15}
    to_eov = osr.CoordinateTransformation(dst, src)
    steps, relief = {}, {}  # per zoom: steepest step anywhere / inside the DEM
    for (z, x, y), data in tiles.items():
        rgb = np.asarray(Image.open(io.BytesIO(data)).convert("RGB")).astype(np.float64)
        heights = -10000 + (rgb[..., 0] * 65536 + rgb[..., 1] * 256 + rgb[..., 2]) * 0.1
        assert heights.min() > 50 and heights.max() < 220, (z, x, y)  # filled: no nodata, no outliers
        size = 2 * ORIGIN / (1 << z)
        bounds = (-ORIGIN + x * size, ORIGIN - (y + 1) * size, -ORIGIN + (x + 1) * size, ORIGIN - y * size)
        warped = gdal.Warp("", path, format="MEM", outputBounds=bounds, width=256, height=256,
                           dstSRS="EPSG:3857", resampleAlg="bilinear", outputType=gdal.GDT_Float32,
                           dstNodata=-32768)
        expected = warped.GetRasterBand(1).ReadAsArray()
        warped = None
        px = size / 256
        cols = bounds[0] + (np.arange(256) + 0.5) * px
        rows = bounds[3] - (np.arange(256) + 0.5) * px
        grid = np.array(to_eov.TransformPoints(np.c_[np.tile(cols, 256), np.repeat(rows, 256)]))
        inside = ((grid[:, 0] > 727003) & (grid[:, 0] < 728497) & (grid[:, 1] > 283503)
                  & (grid[:, 1] < 284997)).reshape(256, 256) & (expected > -1000)
        if inside.any() and z >= 14:  # at the DEM's resolution: GDAL's heights (0.1 m encoding)
            assert np.abs(heights - expected)[inside].max() <= 0.15, (z, x, y)
        steps[z] = max(steps.get(z, 0.0), np.abs(np.diff(heights, axis=0)).max(),
                       np.abs(np.diff(heights, axis=1)).max())
        both = inside[1:, :] & inside[:-1, :]
        if both.any():
            relief[z] = max(relief.get(z, 0.0), np.abs(np.diff(heights, axis=0))[both].max())
    # No cliff where the DEM ends or around its hole, at the zooms filled
    # from the zoom below: a step there (the DEM's detail finer than the
    # zoom below) at most 2.5 times the relief's own steepest (the old fill
    # of every zoom, from the edges: up to 3.5 times, at zooms 13-15). The
    # lowest zoom is filled from the edges by GDAL, as before.
    for z, step in steps.items():
        if z == min(steps):
            continue
        assert step <= 2.5 * relief.get(z, step) + 1.0, (z, step, relief.get(z))
