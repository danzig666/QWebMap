**QWebMap 4.58.10**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### Fixed
A full bug and usability review of the plugin; the main fixes:

**Publishing**
- **A login written into a live layer's address is no longer published.** A web tile or WMS layer whose address holds a user name and password (`https://user:password@host/…`) was loaded live and its address, password included, went into the published files. Such a layer is now rendered into the release like other layers that need a login.
- The leak check before an upload reads large archives in blocks instead of whole into memory (a several-GB map could run out of memory). Web addresses containing `/home/` or `/tmp/` and attribute values shown in popups or search are no longer reported as local paths.
- Object storage: file checks (HEAD) and downloads are retried after a temporary error, like uploads; one failed check no longer stops an upload of thousands of files. The upload journal is written faster.
- Unusual server answers in the check after publishing are reported as failed checks instead of "Publishing failed".
- Preview server: a file replaced during a request no longer leaves the browser waiting.

**Export**
- A rule filter calling a function that was not loaded (a plugin's, a project macro's) is no longer remembered as an empty layer: the next export with the function available draws it.
- *Merged when zoomed out* also merges the classes of layers with more than 100 classes.
- On Windows the helper processes start side by side (QGIS no longer freezes while each one starts).
- An interrupted copy or layer preparation leaves no half-written file that a later export would reuse.
- The local viewer starts from folders with non-ASCII names (e.g. `C:\Users\Kovács\…`).

**Style conversion**
- Marker sizes, marker-line intervals and inside-polygon strokes in *meters at scale* are right in projects in degrees or feet.
- Paint effects set to *Render only* are drawn and *Modifier only* ones are not (it was the other way round).
- A data-defined opacity of a symbol or label replaces its own opacity, as in QGIS (it was multiplied); a label buffer keeps its opacity under a data-defined colour.
- Projects in US survey feet and other non-metre units scale line widths and sizes correctly.

**Publish window**
- Closing the window with changes that cannot be saved asks first instead of dropping them.
- The window fits a 1366 × 768 screen: the wide tabs scroll.
- The layer list follows layers added, removed or renamed in the project while the window is open.
- *Local only* shows no upload fields, cost or approval; without a basemap its settings are greyed out.
- *Cancel* in the import question imports nothing; choosing *Current map view* again brings back the question before the export; an extent layer that was removed falls back to the map view; a world layer's extent is cut to what a web map can show.

**Web viewer**
- Range and value filters treat features without a value the same on the map and in popups.
- A basemap that failed to load can be chosen again; search works again after a failed index load.
- The links of a map with deep links off no longer carry the selected feature; long drawings stay in shared links.
- With popups off, clicking a parcel still opens the parcel report; the legend can switch on layers of switched-off groups.
- Escape closes the popup, keyboard focus is visible, map controls are labelled in Hungarian, colours have more contrast, copying a link says whether it worked, buttons are 44 px on phones, and the short address's loading page is in the map's language.
