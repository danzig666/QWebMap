**QWebMap 4.56.1**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
- **No crash on hillshade raster layers.** With OpenCL switched on (*Settings › Options › Acceleration*), QGIS's own hillshade renderer could crash QGIS while the export rendered the layer's tiles: on a block one pixel high it copies a second row that is not there. The export now renders raster tiles with OpenCL off and switches it back on afterwards. (The same QGIS bug can rarely hit the map canvas; switching OpenCL off avoids it there too.)

- **Exports that never finished.** An outline-only polygon layer (a fully transparent fill) was exported as filled polygons: a layer covering a large area put a polygon that draws nothing into every tile inside it, up to the last zoom (hundreds of millions of tiles for an Arctic map). Only its outline is exported now, as QGIS draws it.
- **Long lines no longer stall tile generation at about 80 %.** GDAL cuts each feature at every tile of its bounding box, so a long diagonal line (a sea route, the outline of a large polygon) cost hours at the highest zooms. From the zoom where that happens, such lines are tiled from a copy cut along the tile grid; the cuts are tile edges, so the map looks the same. A test project of the Arctic now exports in 12 minutes instead of not finishing.

### Changed
- **Saving the project as another file keeps the publication settings.** A project saved under a new name or in another folder no longer asks whether to start a new web map. Every setting and the same web map are kept; the window asks only where to export: *Keep the folder*, *Next to this project* (its `web_maps` folder) or *Choose a folder…*. It does not ask when the new file is in the same folder. For a separate web map, export the settings to a file and import them as a new web map.
- **The zoomed-out check runs once.** Before an export, the *Zoomed-out load* estimate is not run again while nothing it reads changed (the extent, the zooms, a published vector layer's data, style or scales, the web layer settings). Once you have answered it, or looked at it with *Zoomed-out load…*, the next export does not ask again.
