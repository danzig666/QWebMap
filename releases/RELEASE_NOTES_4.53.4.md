**QWebMap 4.53.4**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
- **Horizontal polygon labels where QGIS puts them.** Polygon labels with *Horizontal* placement went to the point of the polygon with the most room; QGIS picks among candidate spots by their room from the polygon's edge and the map's edge, *and* by their nearness to the polygon's centroid. A long strip was labelled at its wider end instead of its middle, and the label moved with the zoom. The web map now uses QGIS's candidates and costs: measured against QGIS, the label sits within a few pixels of QGIS's at every zoom tested. A strongly concave polygon (an L or U shape) can still be somewhat off: QGIS first cuts such a polygon into pieces, which the web map cannot do.

Re-export the map to get the fix (the web map code is part of each release).
