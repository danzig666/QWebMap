**QWebMap 4.53.3**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
- **Active view after switching a group off.** The view bar marks the view you picked as active until the layers shown change. Switching one layer off already unmarked it; switching a whole group off did not — the view stayed marked although the map no longer showed it. Now it is unmarked, and switching the group back on marks it again.

Re-export the map to get the fix (the web map code is part of each release).
