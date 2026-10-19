**QWebMap 4.50.3**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### New
- **QGIS 4 (Qt6) support.** The plugin is now marked Qt6-ready, so QGIS 4 lets you install it. The whole test suite (unit, QGIS integration and browser tests) passes on QGIS 4.2. QGIS 3.44 and later keep working as before.

### Fixed
- **Marker-line hatches on QGIS 4.** A *Line pattern fill* drawn with a marker line (arrowheads, dots along the hatch lines) fell back to an approximate image on QGIS 4. It is now the same exact QGIS tile as on QGIS 3.
