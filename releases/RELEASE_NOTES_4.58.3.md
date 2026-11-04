**QWebMap 4.58.3**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Faster
- **Polygon labels on the visible part are much lighter zoomed out.** These labels (*Polygon labels: Visible polygon*, and QGIS's default *Centroid: visible polygon*) are placed by the viewer as the map moves. On a dense layer zoomed out, it did far more than needed:
  - It prepared a label for nearly every polygon around the screen, in advance, without checking whether they overlap: 26 523 labels at zoom 12 on a 100 000-parcel test layer, of which 523 showed. Every one was sent to MapLibre and laid out there. Now the labels prepared in advance keep clear of each other as they will on screen: 746 are written, and the same 523 show.
  - It read and clipped every polygon on every update. A polygon wholly on the screen, or wholly off it, now gets its label at a point computed once per tile; only polygons at the screen's or a tile's edge are clipped (each decoded once).
  - While the map moves, an update waits twice as long as the last one took, so a heavy map keeps drawing its frames.

  On the test layer at zoom 12 (Chrome with software graphics, so compare the numbers with each other): main-thread work 74 s → 33 s, worker work 25 s → 1.1 s, a frame while panning 1.3 s → 0.27 s (median), time until the map settles up to 7 s → up to 2.6 s. The labels on screen are the same. The browser keeps up to about 50 MB more for the cache at the most zoomed-out heavy zooms.
  - Applies to *Over point* / centroid placement; *Horizontal*, *Free*, *Around point* and line labels keep the previous path (with the first and last change above).
