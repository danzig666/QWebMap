**QWebMap 4.61.1**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
- **The local viewer starts when another program uses port 9000.** The viewer of an exported package (*activate_server*) used to stop working if another program (MinIO, PHP-FPM, Portainer, a development server …) already listened on port 9000. Now the tile server takes the next free port (9001, 9002 …), and the viewer, its style and the browser all use the port it got. The program on port 9000 is left alone.
- Starting the viewer again stops only the earlier QWebMap tile server, whatever port it took, so hidden servers do not pile up.
- On Windows the tile server no longer shares a port with another program, and it keeps its port when a viewer tab is still open.
