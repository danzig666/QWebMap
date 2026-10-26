**QWebMap 4.53.0**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Improved: raster layers as sharp as in QGIS
Raster layers (scanned plans, orthophotos) looked softer on the web map than in QGIS, with blurry edges — measured against QGIS's own drawing of the same view, 70–85 % of its edge sharpness. Three causes, all fixed:
- **"Like the image" stopped one zoom too early.** Zoomed in past it, the browser enlarged tiles that were already resampled from the image — smoothed twice. It now publishes one zoom finer than the image (about 2.7× larger raster archives; you can still pick a coarser pixel size per layer). Online tile services keep their own finest zoom.
- **Tiles were enlarged between zoom levels and on scaled screens** (125 %, 200 %). The web map now loads the next finer tiles instead and only ever shrinks them.
- **Shrunk tiles were drawn from a blurred half-size copy.** They are now drawn from the tile itself, as QGIS draws an image.

Result: 87–100 % of QGIS's sharpness (mostly 90–100 %) between zoom levels, past the image's own resolution and on scaled screens. Live online layers (XYZ / WMS) load as before.

### New: maps of raster layers only
A web map can now have only raster layers — local images, live XYZ or WMS layers, with or without a basemap. Before, the export stopped with "Select at least one vector layer to publish". Layer list, legend, themes, zoom to layer, print and publishing work as usual.

Re-export the map to get the changes.
