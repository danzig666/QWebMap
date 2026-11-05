**QWebMap 4.58.8**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Changed
- **Raster tiles start at the zoom where the layer can be seen.** A raster layer (and a vector layer drawn as images zoomed out) is rendered from the first zoom where it is at least 8 pixels across, not from the web map's first zoom: a 16 km elevation model is less than a pixel at zoom 0, and its tiles at the lowest zooms showed nothing. On QGIS 4 for Windows those renders, started together at every zoom, closed QGIS at once while exporting a hillshade. Fewer tiles, and the export no longer draws them.
