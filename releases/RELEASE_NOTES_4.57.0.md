**QWebMap 4.57.0**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### New
- **Dense layers stay visible zoomed out, but lighter.** A new *Zoomed out* column in the Interaction tab's layer table sets how a vector layer is drawn when zoomed out beyond a zoom, instead of hiding it there (double-click the cell, or *Selected layers → Zoomed out…*):
  - **merged** — the features of one style (and the same filter values) are joined into one shape per tile. Much lighter for parcels or buildings; the outlines between joined features and their popups are gone at those zooms, attribute filters still work. The idea follows the "coalesce" and building-merge steps of tile tools such as Tippecanoe and Planetiler.
  - **image** — QGIS renders the layer's symbols as image tiles there, exactly as in QGIS: the lightest. No popups or highlighting at those zooms, and the layer's category switches do not affect the images; its switch and opacity do.
  - The labels stay as text in both, and from the chosen zoom on every feature is drawn as usual.
