**QWebMap 4.61.2**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
- **QGIS could crash when making a map** (seen with QGIS 3.44 on Windows). The zoomed-out load check that runs before an export read a sample of each layer's features by feature id, and GDAL crashed doing that for some data. It now reads each layer once over the area and keeps a random sample as it goes. That is also faster for formats where reading by id is slow (GeoJSON, CSV …).
- **The simple view no longer freezes on large projects.** Measuring the layers (for *Choose automatically* and for where the preview looks) now runs in the background, with a busy bar under the preview while it works; the window keeps responding. Measuring and drawing stop when a map is made, when you switch to Advanced, or when the window closes.
