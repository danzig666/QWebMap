**QWebMap 4.58.5**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
- **QGIS 4 could close while exporting a map with raster layers.** While the export renders raster layers (and zoomed-out images, terrain), the tiles are made in the background; that part also opened the export's GeoPackages with GDAL inside QGIS. On QGIS 4.2 for Windows the two met inside GDAL and QGIS closed without a message (the export log showed an access violation). The GeoPackages are now opened with the GeoPackage driver only (GDAL no longer tries all its drivers on them), and the background work with GDAL waits while raster layers are rendered. The tile cutting itself goes on meanwhile: a test project with two DEM layers and 107 layers exported in the same time as before.
- **Why the helper processes did not start is now in the export log.** Big exports use helper QGIS processes; when they cannot start, the export goes on in QGIS itself (slower). `export_log.txt` now includes their error message, which was only in a temporary folder.
