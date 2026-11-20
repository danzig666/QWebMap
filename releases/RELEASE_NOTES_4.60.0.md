**QWebMap 4.60.0**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### New
- **Simple view.** The Publish window has a **Simple** view for first web maps and occasional users. It shows only the essential settings, in plain words:
  - **Title.**
  - **Layers:** *On the map*, and *Show its information when clicked* (a click shows the feature's attributes, without ids; anyone who opens the map can see them). *Use the layers visible in QGIS* ticks the layers visible in QGIS.
  - **Area:** what the QGIS map shows now, or a layer's extent, with its size and tile count.
  - **How close visitors can zoom** (see below).
  - **Background map:** none or OpenStreetMap.
  - **Save in folder.**

  One **Make web map** button makes it on this computer, then **Open in browser**, **Open folder** or **Make a ZIP to send**. **Advanced** shows every setting as before (publishing online included); the two views show the same settings, so switching at any time changes or loses nothing, and settings that only the advanced view shows are kept and listed. The window asks once, the first time it is opened, which view to start with; if you used the window before, it stays advanced.
- **How close visitors can zoom, as a map scale.** In the simple view the detail is a QGIS map scale (1:100 000 to 1:500, in your project's CRS) instead of a zoom level. *Choose automatically from the project* (on for new settings) picks the scale at which the smallest typical features of the published layers are clearly visible, at least what a layer that only appears when zoomed in needs, and less for very large areas; it says why. A **preview** draws your layers as QGIS does at that scale, where the area has most detail.
