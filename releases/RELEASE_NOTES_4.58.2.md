**QWebMap 4.58.2**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Changed
- **Sharper, thinner lines in zoomed-out images.** A layer drawn as images zoomed out (*Zoomed out* column: *image*) was rendered at normal resolution, so QGIS's hairlines (zero-width lines, e.g. parcel boundaries) were a full pixel wide there and blurred on high-resolution screens. A dense parcel grid looked filled in, which is what *Thin hairlines* (Output options, on by default) avoids for the vector lines. With that option on, the images are now rendered at twice the resolution: their hairlines are as thin as the vector ones, every other size stays the same, and the lines are sharp on high-resolution screens. The images are about three times larger (100 000 parcels below zoom 15: 3.6 MB → 10.1 MB, still a third of drawing every feature), and the export is barely slower.
