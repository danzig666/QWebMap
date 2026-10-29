# QWebMap user guide

QWebMap publishes a QGIS project as a fast, accurate web map: vector tiles in one PMTiles file, a ready viewer, and a static site you can open locally, upload to Cloudflare R2 / S3 or copy to any web server. This guide is for QWebMap {version}, the generic edition. Everything is set in one window: **Web → QWebMap: Publish Web Map…** (or its toolbar button). The settings are saved in the project.

## Quick start

1. **Install.** Download `QWebMap-<version>.zip` from the [latest release](https://github.com/danzig666/QWebMap/releases/latest) (not the `-hu` file), then *Plugins → Manage and Install Plugins → Install from ZIP*. QGIS 3.44 or newer, or QGIS 4.
2. **Open the window:** *Web → QWebMap: Publish Web Map…*
3. **Map tab.** Enter a **Title**. Choose the **Extent**: the current map view, a layer's extent, or **Draw…** a rectangle. Tick **Publish** for the layers to put on the web map, or click **Publish the visible layers**.
4. **Interaction tab** (optional). For each layer, tick the fields to show in **Popup**, to **Search**, or to **Filter**. Only ticked fields become public.
5. **Export locally**, then **Preview**: the map opens in your browser from this computer. Fix what you see in QGIS or in the window, and export again (unchanged layers are reused, so it is faster).
6. **Publish online** (optional). On the **Destination** tab choose *Cloudflare R2* (see **Step-by-step: set up Cloudflare R2…**), *Other S3-compatible storage* or *SSH / SFTP server*. Fill in the fields and click **Test connection**. On the **Review** tab check what becomes public and tick the approval. Click **Publish**, then **Copy link**.
7. **Save the project.** The settings live in the project file. Save it after **Save settings** or **Close**.

> If the map is slow when zoomed out, use **Zoomed-out load…** on the Map tab (the export also offers it). For a raster layer (scanned plan, orthophoto), keep **Sharpest detail** at *Like the image*. Each extra zoom level makes about 4× more tiles.

## Map tab

### Web map

- **Title** — Map title shown in the viewer. Required. For new settings (never saved), editing it also updates the slug.
- **Address name (slug)** — The map's address and folder name, e.g. `maps/<slug>`. Use lowercase ASCII letters, digits and `-`, 1–64 characters. If you leave it empty, it is made from the title.
- **Description** — Short text about the map, shown in the viewer.
- **Language of the viewer** — Language of the viewer's interface: English (the default for new settings) or Magyar. Saved settings keep their language.
- **Attribution** — Credit or copyright text shown on the web map.
- **Logo (PNG/JPEG/WebP)** — Local image file shown in the viewer. Click **…** to browse.
- **Minimum tile zoom** — Lowest zoom (0–22) that gets tiles. Default 0.
- **Maximum tile zoom** — Highest zoom (0–22) that gets tiles. Default 16. Beyond it, the viewer enlarges (overzooms) the last tiles.
- **Maximum browser zoom (overzoom)** — How far visitors can zoom in (0–24). Default 22.
- **Extent** — The area to publish. **Current map view (at each export)** (the default): whatever the QGIS map shows when you export. **Extent of a layer**: follows the chosen layer when its data changes. **Fixed area (drawn or frozen)**: a fixed rectangle.
- **Show on map** — Briefly outlines the area that will be published on the QGIS map.
- **(choose a layer)** — The layer whose extent is published. Available only in the "Extent of a layer" mode.
- **Freeze view** — Fixes the published area to what the QGIS map shows now. Switches the mode to Fixed area.
- **Draw…** — Hides the window so you can draw the area on the map. Click one corner, then the opposite corner, or press and drag. Corners snap when QGIS snapping is on. Right-click or Esc cancels.
- **Keep the web map on the extent (no panning or zooming away)** — The map centre cannot leave the extent, and visitors can zoom out only a little beyond it. On by default.
- **Accent colour of the viewer** — Colour of the viewer's interface (#rrggbb, no opacity).

The text below the extent buttons gives the area's size in km and its bounds in degrees.

### Layers (publishing does not change the project's layer visibility)

- **Map theme:** — A QGIS map theme (View → Map Themes) for the two buttons next to it.
- **Publish its layers** — Publishes the layers visible in the theme and makes them visible at start. Also ticks the theme as a web map view. Additive: layers that are already published stay published.
- **Use as start view** — Sets "At start" to exactly the theme's visible layers. Because ticking At start publishes a layer, the theme's layers also become published.
- **Selected layers** — Menu of bulk changes for the selected rows (see the menu entries below). Right-clicking the list opens the same menu.
- **Publish the visible layers** — Publishes exactly the layers visible in the QGIS Layers panel now and makes them visible at start. A layer in a hidden group counts as hidden. All other layers are unpublished.
- **Zoomed-out load…** — Estimates which published vector layers slow the map down when zoomed out, and suggests limits (see the dialog below).
- **Filter layers by name…** — Shows only layers whose name contains the text (case- and accent-insensitive), plus the groups that hold them. If a group's name matches, the whole group shows.
- **Only published layers** — Hides layers that are not published.

Layer list columns:

- **Layer** — The QGIS layer tree: vector layers with geometry, and raster layers (marked "(raster)"). Group names are bold. Other layers are not listed.
- **Publish** — Includes the layer in the web map. A group's box shows whether all, some or none of its layers are published. Ticking or unticking the group sets all of its visible layers.
- **At start** — The layer or group is visible when the web map opens.
- **Switchable** — Visitors can switch the layer or group off.
- **Legend** — The layer is shown in the web map's legend. This is the same setting as "Show in the legend" in the Interaction tab. Layers only.
- **Scales** — Web map only: hides the layer when zoomed out or in beyond a scale. "labels 1:… –" hides only its labels. Grey "(QGIS …)" shows the layer's own QGIS scale range. Double-click the cell to edit it.

Right-click / **Selected layers** menu (a selected group applies to all its visible rows):

- **Publish** / **Do not publish** — Sets the Publish column.
- **Visible at start** / **Hidden at start** — Sets the At start column.
- **Can be switched off by visitors** / **Always shown (cannot be switched off)** — Sets the Switchable column.
- **Show in the legend** / **Hide from the legend** — Sets the Legend column.
- **Visible scales…** — Opens the scale dialog for all selected layers.

- **Map themes offered as views in the web map:** — Ticked QGIS map themes become views that visitors can switch between. Ticking a theme also publishes its layers.
- **Start with:** — The view the map opens with. **(the layer settings above)** (the default) uses the At start column. Only ticked themes are listed.

### Visible scales in the web map (dialog)

- **Hide when zoomed out beyond** — Hides the layer at scales smaller than this one (suggested value 1:25 000). It is not tiled there either, so the map is faster and the export smaller.
- **Hide when zoomed in beyond** — Hides the layer at scales larger than this one (suggested value 1:500).
- **Hide only the labels when zoomed out beyond** — Hides only the labels beyond this scale. The features are still drawn (suggested value 1:10 000).

With several rows selected, a limit appears only if every row has the same value. A limit you leave unchanged keeps each row's own value. Only the web map changes; the QGIS project does not.

### Zoomed-out load of the web map (dialog)

- **Find a layer…** — Filters the rows by layer name. Hidden rows keep their ticks.
- **Zoomed out, the web map should be:** — Slider from "slow, showing much" to "fast, showing little": Very slow, Slow, Balanced (the default), Fast, Very fast. Moving it recalculates the suggestions and replaces zooms you set by hand. The position is remembered.
- **Layer** / **Features** — Layer name and its feature count in the extent.
- **Busiest tile, zoomed out** — The layer's share of the heaviest tile at its current first zoom, in features and KB/MB.
- **Features from** — Tick box and zoom: hides the layer (features and labels) when zoomed out beyond this zoom. Suggested changes come ticked. Changing the zoom ticks the box. The lowest zoom means no limit.
- **Labels, zoomed out** — Labels in the heaviest tile and about how many fit.
- **Labels from** — Tick box and zoom: hides only the labels when zoomed out beyond this zoom.
- **Apply the checked limits** — Writes the ticked zooms into the Scales column as scales. The summary line compares the heaviest tile before and after.

**Pitfalls**

- "Current map view" publishes whatever QGIS shows at export time. Before each export you see "Published area" with the size and tile count. Click **Export this view** to go on. "Don't ask again for this project" turns this prompt off. To publish the same area every time, use a layer extent or a drawn area.
- If the extent layer is removed from the project, its last extent is kept and the mode becomes Fixed area.
- Changing the slug of a map that is already published gives it a new address and folder. The old address is not updated.
- A logo that does not exist or has another file extension is silently left out.
- If "Maximum browser zoom" is below "Maximum tile zoom", it is silently raised to the maximum tile zoom.
- Every extra tile zoom roughly quadruples the tile count. A high Maximum tile zoom over a large extent makes slow, large exports.
- The tick boxes depend on each other. Ticking At start also publishes the layer. Unpublishing it clears At start. Unticking Switchable makes it visible at start (and publishes it). Unticking At start makes it Switchable again.
- Bulk changes and group ticks affect only the rows the filter shows. Hiding rows with the filter also deselects them.
- A theme whose layers are not published shows nothing of them, so ticking a theme as a view publishes its layers. Untick them again afterwards if you do not want them.
- Web-only scales add to the layer's own QGIS scale range; they cannot show a layer outside its QGIS range.
- Zoomed-out load is an estimate from a sample of up to 2000 features per layer. It covers only published vector layers with features in the extent. If a "Labels from" zoom is not past the "Features from" zoom, it is dropped (the layer is hidden there anyway). A zoomed-out limit is not applied if it would conflict with an existing zoomed-in limit.
- Before each export, the plugin checks the zoomed-out load. If some layers are heavy, it asks: **Make it faster…** opens the dialog and then exports, **Export as it is** exports unchanged, and Cancel stops. "Don't check this before exports (the Map tab's Zoomed-out load… button still does)" turns the check off for good (QGIS setting).
- Raster tiles are capped at 400 000 per layer. "Like the image" on a sharp aerial photo over a large extent can exceed the cap.
- If QGIS cannot write WebP, the tiles are written as PNG (larger) and a warning is shown.

**Errors**

- "title: required" (Q2VT_PUB_PROFILE_INVALID): the Title is empty. Enter a title.
- "slug: lowercase ASCII letters, digits and '-', 1-64 characters": the slug is invalid, or it starts or ends with `-`. Fix the Address name.
- "accentColor: #rrggbb": the accent colour is not a 6-digit hex value. Pick a colour.
- "view: 0 <= minZoom <= maxZoom <= 22": Minimum tile zoom is above Maximum tile zoom. Lower the minimum.
- "Choose an extent." / "view.extent: [xmin, ymin, xmax, ymax] …": there is no usable area. Pick a layer, freeze the view, or draw an area.
- "This area is outside what a web map can show (web maps end short of the poles); the extent is unchanged.": the view or drawn area reaches past about ±85°. Zoom in and try again.
- "Select at least one layer to publish (Map tab) …": nothing is ticked in Publish. Publish at least one layer.
- "Layer … is not a vector or raster layer of this project." / 'Raster layer "…" cannot be read (invalid data source).': a published layer is missing or broken. Fix the layer, or unpublish it.
- 'Raster layer "…": about N tiles at zooms a-b; lower its maximum zoom …': the raster exceeds 400 000 tiles. Choose a coarser "Sharpest detail", a higher "Shown from zoom", or a smaller extent.
- "Nothing to publish: no published raster layer draws anything in the extent." (Q2VT_PUB_EMPTY_ARCHIVE): the extent does not cover the raster data. Check the extent.
- "Select layers (or groups) in the list first.": you opened Visible scales… with nothing selected. Select rows first.
- "The zoomed-out limit must be a smaller scale (larger number) than the zoomed-in limit.": the two limits in the scale dialog overlap. Fix one of them.
- "No published vector layer has features in the extent.": Zoomed-out load found nothing to analyse. Publish vector layers, or check the extent.
- "Zoomed-out load: cancelled.": you cancelled the estimate. Nothing was changed.

## Interaction tab

### Viewer

- **Labels switch** — A switch in the web map that shows or hides all labels. Default: on.
- **Opacity sliders** — An opacity slider for each layer in the Layers tab. Default: on.
- **Search** — One search box covering the fields ticked in the *Search* column, plus streets and house numbers if those are set. The feature found is zoomed to and marked, and its popup opens when *Popups* is on. Default: on.
- **Attribute filters** — Filters for the fields that have a *Filter* kind set (value lists with counts, number ranges, text). Default: on.
- **Popups** — A click on a feature shows its *Popup* fields. Default: on.
- **Shareable links** — A Share tab with a link to the current map (follows updates) and a link to this exact version. Links keep the view, layers, filters, basemap, selection and drawing. Default: on.
- **Coordinates (WGS 84 and the project CRS)** — Shows the pointer's coordinates in the Tools tab. Default: on.
- **Measurement** — Distance and area tools in the Tools tab. With terrain, measured lines also get an elevation profile. Default: off.
- **Print** — Prints a map extract of the current view at a chosen scale on A4 or A3, with legend, scale bar and header. Default: on.
- **Legend: only what is visible in the current view** — The legend starts in "only visible" mode. Visitors can switch it off. Default: off.
- **Layers tab (off: the legend only)** — Off: visitors get only the legend, with an on/off switch per layer. Default: on.
- **Map panel closed at start** — The web map opens with its panel closed, so more of the map shows. The menu button opens it. Default: off.
- **My location button** — Shows the visitor's location. Needs https and the browser's permission. Outside the map extent it shows a message and does not move the map. Default: off.
- **Search street names (OpenStreetMap)** — The search also finds named OSM streets inside the extent layer (Map tab), or inside the export extent if there is none. Only names, a point and bounds are published. Default: off.
- **Overview map (inset)** — A small overview map in a corner that marks the current view. Default: off.
- **3D view** — A 3D button: tilted view with the terrain relief (Basemap tab) and polygons raised by their *3D height field*. Default: off.
- **Drawing tools** — Points, lines, areas and text in the Tools tab. The drawing is kept in the shared link and can be saved as GeoJSON or KML. Default: off.
- **Zoom-to-layer buttons** — A button in each layer row of the Layers tab that zooms to the layer's extent. Default: off.
- **Street View (Google)** — A Street View button. Blue lines show where coverage exists, and a tap opens the panorama facing the tapped point. Turning it on enables the key field. Default: off.
- **Google Maps API key (needed for Street View)** — Your Google Cloud key, with the Maps JavaScript API and the Map Tiles API enabled. The key is visible in the published page.
- **House numbers** — A point or building layer with house numbers. The search then finds "street number" (e.g. "Main Street 12"). Only street, number and a point are published. Default: (none).
- **number** — The house number field. It is guessed from common names (hsz, housenumber, number…), otherwise left empty.
- **street (empty: nearest OSM street)** — The street name field. Empty uses the nearest named OSM street within 150 m.

### Layer list

- **Find a layer…** — Filters the layer list by name (case- and accent-insensitive). Shown only when more than 10 layers are listed.
- Layer list — Lists every layer ticked *Publish* on the Map tab, sorted by name. Select one to edit its settings on the right.

### Layer settings (vector layers)

- **Title in the viewer** — The layer name in the web map. Empty: the QGIS layer name.
- **Feature title (display expression)** — A QGIS expression for the search result and popup title (e.g. a parcel number field). Empty: the first search field.
- **Initial opacity** — Starting opacity, 0–1 in steps of 0.1. Default: 1.
- **Show in the legend** — Lists the layer in the legend. This is the same setting as the Map tab's Legend column. Default: on.
- **Feature links (deep links)** — Adds "Link to this feature" to popups. Default: on.
- **Label every feature (smaller where the label does not fit)** — Every feature gets its label. Labels that do not fit shrink to half size, or move to the roomiest point. None are dropped. Default: off.
- **Measurements snap to this layer (corners and edges)** — While measuring, points snap to this layer's nearest corner, or else its nearest edge. Hold Alt in the viewer for a free point. Default: off.
- **3D height field (m)** — Polygon layers only: a numeric field of heights in metres that the 3D view uses. Text fields holding numbers are listed with "(text)". Default: (none).
- **Field** — The layer's field names (read-only).
- **Popup** — Shows the field in popups and makes it public.
- **Popup title** — The field's label in the popup. Empty: the field name.
- **Type** — How the popup value is shown: string, integer, number, boolean, date or url (a safe link). Guessed from the field type.
- **Search** — Makes the field searchable, and public.
- **Feature key** — The field(s) that identify a feature for links. Values must be unique and never empty (e.g. a parcel number).
- **Filter** — The visitor filter: no filter, values, range or text. Makes the field public.

### Layer settings (raster layers)

- **Title in the viewer** — The layer name in the web map. Empty: the QGIS layer name.
- **Load live from its server (web tiles / WMS)** — XYZ or WMS layers only. Visitors' browsers load the images straight from the server, and a click on a WMS layer shows GetFeatureInfo. Disables the rendering settings below. Default: on.
- **Image format** — WebP (small, transparent; the default), PNG (sharp, transparent; larger) or JPEG (photos; no transparency).
- **Sharpest detail** — Ground size of one pixel when zoomed in fully: like the image or service (recommended), like the map, or a fixed size. Each finer step means about 4× more tiles.
- **Shown from zoom** — The lowest zoom the layer is tiled for. "as the map" uses the publication's minimum zoom.
- **Quality (JPEG/WebP)** — Compression quality, 1–100. Default: 85.
- **Initial opacity** — Starting opacity, 0–1. Default: 1.
- **Show in the legend** — Same as the Map tab's Legend column. Default: on.
- The estimate line below shows the pixel size, the maximum tile count, the zooms and any warnings.

**Pitfalls**

- Only layers ticked *Publish* on the Map tab are listed. Tick them there first.
- A field becomes public only if it is ticked in Popup, Search or Feature key, or has a Filter kind. The 3D height field also becomes public. Nothing else ends up in the release unless *Output* includes all fields.
- Without a Feature key, feature links only work in the same version of the map.
- *House numbers*, *Search street names* and field search all need **Search** on. Without it they silently do nothing.
- Choosing a House numbers layer with an empty *number* field silently drops the address search at save time.
- *Measurements snap…* needs **Measurement** on. *3D height field* needs **3D view** on, and is disabled for layers that are not polygons.
- **Street View** with an empty key is published as off, silently. The key is public: restrict it in Google Cloud to your site (HTTP referrers) and to the two APIs.
- **My location button** works only on https pages.
- Street search with no basemap reads streets from the latest Protomaps build, so exporting needs internet. Large areas take extra export time.
- Filter titles have no widget here. Values saved in the profile are kept.
- Raster *Load live* works only if the address is https with no login and no custom headers, the server allows CORS, and the source is not WMTS. Otherwise QGIS renders the layer into the release and the export log says why.
- Finer *Sharpest detail* or a lower *Shown from zoom* makes raster exports much larger (about 4× per zoom).

**Errors**

- `Q2VT_PUB_PROFILE_INVALID` "Layer "…": field "…" does not exist." — A ticked field was renamed or removed in QGIS. Reopen the layer here and fix the ticks.
- `Q2VT_PUB_PROFILE_INVALID` "Layer "…": display expression: …" — The *Feature title* expression does not parse. Correct it, or clear it.
- `Q2VT_PUB_PROFILE_INVALID` "House numbers: the layer is not in the project (Interaction tab)." / "House numbers: field "…" does not exist in "…"." — The address layer or field is gone. Pick them again.
- `Q2VT_PUB_IDENTITY` "Layer "…": N feature(s) have no key (… is NULL)." / "the key (…) is not unique, e.g. …" — Fix the data or choose another *Feature key* field.
- `Q2VT_PUB_PROFILE_INVALID` "Raster layer "…": about N tiles at zooms a-b; lower its maximum zoom or the extent (limit 400000)." — Choose a coarser *Sharpest detail*, a higher *Shown from zoom* or a smaller extent.
- `Q2VT_PUB_PROFILE_INVALID` "…opacity: between 0 and 1" / "rasterQuality: 1-100" — Only happens with an edited settings file. Fix the value.
- `Q2VT_PUB_BASEMAP` "Street search: the area needs N tiles (limit …)." — The street-search area is too large. Use a smaller extent layer.
- Warning "Street search: the street names could not be read (…)" / "no named street was found in the area." — The map is published without street search. Check the internet connection, the basemap source and the extent layer.
- Warning "House number search: the address layer or its number field is missing…" / "N house numbers have no named street within 150 m and are left out." — Set a *street* field, or check that the addresses lie inside the area.
- Info "Raster layer "…" is rendered into the release: it needs a login / its address is not https / … does not let other sites' pages use its images (CORS)" — Live loading is not possible. The layer is rendered instead.

## Basemap tab

- **Basemap shown at start** — What the web map shows first: None (switched off), one of the offered styles, or "Web: <name>". Default: the first style.

### OpenStreetMap vector basemap (copied into the release)

- **Basemap** — No basemap (only the project's layers), or OpenStreetMap vector basemap (Protomaps). Default: No basemap.
- **Download the area from the latest Protomaps daily build (internet needed while exporting)** — The source is the newest Protomaps planet build. Default.
- **Use this PMTiles file or URL (Protomaps schema):** — Uses the file or https URL in the box below instead.
- **…** — Browses for a local .pmtiles file and selects the option above.
- **Styles offered** — The styles visitors can switch between: Light, Dark, White, Grayscale, Black. If none is ticked, Light is used. Default: Light.
- **Most detailed zoom** — The highest basemap zoom copied, 0–15. Default: 15.
- **Area around the extent** — Extra detail area around the export extent, as % per side (0–1000). Default: 50 %.
- **Overview zooms (0 to)** — Zooms 0 up to this value cover the wider overview area. Capped at *Most detailed zoom*. Default: 7.
- **Overview area** — Side length of the overview area, 0–5000 km. Default: 300 km.

### Web basemaps (XYZ tiles or WMS, loaded from their server while browsing)

- **Use** — Offers the row in the web map's basemap menu. Rows that are not https cannot be ticked.
- **Name** — The menu name. For an existing QGIS XYZ connection it is the connection name (read-only).
- **Tile address (XYZ or WMS)** — An https:// template with {z}, {x} and {y} ({-y} for TMS, {s} for a/b/c servers), or a WMS template.
- **Attribution** — The credit text the service requires. It is saved into the QGIS connection too.
- **Min z** — The lowest zoom the service has. Default: 0.
- **Max z** — The highest zoom the service has. Default: 19 (20 for WMS).
- **Add new…** — Adds an editable empty row. Ticked rows are saved as QGIS XYZ connections (Browser → XYZ Tiles).
- **Add WMS…** — Opens *Add WMS* to add a WMS service as a basemap.
- **Reload from QGIS** — Lists the QGIS XYZ connections again, e.g. ones added in the Browser meanwhile.

#### Add WMS

- **WMS layer of the project** — Fills the fields below from a WMS layer in the project. Shown only if the project has one.
- **Name** — The menu name. Empty: the layer names.
- **Service address** — The https:// WMS address.
- **Layers** — WMS layer names, comma separated.
- **Image format** — image/png or image/jpeg.
- **Attribution** — The credit text shown on the map.

### Terrain (3D relief, hillshade, elevation profiles)

- **Elevation layer (DEM)** — A file-based raster of ground heights in metres. Online services are not listed. Default: (no terrain).
- **Hillshade: shaded relief drawn above the basemap (also in 2D)** — Draws shaded relief. Enabled only when an elevation layer is chosen. Default: on.
- **Height exaggeration in 3D** — Vertical exaggeration in the 3D view, 1–5 ×, in steps of 0.5. Default: 1.5 ×.

**Pitfalls**

- *Styles offered*, the size fields and the source matter only when *Basemap* is the Protomaps option.
- The PMTiles box is used only when its radio button is selected. Otherwise its text is ignored.
- An http:// basemap URL is allowed only for localhost.
- Large *Most detailed zoom*, *Area around the extent* or *Overview area* values multiply the tile count (limit 200,000) and the release size.
- *Basemap shown at start* matches by name. If the chosen entry is unticked or removed, it falls back to the first style, or to None.
- Web basemaps are never copied into the release: visitors' browsers load them live. Use only services you may use, with their required attribution.
- A row with no address is ignored. A Min z or Max z that is not a number silently becomes 0 or 19.
- WMS rows are not saved as QGIS XYZ connections. The service must support EPSG:3857 and allow use in web maps.
- Terrain heights become public (data/terrain.pmtiles). 3D relief needs *3D view* on (Interaction tab). Elevation profiles need *Measurement* on.
- A terrain failure does not stop the export: the map is published without terrain, with a warning.

**Errors**

- *Add WMS* "An https:// service address and at least one layer name are needed." — Enter an https address and a layer name.
- `Q2VT_PUB_PROFILE_INVALID` "basemap.xyz[i].title: required" / "'…' is used twice" — Give every ticked row a unique name.
- `Q2VT_PUB_PROFILE_INVALID` "basemap.xyz[i].url: an https:// tile address" / "needs {z}, {x} and {y} (or {-y}), or a WMS {bbox-epsg-3857}" / "only {s} may stand in the server name" / "a WMS address needs REQUEST=GetMap" — Fix the tile address.
- `Q2VT_PUB_PROFILE_INVALID` "basemap.xyz[i]: 0 <= minZoom <= maxZoom <= 24" — Fix Min z or Max z.
- `Q2VT_PUB_PROFILE_INVALID` "basemap.source: https:// URL (http only on this computer) or a local file" — Use https or a local file.
- `Q2VT_PUB_BASEMAP` "Basemap file not found: …" — Fix the path.
- `Q2VT_PUB_BASEMAP` "The list of Protomaps builds could not be read…" / "Basemap download failed…" — No internet, or the server failed. Retry, or use a URL or local file.
- `Q2VT_PUB_RANGE_UNSUPPORTED` "The basemap server answered … to a range request" — The URL's server does not support HTTP Range. Download the file and use it locally.
- `Q2VT_PUB_NOT_MVT` "The basemap source does not hold vector tiles." / `Q2VT_PUB_BASEMAP` "…is not in the Protomaps schema (no 'earth' layer)." — Use a Protomaps-schema vector PMTiles file.
- `Q2VT_PUB_BASEMAP` "The basemap area needs N tiles (limit 200000); lower its maximum zoom, padding or overview size." — Lower *Most detailed zoom*, *Area around the extent* or *Overview area*.
- `Q2VT_PUB_BASEMAP` "The basemap source has no tiles in this area." — The file does not cover your extent. Use another file, or the daily build.
- `Q2VT_PUB_BASEMAP` "No installed font for the basemap labels." — Install a system font (e.g. Noto Sans or DejaVu Sans).
- Warning "Terrain: "…" cannot be read as a file…" / "could not be read (…)" / "has no heights inside the extent." / "the elevation layer is not in the project" — Choose a local DEM that covers the extent.

## Parcel report tab

- **Clicking a parcel shows its report: area, parts cut by the zoning and the regulation lines, zones and restrictions** — Turns the parcel report on. The report is computed in QGIS at export time from exact geometry; only the result is published. Default: off.

### Parcels

- **Parcel layer** — Polygon layer of the parcels. Clicking one of its features in the web map opens the report.
- **Parcel id (unique, e.g. hrsz)** — Field that identifies a parcel. It also becomes the parcel layer's feature key in the tiles.
- **Parcel data shown** — Table of the parcel layer's fields. Tick a field to show it in the report.
- **Field (tick to show)** — Column of the field tables: the field name with its tick box.
- **Title** — Column of the field tables: the label shown for the field. Empty uses the field name.

### Zoning (parts of the parcel)

- **Zone layer (its style gives the zone colours)** — Polygon layer of the zones. The parcel is cut into parts by these zones. Each part gets the zone's legend colour.
- **Zone code field** — Field with the zone code (e.g. a zone code such as R1). It names each part. It is guessed from the layer's style or labels when you pick the layer.
- **Zone values shown per part** — Zone layer fields to show for each part. Tick the field, optionally give a title.
- **Lines that cut parcels** — Tick line layers (e.g. regulation lines, zone boundaries) that also cut the parcel into parts. Lists only line layers of the project.

### Restrictions (shown with their legend symbol when they touch the parcel)

- **Layer** — Tick a layer to use it as a restriction. Lists every spatial vector layer of the project.
- **Title** — Name of the restriction in the report. Default: the layer name.
- **Name field** — Optional field whose value names the feature (e.g. the protected site). Empty: no name.
- **Distance (m)** — Protection distance for line and point layers, 0–1000 m. Ignored for polygon layers. Default: 0.
- **Explanation** — One-sentence explanation shown with the restriction.
- **Legal reference** — Legal reference shown with the restriction (e.g. the article of the building act).

### Zone regulations table (optional, e.g. the local building code)

- **Table** — Optional table (any vector layer, also without geometry) joined to the zones by zone code. Empty: not used.
- **Zone code field** — Field of the table with the same codes as the zone layer's code field. Guessed by name when you pick the table.
- **Fields shown** — Table fields to show under each zone. Tick and optionally title them.
- **Full texts table** — Optional table with the full regulation text of each zone. The report shows it under the zone, opened on request. Empty: not used.
- **Its zone code field** — Zone code field of the full texts table. Guessed by name.
- **Its text field (HTML)** — Field with the text as simple HTML (headings, paragraphs, lists, tables). Guessed from names like html or text.

### Accuracy and notice

- **Ignore parts smaller than** — Parcel parts below this area are dropped as slivers, 0–1000 m². Default: 1 m².
- **Ignore restriction overlaps below** — Restriction overlaps below this share of the parcel are ignored, 0–50 %. Default: 0.5 %.
- **Notice shown on every report** — Notice text at the bottom of each report. Empty: the viewer's standard notice ("Information only, not an official certificate…") in the viewer's language.

**Pitfalls**

- The parcel layer must also be published on the Map tab. Its feature key is replaced with the parcel id field.
- Everything in the report becomes public for every parcel in the extent. This includes the ticked fields, the restriction titles, explanations, references, name fields, regulation fields and full texts. The Review tab lists them.
- Choosing another parcel, zone or regulations layer clears that layer's field ticks and titles.
- The field tables have no type column. A field's type (url, number …) comes only from saved or imported settings.
- Parcel layer and Zone layer have no empty choice. If saved settings name a layer that is not in this project, the log says "Parcel report: a layer of these settings is not in this project; check the Parcel report tab." Another layer may then be shown as selected. Check both combos.
- If the zone code field looks like a feature id (fid), another field is used instead and a warning is logged. Choose the real code field.
- Parcels with an empty id are skipped. If several parcels share an id, only the first is reported and a warning is logged. Use a unique id field.
- With a distance of 0, line and point restrictions only count when they touch the parcel exactly. Set a protection distance.
- A restriction or cut line layer missing from the project is skipped with a warning.
- Regulations and full texts are matched by zone code. Only the first row per code is used. Codes that do not match the zone layer's codes show nothing, with no error.
- Full texts are cleaned: HTML other than simple formatting is removed. A text that is empty after cleaning is dropped.
- When the report is off, these settings are kept but ignored, and they are not validated.
- The report adds an export stage. It is cached and is only recomputed when its inputs change.

**Errors**

- "parcelInfo.parcel_layer_id / key_field / zoning_layer_id / zoning_code_field: required when the parcel report is on" — The report is on but a layer or field is not chosen. Choose it, or turn the report off.
- "Parcel report: choose the parcel and zone layers." (Q2VT_PUB_PROFILE_INVALID) — A chosen layer is no longer in the project. Choose existing layers.
- "Parcel report: the parcel id or the zone code field does not exist." (Q2VT_PUB_PROFILE_INVALID) — The field was renamed or removed. Choose the field again.
- "Parcel report: publish the parcel layer (Map tab)." (Q2VT_PUB_PROFILE_INVALID) — The parcel layer is not ticked for publishing. Tick it on the Map tab.
- "Parcel report: the parcel layer must be a vector layer (Parcel report tab)." (Q2VT_PUB_PROFILE_INVALID) — Choose a vector polygon layer.
- "Parcel report → Zone regulations table: choose the table's zone code field …" — A table is chosen without its zone code field. Choose the field, or set Table to empty.
- "Parcel report → Regulation texts: choose the zone code field and the text field, or set Table to empty" — The full texts table lacks one of its fields. Choose both, or set the table to empty.
- "parcelInfo: minArea 0-1000 m², minShare 0-50 %", "parcelInfo.restrictions.bufferM: 0-1000 m", "parcelInfo.restrictions: a layer id once per layer" — Out-of-range or duplicate values, only possible from imported or hand-edited settings. Fix the values in the tab and save.

## Info tab

### About the map

- **Issued by** — Who issued the map (e.g. the municipality). It is shown under the title, in the panel and on prints.
- **Decree / plan number** — Decree or plan number (e.g. the local decree that adopted the plan).
- **In force from** — Date the map is in force from, as free text. It is shown under the title, separately from the export date.
- **Data as of** — Date of the data shown (survey, cadastre extract …), as free text.

### Documents published with the map

- **Title** — Column: the document's name in the viewer's panel. Editable. Default: the file name without its extension.
- **File** — Column: the local file path. Read-only. To change the file, remove the row and add the file again.
- **Add document…** — Picks one or more files (.pdf, .docx, .doc, .odt, .rtf, .txt, .png, .jpg, .jpeg, .webp) and adds a row for each.
- **Remove** — Removes the selected rows.

**Pitfalls**

- Documents are copied into the web map. Anyone can download them. The Review tab lists them as "Documents (downloadable by anyone)".
- A popup value equal to a document's file name or title becomes a link to the document.
- Files are copied under ASCII names in docs/. Two files with the same name get -2, -3 … suffixes.
- Paths are stored as local paths. On another computer, or after the file has moved, the export fails. Add the file again.
- Changing a document's content (same name) requires a new review before publishing.
- Dates are free text and are not checked. If all four fields are empty and there are no documents, the map shows no info block.
- An empty title falls back to the file name.

**Errors**

- "info.documents[n].title: '…' is used twice" — Two documents have the same title. Rename one.
- "info.documents[n].title: required" — Empty title in imported settings. Enter a title.
- "info.documents[n].path: one of .pdf, .docx, …" — Unsupported file type. Convert the file, e.g. to PDF.
- "Document '…': the file does not exist." (Q2VT_PUB_PROFILE_INVALID) — The file was moved or deleted. Remove the row and add the file again.
- "Document '…': not a .pdf, .docx, … file." (Q2VT_PUB_PROFILE_INVALID) — Unsupported extension at export. Use a supported type.

## Output tab

- **Archive** — Tile archive format. *PMTiles (vector tiles for static web hosting)* (default) is what the web map uses. *PMTiles + MBTiles copy* also writes `<slug>-<release>.mbtiles` next to the publication folder. *MBTiles only (desktop / preview; not for direct web hosting)* works for local export only.
- **Local output folder** — Folder for the exported map. It goes in `<folder>/<name>/`. Default: `web_maps` next to the project file, or in your home folder if the project is unsaved. Also used as the work and cache folder for uploads.
- **…** — Opens a folder picker for the local output folder.
- **Keep earlier versions in the local folder (releases, rollback)** — Off (default): each export replaces the map in `<folder>/<name>/`, a plain site you can copy to any web server. On: each export is kept as a version in `releases/`, and `index.html` opens the current one, with rollback. Applies to the *Local only* destination only.
- **Also write the legacy XYZ web package (web/)** — Also writes static XYZ tiles, a style and a viewer in a `web/` folder inside the export's work folder (`.q2vt-work`). Off by default.
- **Also write an offline ZIP of the release** — Writes `<slug>-<release>.zip` next to the publication folder. The ZIP holds the whole site. Off by default.
- **CPU limit (%)** — Share of CPU cores used for parallel export, tiling and raster drawing (1–100, default 100).
- **Fidelity** — *Vector-first: approximate where declared and report* (default) exports what it can and lists the approximations in the fidelity report. *Strict: fail if any component is unsupported or approximated* stops the export before anything is published.
- **Beyond the maximum zoom** — *Keep showing the last tiles beyond the maximum zoom* (default, overzoom) or *Hide layers beyond the maximum zoom*.
- **Polygon labels** — Where polygon labels go. *Whole polygon* uses the whole polygon. *Visible polygon* uses the part visible on screen. *As set in each layer's labels* (default) follows each layer's QGIS setting.
- **Publish ALL attribute fields in the tiles (not recommended)** — Off (default): tiles carry only the fields the map needs, plus the fields you approved. On: every attribute goes into the public tiles.
- **Fast marker lines: let the browser place screen-size line markers** — The browser places marker lines spaced in screen units, instead of the export computing them for every zoom. Much faster export, but positions are approximate: spacing is about 0.7–1.4× and markers can be missing at tile edges. Off by default.
- **Thin hairlines: draw zero-width lines thinner than QGIS** — Zero-width lines (hairlines) are drawn one device pixel wide, and a little wider when zoomed far in, so dense lines do not merge. Dashed hairlines keep their width. On by default.
- **Low memory web map: keep fewer tiles in the browser** — The browser keeps tiles for about one zoom level beyond the screen (instead of five). This uses much less memory, but tiles reload when you return to a place. Above 200 % screen scale, the map is drawn at 2 device pixels per CSS pixel. On by default.
- **Lighter tiles when zoomed out: leave out features under half a pixel** — Leaves out fills and thin lines smaller than 0.5 px at each zoom, and simplifies outlines a little more (¼ px) below each layer's last zoom. The last zoom of each layer keeps every feature with its exact shape. On by default.
- **Hide labels smaller than** — Hides labels sized in map units where their text is smaller on screen than the value (1–48 px, default 6 px). It also sets the smallest size for *Label every feature*. Labels sized in points, mm or pixels are not affected. On by default.
- **Reuse unchanged layers from earlier exports (faster)** — Skips layers whose data files, style and export settings are unchanged since an earlier export into this output folder, raster layers included. Database and web layers are always exported again. On by default.
- **Clear cache…** — Shows the size of this output folder's export cache (`.q2vt-cache`) and deletes it after you confirm. The next export processes every layer again.

**Pitfalls**
- *MBTiles only* cannot be used with Cloudflare R2, S3 or SSH destinations. Choose *PMTiles* or *PMTiles + MBTiles copy*.
- *Keep earlier versions…* does nothing for R2, S3 or SSH destinations (R2/S3 are always versioned; SSH never is).
- If versions are off, each export overwrites the previous map in `<folder>/<name>/`. Only files written by an earlier export are deleted. Your other files there stay.
- The XYZ package lands in the hidden work folder, not in the published site, and it is never uploaded.
- *CPU limit* is capped internally: at most 90 %, and at most 6 parallel workers. Values above that do not speed up the export.
- *Strict* fails on any warning about an unsupported or approximated component (code `Q2VT_STRICT_FAILED`). Read `fidelity_report.html` first.
- Turning on *Publish ALL attribute fields* makes every attribute public. It also makes tiles larger. Check the field list in the Review tab.
- Turning off *Lighter tiles*, *Low memory* or *Reuse unchanged layers* can make detailed maps (such as parcels) heavy in the browser or slow to export.
- The cache is shared by every publication in the same output folder. It is pruned automatically: entries unused for 30 days, then the oldest beyond 4 GB. A plugin update invalidates it.
- For a network output folder (Windows share, NFS, SMB, sshfs), the work files and the cache stay in the system temp folder on this computer. Only the finished map and logs go to the network folder.
- Changing the output folder starts with an empty cache, and with a new site if versions are on.

**Errors**
- `Q2VT_PUB_PROFILE_INVALID` "output.archive: web hosting needs PMTiles (choose PMTiles or Both)" — *MBTiles only* is set with an R2, S3 or SSH destination. Fix: pick a PMTiles option.
- `Q2VT_PUB_PROFILE_INVALID` "Choose a local output folder." — The *Local output folder* field is empty, on export or on *Clear cache…*. Fix: choose a folder.
- "The cache of this output folder is empty." (Cache message) — There is nothing to delete. This is information only.
- `Q2VT_STRICT_FAILED` "N component(s) cannot be reproduced exactly." — *Strict* fidelity found unsupported or approximated styling. Fix: change those styles (see the fidelity report), or switch to *Vector-first*.
- `Q2VT_PUB_DISK` (OS error text) — Writing the PMTiles archive failed. Causes: the disk is full, or the folder is not writable. Fix: free space or choose another folder.

## Destination tab

- **Destination** — Where Publish sends the map: "Local only (no upload)" (default), "Cloudflare R2", "Other S3-compatible storage", or "SSH / SFTP server (one folder, not versioned)". The fields below change with the choice.
- **Step-by-step: set up Cloudflare R2…** — Opens the "Cloudflare R2: step by step" guide (see below). Hidden for SSH.
- **Map address** — Read-only. The final address: `<public base URL>/<prefix>/` (R2/S3) or `<public URL>/` (SSH). Shows "— (enter the public base URL)", "— (check the prefix)" or "— (local only)" when it cannot be built.

### Cloudflare R2 and S3-compatible storage

- **Cloudflare account id** — R2 only. The 32-character Account ID. You can paste the S3 API URL or a dashboard address instead; the id (and the bucket, and a jurisdiction endpoint) is taken from it.
- **S3 API endpoint (optional)** — R2: leave empty; it is derived from the account id. Fill only for EU/FedRAMP jurisdiction buckets.
- **S3 API endpoint** — Other S3 storage: required. The API address, not the public address. Must be `https://`.
- **Bucket** — The bucket name exactly as in the provider's console. Required. Pasting a bucket's S3 API URL fills the account id too.
- **Prefix in the bucket** — Folder for this map inside the bucket, e.g. `maps/arlo`. Empty: `maps/<slug>`. The plugin writes only inside it; several maps can share one bucket.
- **Public base URL (custom domain)** — The address people open (the custom domain connected to the bucket), e.g. `https://maps.example.com`. Required. Not the S3 API URL.
- **Saved credentials (QGIS authentication: user = access key id, password = secret)** — A QGIS authentication configuration holding the keys, encrypted and protected by the QGIS master password. Only its id is saved with the settings.
- **Or keys for this session only** — Access Key ID and Secret Access Key used while the window is open; not saved. They take precedence over the saved credentials.
- **Save keys in QGIS…** — Stores the session keys as an encrypted "Basic" configuration named "R2/S3 <bucket> (QWebMap)", selects it and clears the fields.
- **Releases to keep** — 1–100 (default 3). How many releases "Delete old releases…" leaves in the bucket. Not applied automatically.
- **Storage supports conditional writes (R2, AWS S3)** — Default on. Activation uses If-Match/If-None-Match so two publishers cannot overwrite each other. Turn off only for storage without it.
- **Test connection** — Checks that the bucket is reachable and the prefix can be listed. Shows ✔/✖ per check.
- **Show CORS policy** — Shows a CORS rule for your public origin (GET/HEAD, Range headers). Needed only when the map data is read from another site (e.g. embedded). The plugin never changes the bucket's CORS.
- **Releases and rollback…** — Opens the release list of this publication (see below).

### SSH / SFTP server

- **SSH server** — Host name or IP address. Pasting `user@server:/folder` or `sftp://user@server:port/folder` fills User, Port and Folder too.
- **Port** — 1–65535, default 22.
- **User** — The SSH login. Empty: the user of the saved password, else your ssh default.
- **Folder on the server** — Where the map's files go (created if missing). Absolute, or relative to the login's home (`~/` allowed). Each publish replaces the previous map there; no versions.
- **Private key file** — Optional OpenSSH private key. Empty: ssh-agent or your default keys in `~/.ssh`. **Browse…** picks the file.
- **Public URL of the folder (optional)** — The folder's web address, e.g. `https://www.example.com/map`. Used for Open map / Copy link / embed code and to check that the new map is served. Empty: nothing is checked.
- **Saved password (QGIS authentication: user = SSH user, password = password or passphrase)** — A saved, encrypted Basic configuration with the SSH password or key passphrase.
- **Or a password for this session only** — Password or key passphrase used while the window is open; not saved. Leave empty for a key without passphrase or ssh-agent.
- **Save in QGIS…** — Stores User + password as "SSH <user>@<server> (QWebMap)", selects it and clears the field.
- **Test connection** — Logs in, creates the folder if needed, writes and deletes a test file, and reports whether files are replaced atomically.

### Cloudflare R2: step by step (guide window)

- **Open the Cloudflare dashboard** — Opens the R2 overview in your browser. The guide lists the one-time steps: activate R2, copy the Account ID, create a bucket, choose a prefix, connect a custom domain, create a bucket-scoped "Object Read & Write" API token, save the keys in QGIS, test, then publish.
- **Close** — Closes the guide.

### Releases of <map> (Releases and rollback… window)

- **Make current (rollback)** — Points the stable address at the selected older release (asks first; nothing is uploaded). The current one is marked "← current".
- **Delete old releases…** — Deletes the oldest releases beyond **Releases to keep**; never the current one. Lists them and asks first.
- **Abort interrupted uploads…** — Lists and aborts unfinished multipart uploads under this prefix. A later publish starts them again.
- **Close** — Closes the window.

**Pitfalls**

- R2/S3 and SSH need the PMTiles archive: choose PMTiles or Both on the Output tab, not MBTiles only.
- R2/S3: `r2.dev` works for tests but is rate-limited; use a custom domain. The public URL and endpoint must be `https://` (plain `http` only for `localhost`).
- Settings imported from another computer keep a credentials id that does not exist here: select or save the keys again.
- Switching between SSH and R2/S3 puts the other family's public URL and saved credentials aside; switching back restores them (within the open window).
- Releases are never deleted automatically: use **Delete old releases…** to apply **Releases to keep**. Storage of retained releases is billed.
- Deleting releases or rollback cannot recall copies already downloaded or cached.
- A prefix already used by another publication is refused; give the new map another prefix or slug.
- SSH: no versions and no rollback. Files with the same name in the folder (e.g. `index.html`) are replaced; only files QWebMap uploaded before (listed in `.q2vt-files.json`) are deleted.
- SSH: a new server's host key is accepted on first use; a changed key stops the upload.
- SSH on Windows: a password or passphrase needs OpenSSH 8.4+; the built-in Windows 10 client is older, so use a key or ssh-agent.
- SSH without "posix-rename" support: each changed file is briefly missing during the upload.
- Session keys and passwords are lost when the window closes; settings export never includes an SSH password.

**Errors**

- "destination.bucket: required" / "destination.publicBaseUrl: required (the public custom domain)" / "destination.endpoint: required" / "destination.accountId: required for R2 (or an explicit endpoint)" — Shown on Save/Export. Fill the field.
- "destination.endpoint / publicBaseUrl: must be an https:// URL" — Use `https://`.
- "output.archive: web hosting needs PMTiles (choose PMTiles or Both)" — Change the archive on the Output tab.
- "destination.prefix: Prefix segment '…' must be ASCII letters, digits, '.', '_' or '-'." (Q2VT_PUB_PATH_UNSAFE) — Remove spaces, accents and `..` from the prefix.
- "destination.retention: 1-100" — Use a value in range.
- "destination.host: required" / "a host name or IP address (no spaces, user@ or path)" / "(the port goes into the Port field)" — Enter only the host; put user, port and folder in their fields.
- "destination.remoteDir: required" / "a folder, not the server's root" — Give a real folder, not `/`.
- "destination.identityFile: this is the public key (.pub)…" — Choose the private key file (same name without `.pub`).
- "destination.publicBaseUrl: the folder's address, without index.html at the end" — Remove `index.html`.
- "The private key file … does not exist." (Q2VT_PUB_DESTINATION) — Fix the path.
- "Enter the Cloudflare account id." (Q2VT_PUB_DESTINATION) — Fill the account id (letters/digits only).
- "No saved credentials are selected." / "…do not exist in this QGIS…" / "could not be unlocked (master password?)" / "need an access key id (user name) and a secret access key (password)" (Q2VT_PUB_CREDENTIALS) — Select or save keys, enter session keys, or unlock the master password.
- "Set the QGIS master password to save credentials, or use them for this session only." (Q2VT_PUB_CREDENTIALS) — Set a master password, or use session keys.
- "The storage refused the credentials or the key has no permission for this bucket/prefix." (Q2VT_PUB_CREDENTIALS) — Wrong keys, or the token is not scoped to this bucket.
- "Bucket '…' does not exist." (Q2VT_PUB_DESTINATION) — Check the bucket name and the endpoint/jurisdiction.
- "Object storage request failed." (Q2VT_PUB_UPLOAD) — Network or server error after retries; try again.
- "The S3 library could not be loaded" (Q2VT_PUB_DEPENDENCY) — The bundled boto3 is broken; reinstall the plugin.
- "The prefix '…' holds another publication (…)" (Q2VT_PUB_DESTINATION) — Choose another slug/prefix.
- "This destination cannot do conditional writes; activation would not be conflict-safe." (Q2VT_PUB_ACTIVATION) — The conditional-writes box is off; turn it on if the storage supports it.
- "Another publisher activated a release first." (Q2VT_PUB_ACTIVATION_CONFLICT) — Your release stays uploaded; make it current from **Releases and rollback…** if wanted.
- "The current release cannot be deleted." (Q2VT_PUB_ACTIVATION) / "Release … is not complete remotely." — Pick another release.
- "The OpenSSH client (sftp, ssh) was not found on this computer." (Q2VT_PUB_DEPENDENCY) — Install OpenSSH Client, restart QGIS.
- "The OpenSSH client of this computer (version …) cannot take a password…" (Q2VT_PUB_DEPENDENCY) — Use a key/ssh-agent or install OpenSSH 8.4+.
- "The server … refused the login (…)" (Q2VT_PUB_CREDENTIALS) — Check user, password/passphrase or key.
- "ssh ignored the private key file … because other users can read it." — `chmod 600` the key (Windows: restrict file permissions).
- "The private key file … is not an OpenSSH key (a PuTTY .ppk key?)." — Export it as OpenSSH from PuTTYgen.
- "The host key of … has changed since the last connection" (Q2VT_PUB_DESTINATION) — If expected, run `ssh-keygen -R <host>` and retry.
- "The server name … is not known" / "cannot be reached on port …" (Q2VT_PUB_DESTINATION) — Check host, port, network, firewall.
- "…accepted the login but offers no SFTP" (Q2VT_PUB_DESTINATION) — Ask the admin to enable the SFTP subsystem.
- "The folder … does not exist on the server and could not be created" / "Permission denied: … cannot write into …" (Q2VT_PUB_DESTINATION) — Fix the folder or the user's permissions.
- "The map needs a folder where the server's folder has a file: …" (Q2VT_PUB_DESTINATION) — Rename or remove that file on the server.
- "The SSH password (or the key's passphrase) appears in the map's files" (Q2VT_PUB_SECRET_LEAK) — Use another password or a key.
- "The SSH connection to … failed or was lost" / "The SFTP transfer stopped" (Q2VT_PUB_UPLOAD) — Publish again to complete the folder.

## Review tab

- **Review text** — Read-only summary of what becomes public: target address, each published layer (feature count, popup, search, filter and key fields, always-shown/hidden at start), raster layers, "all fields" warning, basemap source, views, terrain, 3D height fields, viewer extras, house-number search, documents, parcel report fields, external resources (web basemaps, Street View, live layers), cost note, last local export size, and whether approval is needed. Refreshed when the tab opens.
- **Refresh review** — Rebuilds the summary from the current settings.
- **I understand that the geometry of the selected layers and the fields listed above become public at the target address.** — The approval. Ticked automatically when the same data scope was approved before; untick and re-tick after reviewing a changed scope.

**Pitfalls**

- Approval is needed for the first publication and whenever what becomes public changes: included layers, popup/search/filter/key fields, "all fields", documents (also their file content), terrain, web basemaps, Street View, address search, parcel report, live layers, or the destination (kind, public URL, bucket+prefix or SSH host/port/user/folder).
- The approval covers only what the Review tab last showed: a change after ticking it sends you back to this tab on Publish.
- Approval is not needed for "Local only"; Publish then just exports.
- "Filter fields (also in the tiles)" and "all attribute fields" are downloadable by anyone, not only shown in popups.
- Online map services (WMS/XYZ rasters) are flagged: check their licence allows republishing.
- "3D height fields are set but "3D view" is off" — the height data is published but the map shows no 3D button.

**Errors**

- "Review what becomes public and tick the approval before publishing." — Publish was pressed without a current approval. Read the summary, tick the box, press Publish again.

## Window buttons

- **Save settings** — Validates and saves the settings into the project. Save the project file to keep them. Shows up to 12 problems instead of saving.
- **Settings file…** — Menu with **Export settings to a file…** (writes a `.q2vt.json`; includes the R2/S3 keys if session keys are entered or saved credentials are selected, never an SSH password — keep the file private) and **Import settings from a file…** (asks Yes = same web map/address, No = a new separate map; layers are matched by name; imported keys are saved encrypted in QGIS if possible; web basemaps also become QGIS XYZ connections).
- **Export locally** — Builds the web map into the local folder. Asks first if the extent is the current map view, and may offer to speed up a slow zoomed-out map. Saves the settings first. Blocks the rest of QGIS while it runs.
- **Preview** — Enabled after an export. Serves the exported folder on a local web server and opens it in the browser.
- **Publish** — Local only: exports, then enables Open map (file address). R2/S3/SSH: checks the approval, reuses the last export if the settings are identical (else exports), then uploads in the background, verifies the public URL and activates the release. The status shows the stable address and, for R2/S3, "This version" (versioned link).
- **Open map** — Opens the published map (or the local `index.html` after a local Publish).
- **Copy link** — Copies the public address. Enabled after a successful online publish.
- **Copy embed code** — Copies an `<iframe>` of the online map in embed mode (`?embed`). Works once a public URL is set, even before publishing.
- **Open local package** — Opens the exported publication folder.
- **Cancel** — Enabled while exporting or uploading. Stops the job; the previous online release stays current (SSH: already replaced files stay; publish again).
- **Close** — Closes the window and saves changed, valid settings silently. An upload keeps running in the QGIS task bar.

**Pitfalls**

- Settings live in the project: after Save settings, also save the project file.
- If the project was saved elsewhere, the window asks: Yes = keep updating the same web map (same address), No = new separate map. Choose No for a copy, or both projects will overwrite one map.
- Invalid settings are not saved on Close; the last valid ones stay.
- Opening another project closes the window; its settings are not saved into the new project.
- During an export the tabs are locked and QGIS takes no input until it ends or you press Cancel.
- Copy link stays disabled for a local-only Publish; use Open map / Open local package.
- If a CDN still serves the old `current.json`, a warning says so; the versioned link works at once.

**Errors**

- "Choose an extent." (Q2VT_PUB_PROFILE_INVALID) — Set an extent on the Map tab.
- "Export failed." (ERROR) — Unexpected error; the log under the progress bar has the details.
- "Publishing failed." (ERROR) — Unexpected error in the upload task; see the log.
- "Publishing cancelled." — Cancel was pressed before the upload started.
- "The project these settings belong to was closed; they are not saved." — Reopen the project and the window.
- "Not a publication settings file: …" — The import file is not valid settings JSON.
- "This profile was saved by a newer plugin (schema …)" (Q2VT_PUB_SCHEMA_UNSUPPORTED) — Update the plugin.
- "Profiles never store secrets; remove: …" (Q2VT_PUB_PROFILE_INVALID) — A hand-edited file contains secret-looking keys; remove them.
- "Q2VT_PUB_RANGE_UNSUPPORTED" / "Q2VT_PUB_CORS" / "Q2VT_PUB_MIME" / "Q2VT_PUB_PUBLIC_VERIFY" — The public URL does not serve the release correctly (byte ranges, CORS, content type, or wrong URL/cache). R2/S3: the release is uploaded but not activated. SSH: the files are on the server; a warning explains. Check the public URL and the host settings (HOSTING.md).
- "Q2VT_PUB_SECRET_LEAK" — A credential was found in the output; nothing is uploaded. Remove it from the data.
- "Enter the public URL of the server folder (Destination tab)…" / "Publish the map online first (Destination tab)…" — Copy embed code needs a public address.

## Command line (Processing)

Algorithm **Publish web map (saved settings)** (`QGIS2VectorTilesFork:publish_web_map`, QWebMap provider). Runs the saved settings without the window, as Publish / Export locally do; nothing is asked.

- **Publication settings (title or web address; empty = the active ones)** — `SETTINGS`. Title, slug or id (any case) of saved settings. Empty: the ones the window opens with.
- **Action** — `ACTION`. 0 = "Publish to the settings' destination" (default), 1 = "Export locally only".
- **Extent (empty = the settings' extent)** — `EXTENT`. Empty: the extent layer's current extent, else the saved fixed/last-exported extent.
- **Local folder (empty = the settings' folder)** — `OUTPUT_DIR`. Overrides the export folder.
- **Approve what becomes public (when the review is due)** — `APPROVE`, default false. Required when the review is due.
- **Save the approval and settings into the project file** — `SAVE_PROJECT`, default false. Writes the approval into the project so later runs need no APPROVE.
- **Outputs** — `OUTPUT_FOLDER` (local web map folder), `ENTRY` (local index.html), `URL` (public address), `PUBLISHED` (true/false).
- **Credentials** — Environment variables `QWEBMAP_ACCESS_KEY_ID`, `QWEBMAP_SECRET_ACCESS_KEY` (optional `QWEBMAP_SESSION_TOKEN`); SSH: `QWEBMAP_SSH_PASSWORD` (optional `QWEBMAP_SSH_USER`), or a key/ssh-agent. Else the saved QGIS authentication configuration.

```
qgis_process plugins enable QWebMap
qgis_process run QGIS2VectorTilesFork:publish_web_map --PROJECT_PATH=city.qgz --ACTION=1 --OUTPUT_DIR=/srv/web/city
qgis_process run QGIS2VectorTilesFork:publish_web_map --PROJECT_PATH=city.qgz --SETTINGS="City map" --APPROVE=true --SAVE_PROJECT=true
```

On Windows use `qgis_process-qgis.bat` (QGIS `bin` folder or OSGeo4W Shell). `--json` prints the outputs as JSON; `qgis_process help QGIS2VectorTilesFork:publish_web_map` lists the parameters. `--EXTENT="xmin,xmax,ymin,ymax [EPSG:xxxx]"`.

**Pitfalls**

- The settings must be saved in the project first (Save settings, then save the project file).
- Settings that follow the map view have no extent until exported once from the window; pass EXTENT.
- A saved credentials configuration needs the master password without a prompt: integrate it with the system password manager (Settings → Options → Authentication), or use the environment variables.
- Without SAVE_PROJECT the approval is not stored, so every run needs APPROVE.
- APPROVE approves without showing the review; check the Review tab first.

**Errors**

- "No project is open: give the project file (qgis_process: --PROJECT_PATH=map.qgz)." — Add `--PROJECT_PATH`.
- "The project has no saved publication settings…" (Q2VT_PUB_PROFILE_INVALID) — Set up and save settings in the window.
- "No saved publication settings are called '…'. Saved: …" (Q2VT_PUB_PROFILE_INVALID) — Use one of the listed names.
- "The settings have no extent (they follow the map view, never used yet)…" (Q2VT_PUB_PROFILE_INVALID) — Pass EXTENT or export once from the window.
- "The saved settings have problems: …" (Q2VT_PUB_PROFILE_INVALID) — Fix them in the window.
- "This publication needs the review…" (Q2VT_PUB_REVIEW_NEEDED) — Approve on the Review tab, or run with `--APPROVE=true`.
- "The project file could not be saved: …" — SAVE_PROJECT failed (read-only file?); the publish itself succeeded.
- Credential and destination errors are the same as on the Destination tab (Q2VT_PUB_CREDENTIALS, Q2VT_PUB_DESTINATION, …), printed as `CODE: message`.

## Keeping this guide up to date

This page is built from `docs/USAGE.md` in the repository (`python3 tools/build_usage.py` writes `docs/usage.html`); a push to `main` publishes it on GitHub Pages. The test `tests/unit/test_usage_docs.py` fails when an option of the Publish window has no entry here, or when the HTML is older than the Markdown. So a new option is documented together with the change that adds it.

