**QWebMap 4.58.0**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Changed
- **Zoomed-out load suggests merged or image drawing.** The check (*Zoomed-out load…* on the Map tab, and before an export) suggested only hiding a layer, and only where its features are smaller than a pixel or two. A layer that is heavy where its features are still worth seeing (parcels, buildings) got no suggestion. Now such a layer gets one in the new *Drawn zoomed out* column: *Merged* (polygon layers) or *Image*, below the first zoom where every feature is light enough. It comes ticked when it draws zooms that *Features from* does not hide; untick *Features from* to keep the layer visible at every zoom out. *Apply the checked settings* writes it into the layer list's *Zoomed out* column.
- A layer already drawn merged or as images counts as such in the estimate (merged: about 5 % of the tile, images: no vector data), so the check before an export no longer asks about it. A mode set from too low a zoom gets a closer zoom suggested.
