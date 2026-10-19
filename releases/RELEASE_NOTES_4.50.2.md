**QWebMap 4.50.2**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
- **Angled labels showed level for a moment after panning.** On a heavy map, labels with *Free* (angled) placement — for example parcel numbers turned along narrow parcels — appeared horizontal when they scrolled into view and turned to their angle only once the map's tiles had loaded (up to a few seconds). The labels prepared just outside the screen now carry their angle, so they appear turned at once. Measured on a city map: from about 5 such labels per pan to about one in five pans.

Re-export the map to get the fix (the web map code is part of each release).
