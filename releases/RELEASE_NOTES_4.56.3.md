**QWebMap 4.56.3**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### New
- **Map only.** *Map only: nothing on screen but the map* (Interaction tab) publishes a page that shows only the map: no title, panel, legend, buttons, scale bar, popups or search; visitors can still pan and zoom. The attribution of the map and its basemap stays in a corner when there is one (their licences require it). The other viewer options are greyed out while it is on.
- **Zoom readout for checking (`?debug`).** Add `?debug` to the map's address (before any `#`): a box above the scale bar shows the map's zoom and the zoom of the vector tiles drawn there ("overzoomed" past the last tile zoom). `?debug=tiles` also draws the tile boundaries. Visitors do not see it unless they add it themselves.
