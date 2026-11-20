**QWebMap 4.61.0**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

A bug-fix release: a full code audit of 4.60.0 found 122 problems (2 serious ones, 52 medium, 68 small). Nearly all are fixed here; the few that are not are listed at the end.

### Most important fixes
- **A false "absolute local path" stopped exports at the very end.** The leak check took any text with a letter, a colon and a line break (for example `Zone:` and a new line in a popup) for a path on your computer. JSON texts are now read as they will be shown; the manifest texts are checked at the start of the export.
- **Online publishing with an old boto3/botocore** (Linux distribution packages) failed on every conditional upload. Only an SDK that supports them is used now; otherwise the plugin's own copy, as a whole. Every S3-compatible service now gets request checksums only when required (newer SDKs broke many services, not only R2).
- **Screen-unit line offsets with a near-reversing vertex** crashed the export (OverflowError).
- **Features near the antimeridian** (Fiji, Chukotka) were dropped from geographic-CRS layers when the area was wider than the world.
- **Heatmaps in a geographic or foot-based project** were drawn hundreds of times too faint.
- **Scale rules with feature-dependent comparisons** (`"rank" -5 < 3`, `level_1 > 2`) were taken for scale thresholds: features were shown at the wrong zooms or never.
- **HTML labels:** a span setting only a font size scaled the whole label; characters written as entities (`&eacute;`, `&#8364;`, `&nbsp;`) had no glyphs; `</p>` and `</div>` added an empty line.
- **Raster images of vector layers** ignored a new layer filter (stale images showed filtered-out features).
- **Inner effects** failed for whole rule groups when the direction window reached a line's end.
- **Release safety:** the release workflow now rebuilds the plugin zip from the tagged commit and compares it, and requires the branch's tests to have passed.

### Export
- Cancel while layers are read or datasets are written cancels cleanly (no partial map); intermediate files are deleted as each layer is done, not at the end.
- A layer's own `fid` field keeps its values; long layer ids no longer make work file names too long; locked half-written files fail one layer, not the export.
- Interval markers with blank segments work in file chains; a smooth() expression with accented field names works.
- Boolean data-defined properties that read `@map_scale` work; properties that aggregate another layer's field are no longer switched off; diagrams follow the layer's scale range and the web-only limits.
- Web Mercator projects are recognised by their definition (ESRI:102100, EPSG:3785 …), not only by EPSG:3857.
- Data-defined label quadrant, offset and distance are reported (the style keeps their fixed values) instead of silently writing unused tile fields. Text-format data-defined properties are reported too (a strict export stops on them).
- Hatch spacing and arrow sizes in "meters at scale" are converted (feet CRSs); a filled line keeps its opacity, offset and data-defined width/colour.
- Sprites: pixel sizes inside sub-symbols are oversampled correctly; fallback pattern previews are small (huge sprite sheets are warned about); long callouts are not cut off.
- A failed frame, balloon or callout image keeps the labels (without the image); an outer glow keeps its colour's transparency; label obstacles are prepared in one pass (minutes faster on large projects).
- Style variants read distinct values with SQL, cached (millions of features stalled the style build).
- The tile cache notices changes that decide line joining (an added line offset or pattern); helpers that start keep QGIS responsive; Cancel works during merging and joining; a nested GDAL guard can no longer deadlock.

### Publishing
- The output folder is locked from the start of the export (a lock left by a crashed QGIS is removed), not only at the end.
- A local map is replaced safely: the site move is planned first, retried on a file in use, and an incomplete release is removed. Earlier work folders are removed; local copies of online releases are kept to two.
- *MBTiles only* now writes an MBTiles; one MBTiles and ZIP per export, replaced and shown.
- Raster layers use this project's zoom ↔ scale, not the previous export's.
- A project CRS with a local grid file is published without the file's path.
- Terrain builds its overviews only for the DEM around the area (not a whole national DEM), and Cancel stops it.
- Search: prefix search finds records in every script (Devanagari, Thai, emoji …).
- Basemap: a dropped connection is retried; damaged archives give a clear message; tiles are no longer all held in memory.
- S3: a lost multipart completion answer is accepted when the object is there; a wrong computer clock is named; retention keeps uploads that may still be running.
- The disclosure review lists each feature's display label and its fields (published for deep links).
- The Windows long-path risk is said at the start of the export.

### Publish window
- The simple view no longer overwrites the zoom levels (and the saved settings) just by being shown; imported settings keep their zooms.
- *Visible scales…* on several rows never produces an inverted (never shown) range; such saved ranges are warned about.
- **Publish** reuses the last local export only if the layers' data, style, source and CRS are unchanged.
- *Make a ZIP to send* packs only the map's current version and reports disk errors without leaving half a ZIP.
- Settings files with the object storage keys are saved readable by you only.
- Unloading the plugin during a local export cancels it.

### Local viewer and server
- The local tile server only answers this computer's pages (no `Access-Control-Allow-Origin: *`: other websites could read the exported map).
- The launchers stop only an earlier QWebMap tile server, never another program on port 9000; Windows folders with `& ( ) ^ @` and network (UNC) folders work; the macOS server's Python is found.
- Export folders with `#`, `?` or `%` in the path open.
- The Processing export reads an extent without a CRS in the project's CRS and refuses a missing extent.

### Web viewer
- Polygon label placement on thin, long polygons no longer blocks the page for seconds; labels near the antimeridian are placed.
- Map-unit label sizes with limits (`max`, `min`, `case`, `match` …) are measured right for collisions.
- A server that ignores range requests sends the search pack once, not once per shard.
- Long permalinks drop their longest lists, not the view.

### Tests and CI
- CI tests QGIS 3.44 (the declared minimum) instead of 3.34; MapLibre parity, JS/Python parity and real S3 SDK tests run instead of being skipped; the nightly test selection includes every plugin file.

### Not fixed (known limits)
- Another program already listening on port 9000 still keeps the local viewer from starting (that program is no longer stopped).
- Network actions in the upload dialogs (test connection, list releases) still run in the window's thread.
- Very large archives are hashed again on each publish (slow, not wrong).
- Long Windows paths are only warned about.
- The S3 SDK choice applies to the whole QGIS process (documented).
- Two exports at the same time in one QGIS still share some global state (most of it is now per export).
- Repeated `fid` values in multipart sources keep QGIS's limitation.
- The Windows launcher quoting fix is tested on Linux only.
