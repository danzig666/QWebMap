**QWebMap 4.52.1**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
- **Zoom to layer without the Layers tab.** When the web map has no Layers tab (*Layers tab* off: legend only), the legend already shows the layer on/off switches; now it shows the *Zoom to layer* buttons too, beside the switches — also for a layer that is switched off. Before, there was no way to zoom to a layer in that mode. Printed legends leave the buttons out.

Re-export the map to get the fix (the web map code is part of each release).
