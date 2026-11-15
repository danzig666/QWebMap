**QWebMap 4.59.0**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

Ideas from the November versions of the original plugin ([GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles)), reimplemented.

### New
- **No blank map on a fast zoom-in.** A layer that first appears at a zoom (buildings, parcels) is also written into the tiles one zoom lower, hidden there until its own zoom, so the map draws it straight away while the closer tiles load. Archives with dense layers that start late grow (up to about a third in a synthetic test with 20,000 buildings; usually much less).
- **Line pieces joined when zoomed out.** Where *Lighter tiles when zoomed out* leaves out features under half a pixel, lines of one style are first joined end to end, so a river or road network stored as many short pieces stays whole instead of breaking up (and the tiles get smaller). Lines drawn along their direction (patterns, offsets) are not joined. A joined line opens no popup at those zooms (zoom in for it).
- **Point symbols keep labels off them.** With *Features act as obstacles* on in a point layer's labels (the QGIS default), other layers' labels avoid its symbols, as in QGIS.
- **HTML labels with colours and fonts.** Each part of an HTML-formatted label keeps its colour, bold, italic, font family and size (up to 16 parts). Background colours of parts are not drawn (the fidelity report says so).
- **Use web zoom scales in QGIS…** (Map tab) sets the project's scale list to the scales of the web map's zooms, so scale ranges you set start and end exactly at a zoom.

### Changed
- **Label backgrounds** are drawn with their whole fill symbol (all its layers), not only its fill and stroke colour.
- **Wide text buffers** (more than about a fifth of the text height) are drawn as a rounded box behind the text, as QGIS draws them, instead of a halo that turns boxy.
- **QGIS's own ogr2ogr** is used: looked for next to QGIS first, then on PATH, and tried before use, with QGIS's GDAL and PROJ data passed on. The export log names the ogr2ogr and its version. A different GDAL earlier on PATH no longer breaks the export.
- **Faster first view:** label fonts are uploaded to R2/S3 compressed (about a fifth of the size); labels fade in over 100 ms instead of 300 ms.
- A scale within half a unit of a zoom's exact scale counts as that zoom (1:1066 no longer adds an extra zoom of tiles).

### Fixed
- Labels with *Draw labels* off (obstacle-only labeling) were exported and drawn.
