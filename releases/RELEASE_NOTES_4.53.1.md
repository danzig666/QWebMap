**QWebMap 4.53.1**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
- **Missing tiles in the preview after a new export.** When the map was exported again while a preview page (*Preview* in the Publish window) was still open, that page read the new tiles file at the old file's positions: at one zoom, or in one area, lines and fills disappeared and came back further in. The preview now tells the browser when the file has changed, and the page reloads it — the new export is drawn whole. Published maps on a server were not affected.

Update the plugin; no re-export needed.
