**QWebMap 4.55.0**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Changed
- **No raster tile limit.** A raster layer of more than 400 000 tiles is no longer refused. Before the export, a *Very large raster layer* warning says the export will take hours and make a very large web map, and for each such layer names the setting that makes it large (its *Sharpest detail*, or the Map tab's *Maximum tile zoom* for "Like the map") and what brings it down: the tile count one detail step coarser, the coarsest step that gets under 400 000, and how much smaller the extent should be. *Export anyway* goes on, Cancel stops. The export log warns too, and the layer's tile estimate in the Interaction tab flags it.
- **English is the default viewer language** of new settings (*Language of the viewer*, Map tab). Saved settings keep their language.
- **User guide on phones.** The [user guide](https://danzig666.github.io/QWebMap/usage/) has a *Contents* button that opens the table of contents on narrow screens. Clearer wording of the attribute filter and the large-raster warning.
