**QWebMap 4.49.1**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
- **Sharp lines on scaled screens again.** 4.49.0 drew the web map at one device pixel per CSS pixel in *Low memory web map*; on a screen scaled 125 % (Windows) the browser stretched it and every line blurred. The map is drawn at the screen's own pixel ratio again, at most 2 (phones). The other memory savings of 4.49.0 stay: the shared label source and the label leak fix.
