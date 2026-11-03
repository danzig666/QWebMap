**QWebMap 4.58.1**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Changed
- **Zoomed-out load suggests *Merged* only where merging keeps the look.** Merging joins the features of one style into one shape, so the check now reads the layer's symbology. *Merged* is suggested for polygon layers drawn with plain fills of up to 64 styles. *Image* is suggested instead for:
  - **outlines** (the ones between the features would be lost), unless fully transparent;
  - pattern, gradient, shapeburst, SVG, raster and other special fills (laid out once over the joined shape);
  - data-defined styling (nearly every feature is its own style);
  - draw effects;
  - more than 64 styles;
  - inverted-polygon and 2.5D renderers.

  The tooltip says why; *Merged* can still be chosen by hand. The estimate of a merged layer grows with its number of styles.
- Note: the default QGIS polygon style has an outline, so most parcel layers get *Image* unless their outline is switched off.
