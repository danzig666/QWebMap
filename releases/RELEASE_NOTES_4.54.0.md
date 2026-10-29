**QWebMap 4.54.0**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### New
- **Views publish their layers.** Ticking a map theme under *Map themes offered as views in the web map* (Map tab) now publishes the layers that theme shows, visible at start. It only adds: no layer is unpublished, so several themes can be combined. Before, a view could show layers that were not published (they were simply missing from it).
- **Slow-map check before export.** Before each export the plugin estimates how heavy the web map will be zoomed out (the same estimate as the *Zoomed-out load…* button). When some layers would make it slow, it says which ones and from which zoom their features or labels are worth drawing: *Make it faster…* opens the suggestions (applied with one click, then the export goes on), *Export as it is* keeps the settings. Tick *Don't check this before exports* to switch the check off; the *Zoomed-out load…* button still works.

### Changed
- **Larger plugin icon.** The icon had a wide transparent margin and looked smaller than the other toolbar icons; it now fills its square.
