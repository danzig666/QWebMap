"""Raster tiles drawn smaller than their pixels are sampled from the tile
itself (bilinear, or nearest with raster-resampling "nearest"), as QGIS
samples an image it draws smaller, not from a half-size mipmap.

Stock MapLibre minifies raster tiles with LINEAR_MIPMAP_NEAREST: past about
1.41x smaller the half-resolution level is taken, and a one-pixel line of a
scanned plan or an orthophoto edge is smeared over two to three pixels. The
viewer loads raster archive tiles up to twice finer than the screen (never
enlarged: transport.sharpTileSize), so the tiles are drawn up to two times
smaller; QGIS draws the same view sharp. Measured at zoom 17.5 on a plan
image: 70 % of QGIS's edge sharpness with the mipmap. Two times smaller is
within what bilinear sampling alone draws without visible aliasing (as
QGIS's bilinear resampling).
"""

EDITS = [
    ("main", "texture.bind(textureFilter, gl.CLAMP_TO_EDGE, gl.LINEAR_MIPMAP_NEAREST);",
     "texture.bind(textureFilter, gl.CLAMP_TO_EDGE, textureFilter);", 3),
]
