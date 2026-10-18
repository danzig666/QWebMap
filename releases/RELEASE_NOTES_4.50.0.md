**QWebMap 4.50.0**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### New
- **Live WMS and web tile layers.** An XYZ tile layer or a WMS layer of the project is now loaded by the visitor's browser from its own server, instead of being rendered into the release (*Load live from its server* on the *Interaction* tab, on by default for these layers). The release gets smaller and the map shows the service's current images. Conditions: an `https` address, no QGIS login, and a server that lets other sites' pages use its images (CORS — checked while exporting; if not, the layer is rendered as before, with a note in the log). Opacity, saturation, contrast and brightness are taken from QGIS. WMTS layers are still rendered.
- **WMS feature info.** A click on the map where no feature of the map's own layers is hit asks the visible live WMS layers what is there (GetFeatureInfo): GeoJSON, HTML tables or text, shown as plain text in the popup. If the server does not allow the page to read its answer, the popup offers a link that opens it in a new tab. The legend shows the server's own legend image.
- **Zoom to layer** (*Interaction* tab → *Zoom-to-layer buttons*, off by default): a button next to each layer in the web map's layer list zooms to that layer's features within the map's extent.
