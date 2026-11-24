**QWebMap 4.61.3**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
- **Polygon labels could vanish for a whole layer.** Before a polygon label is placed, each feature's parts are merged (dissolved). At a low zoom the shapes are snapped to that zoom's coarse grid, and a few can become invalid (a ring touching itself). The merge then failed for the whole layer, and none of its labels were published ("Not published (rule failed): … The algorithm returned no output" in the export log). This happened for example on a whole-country map whose highest zoom is low. Such shapes are now repaired and merged again; failing that, the parts are grouped without merging. Labels shown only beyond the map's last zoom are drawn from its last tiles, as intended.
