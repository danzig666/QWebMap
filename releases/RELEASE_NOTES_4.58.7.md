**QWebMap 4.58.7**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Changed
- **The export log names the raster layer being drawn.** A crash inside QGIS's own raster rendering ends QGIS 4 on Windows without a message, a report window or an Event Viewer entry, and the raster part of the export wrote nothing to `export_log.txt`. Each raster layer (its provider, renderer, coordinate system, zooms and how many tiles are drawn at once), each of its zooms and the terrain are now noted there as they start, so the last lines show what QGIS was drawing.
