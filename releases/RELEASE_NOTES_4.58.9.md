**QWebMap 4.58.9**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Changed
- **Preview a web map exported earlier.** *Preview* and *Open folder* used to be enabled only after an export in the same window. They are now enabled whenever the output folder holds an exported web map under the current address name, also one exported in an earlier session, and *Preview* opens that map. Changing the folder or the address name updates them.
