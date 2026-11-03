**QWebMap 4.57.1**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
- **Zoomed out: smaller tiles from the chosen zoom on.** A layer drawn *merged* or as an *image* below a zoom gave all its polygon labels an extra copy of the polygons, also at the zooms where every feature is drawn as usual. That made those tiles about half again as large. The copy is made only for labels shown below the chosen zoom now; from that zoom on the tiles are the same as without the setting.

Measured on a synthetic layer of 100,000 parcels, zoomed out below zoom 15 (software graphics, so the times are relative):

| | Every feature | Merged | Image |
|---|---|---|---|
| Export | 112 s | 110 s | 28 s |
| Map settles at zooms 11–14 | 1.6–12 s | 0.1–1.1 s | 0.1–1.0 s |
| Downloaded | 9.6 MB | 0.4 MB | 2.6 MB |
| Browser memory | 359 MB | 14 MB | 31 MB |
