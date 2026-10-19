**QWebMap 4.50.1**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

A full bug check of the plugin and the web map. No new features; about 50 fixes.

### Fixed — QGIS side
- **The Publish window opens on Python 3.10 and 3.11** (QGIS on most Linux distributions). It failed with a syntax error there.
- **Labels in fonts whose regular style is called "Normal"** (localized Windows, some Linux fonts) were invisible in the web map: their glyphs were not written.
- **Popups and search on copied layers.** Memory layers, layers with unsaved edits, joins or virtual fields could show another feature's attributes.
- **Shapefile encoding** set in QGIS (*Data source encoding*) is kept: non-ASCII text was garbled.
- **Project and layer variables** (`@my_width`, `@layer_name`) in styles and filters work; they were empty or named the temporary copy.
- **Export cache** notices edits of MapInfo (.tab) and other multi-file layers.
- **Rendering order by a geometry expression** (e.g. `$area`) is kept; interval markers on very large line layers are no longer lost.
- **Data-defined multi-line alignment** of labels works.
- **Values filters on decimal and yes/no fields** work in the web map (ticking a value hid everything).
- **An upload that finishes after the window was closed** no longer saves its settings into a project opened meanwhile.
- **Export no longer removes the project's own layers** that are not in the layer list (lookup tables of joins and value relations).
- While exporting, the rest of QGIS is blocked (removing a layer mid-export could crash QGIS).
- Changing the *Title* no longer moves an already published map to a new address.
- Bulk edits on a group skip layers hidden by the list's filter; *Visible scales…* on several layers changes only the limits you edit.
- Filter titles and collapsed groups are kept; picking the second of two layers with the same name works; *Preview* follows a new output folder.
- Uploads replace the map's entry page last, so a failed upload can't leave the live map broken.
- Live WMS/XYZ layers: without a max zoom they stop at zoom 18 (like QGIS); a WMS that cannot draw in Web Mercator is rendered instead of showing an empty layer; PNG8/WebP WMS images stay transparent; live layers are listed in the *Review* and need a new approval.
- The Processing tool reports a failure when nothing was exported.

### Fixed — web map
- **Labels after a jump** (search, link, zoom to layer) could stay missing until the next move.
- Popups, search and the parcel report retry after a network error instead of failing until reload.
- Search: *Enter* acts on what is typed (not on a closed list's result); the list no longer reopens stuck on "Loading".
- Long filter links keep their filters; links shared from an embedded map open the full map; locked layers can't be hidden by a link.
- Labels come back on when the map has no Layers tab; live layers appear in the visible-only and printed legend; the parcel regulations print with Street View enabled.
- Measuring: no stale snap ring after Enter/Escape; an elevation profile is not drawn for a cleared line, and a missing terrain tile leaves a gap; printing from 3D keeps the tilt; the overview map no longer loads Street View coverage.
- More exact label positions on small polygons.
