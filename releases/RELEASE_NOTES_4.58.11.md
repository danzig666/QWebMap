**QWebMap 4.58.11**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
- **Expressions in a CRS without an EPSG code.** For a layer or project in a CRS that has no authority code — a `.prj` that QGIS cannot match ("Unknown CRS"), or a custom CRS made in the project and not saved as a user CRS — the export evaluated expressions in Web Mercator instead of in that CRS. `$area`, `$length`, `$x`/`$y` in labels, filters and data-defined properties, distances in geometry generators (`buffer(@geometry, 10)`), map-unit fill offsets and pattern positions were off: in Hungary an area came out about 2.2 times too large. They are now evaluated in the layer's or project's own CRS, as QGIS does.
