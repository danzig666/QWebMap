**QWebMap 4.56.0**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

Most of this release is ideas taken from the October–November 2026 versions of the original plugin, [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles), and reimplemented in QWebMap's own exporter and viewer. Each item names the idea it came from.

### Symbology
- **Symbol buffers** of marker symbols are drawn once around the whole symbol, under all its layers, as QGIS draws them (before: each layer got its own buffer). A font marker drawn as text gets its buffer as a text halo. *Idea: GallPeters/QGIS2VectorTiles (symbol buffer fix).*
- **Data-defined trims** of simple lines (*Trim lines* start/end) and **data-defined fill offsets** are exported per feature. *Idea: GallPeters/QGIS2VectorTiles.*
- **Point displacement labels**: the labels of a *Point displacement* renderer are shown next to the displaced points. *Idea: GallPeters/QGIS2VectorTiles.*
- **Arrows**: data-defined arrow widths, head length and thickness, offset, head type and arrow type follow each feature. *Idea: GallPeters/QGIS2VectorTiles.*

### Labels
- **Type case** (*All uppercase*, *Title case*, *Capitalize first letter*, …) matches QGIS, also when it is data-defined; leading and trailing spaces of the label text are kept. *Idea: GallPeters/QGIS2VectorTiles.*
- **Data-defined priority** decides which label wins a collision; **data-defined font family** is used per feature. *Idea: GallPeters/QGIS2VectorTiles.*
- **Force point inside polygon** keeps a polygon's label inside the polygon. *Idea: GallPeters/QGIS2VectorTiles.*
- **Callouts** of point labels: simple, Manhattan, curved and balloon callouts drawn as QGIS draws them (anchor, offsets, minimum length, corner radius, wedge width). *Idea: GallPeters/QGIS2VectorTiles (balloon and shaped callouts).*
- **Labels of visible polygon parts** ride in the polygons' own tiles instead of a separate copy of the polygons: smaller web maps, faster export. *Idea: GallPeters/QGIS2VectorTiles (labels read from the renderer's features).*

### Faster
- **Viewer start-up**: the viewer modules are preloaded and the style, the archives and the language are fetched at the same time. *Idea: GallPeters/QGIS2VectorTiles (parallel start-up).*
- **Export**: tiles are built in memory when the machine has enough free memory (on disk otherwise), rule filters that keep every feature are not copied, extent clips are cheaper, and JSON files are written compact. *Idea: GallPeters/QGIS2VectorTiles (in-memory ogr2ogr work database, compact JSON, faster GDAL export).*

### Security
- The export worker accepts only the plugin's own data from its pipe (an allow-list of classes), and non-security hashes are marked as such. *Idea: GallPeters/QGIS2VectorTiles (Bandit findings).*
