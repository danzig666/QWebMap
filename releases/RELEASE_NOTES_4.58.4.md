**QWebMap 4.58.4**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Faster
- **Visible-polygon labels with *Horizontal*, *Free* and *Around point* placement are 2–3 times lighter zoomed out.** 4.58.3 sped up *Over point* labels; these placements now get their share:
  - Zoomed out, most small polygons lie under a label placed before them. Finding a free spot in each of them was most of the work (61 % of an update), only to find none. A polygon wholly inside such a label's box is now skipped at once.
  - Every polygon is decoded once per tile for every placement (lines too), and what depends only on a whole polygon is computed once per zoom: its ranked candidate spots (*Horizontal*), its angle (*Free*), its centroid and the positions around it (*Around point*), its label's size.
  - Fewer allocations while looking up nearby labels.

  One label update on a 100 000-parcel test layer (Chrome with software graphics, so compare the numbers with each other), zoom 12 / 13 / 14:

  | | 4.58.3 | 4.58.4 |
  |---|---|---|
  | Horizontal | 3.6 / 2.6 / 1.2 s | 1.1 / 0.65 / 0.4 s |
  | Free | 3.6 / 2.7 / 1.25 s | 1.2 / 1.0 / 0.7 s |
  | Around point | 1.7 / 1.0 / 0.33 s | 1.4 / 0.7 / 0.25 s |

  The labels are the same: compared with 4.58.3 on 540 random layouts (the three placements, panned views), not one differed.
