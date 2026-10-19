**QWebMap 4.51.1**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed (a full bug check of the QGIS 4 symbology added in 4.51.0)
- **Marker and hash lines**
  - *Trim distance* and *blank segments* were measured in the wrong units for vertex, first/last vertex, segment-centre and central-point markers when the project's coordinate system is not Web Mercator. Now they are measured in the project's units, like QGIS.
  - Data-defined trims, blank segments and extra items now see the layer's own coordinates and variables (`@layer_name`, `$length` on the project ellipsoid) and the whole multi-part feature; `@map_scale` is evaluated per zoom, and `@geometry_part_num` / `@geometry_ring_num` are set.
- **Labels**
  - Long *stretched* curved labels (wider than about 1000 px) were cut off or not drawn. They are now laid out character by character along the line, each with its own collision box; word stretching is now exact.
  - *Place characters at vertices* put the characters on the wrong vertices of multi-part polygons, drew the whole text at every vertex for HTML-formatted labels, and split emoji and accented characters. All three now match QGIS.
  - *Split label text lines over parts* now gives part i its line even when a rule leaves out other parts, and splits a geometry generator's parts, as QGIS does. Data-defined wrap characters and line lengths are applied.
  - A data-defined *label every part* value is read exactly as QGIS reads it.
- **Masking**: a mask marker that is switched off, or that masks only layers that are not published, no longer covers the map below with the background colour (also on QGIS 3).

Projects that use none of these options export exactly as before. Re-export the map to get the fixes.
