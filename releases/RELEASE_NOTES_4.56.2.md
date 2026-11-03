**QWebMap 4.56.2**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
- **Terrain export about 10 times faster.** The *Elevation layer (DEM)* (Basemap tab, Terrain) was very slow to export with a detailed DEM: the area around the DEM was filled anew at every zoom, which took minutes at the highest one, and every zoomed-out level read the whole DEM. The surroundings are now filled once at the lowest zoom and each zoom above takes them from the one below; the zoomed-out levels are read from a pyramid of the DEM built once. A 1 m DEM of a town: 185 s → 16 s. The heights inside the DEM are unchanged, and the fill joins the DEM's edge more smoothly than before.
- **The elevation layer can be removed.** Deleting the text of *Elevation layer (DEM)* put the layer back; an emptied box now means *(no terrain)*, and the box has a clear (✕) button. The same for the other layer boxes that offer "no layer".
- **Raster copies only where they help.** 4.56.1 warped every raster in another CRS to Web Mercator once; for a detailed raster in a national grid (a DEM in EOV) that took longer than it saved. A copy is now made only where the reprojection is strongly curved (a polar image), and never for a hillshade, which QGIS shades by its pixels' size in the layer's own CRS.
