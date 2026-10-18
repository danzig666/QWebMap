**QWebMap 4.49.0**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Changed
- **Less browser memory on scaled and high-resolution screens.** *Low memory web map* (on by default) now draws the map at one device pixel per CSS pixel. The map's WebGL buffers grow with the square of the screen's scale: on a 1920×1080 screen scaled 150 % they took 160 MB, now 50 MB (a city map's page: 464 → 355 MB after loading, 692 → 523 MB after browsing). On such screens the map looks a little softer; turn the option off for full sharpness.
- **Labels placed on the visible part of their polygon or line share one source** instead of one per layer (14 on a city map), each with its own tiles and index in the browser.

### Fixed
- The label placement kept an entry for every feature it had ever labelled, so browsing a large map grew the page's memory without end.
