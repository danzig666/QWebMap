**QWebMap 4.51.0**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### New: QGIS 4 symbology
QGIS 4 added new options to existing symbols and labels. These now come out on the web map as in QGIS (on QGIS 3 nothing changes):

- **Marker and hash lines**
  - *Trim distance* at the start and end (QGIS 4.2): markers and hashes are placed on the trimmed line.
  - *Blank segments* (QGIS 4.0): no markers or hashes inside the blanks, measured along each part and ring as QGIS measures them.
  - *Extra items* (QGIS 4.2): the extra markers or hashes at their own positions and angles.
- **Labels**
  - *Split label text lines over parts* (QGIS 4.0): each part of a multi-part feature gets its own line of the label.
  - Curved labels with *Place characters at vertices*: each character on its vertex, turned like QGIS.
  - Curved labels with *Stretch character spacing* / *Stretch word spacing*: the label fills the line (word spacing is approximate: the web map widens the spaces in whole steps).
- **Selective masking sets** (QGIS 4.0): labels and mask markers that mask through a masking set get the same halo and knock-out as masks with their own list.

Where the web map can only approximate something (for example markers placed by the browser at the highest zooms, or *Ignore whitespace in collisions*), the export report says so.
