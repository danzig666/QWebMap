**QWebMap 4.58.6**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
- **The helper processes start on QGIS 4 for Windows.** Big exports hand the datasets to helper QGIS processes. On QGIS 4 for Windows they never started (export log: *worker message: PyQt6.QtCore.QDateTime not allowed*): its PyQt6 sends a date variable of the project (such as `@project_creation_date`) in a form the helpers refused, so every export ran in QGIS itself, slower. Qt dates, times, colours and similar values are now accepted (everything else is still refused).
