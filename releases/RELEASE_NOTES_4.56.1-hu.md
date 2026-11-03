# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.56.1)](https://github.com/danzig666/QWebMap/releases/tag/v4.56.1)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.56.1**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.56.1 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Javítva
- **Nincs többé összeomlás domborzatárnyékolásos (hillshade) raszterrétegnél.** Bekapcsolt OpenCL mellett (*Settings › Options › Acceleration*) a QGIS saját hillshade-megjelenítője összeomolhatott, miközben az export a réteg csempéit rajzolta: egy pixel magas blokknál egy nem létező második sort másol. Az export mostantól kikapcsolt OpenCL-lel rajzolja a raszteres csempéket, és utána visszakapcsolja. (Ugyanez a QGIS-hiba ritkán a térképvásznon is előjöhet; az OpenCL kikapcsolása ott is segít.)

### Változott
- **A projekt más néven mentve megtartja a közzétételi beállításokat.** Új néven vagy más mappába mentett projektnél a bővítmény már nem kérdezi, hogy új webtérképet kezdjen-e. Minden beállítás és ugyanaz a webtérkép megmarad; az ablak csak azt kérdezi, hova exportáljon: *Keep the folder* (a régi mappa), *Next to this project* (az új fájl melletti `web_maps` mappa) vagy *Choose a folder…* (saját választás). Ha az új fájl ugyanabban a mappában van, nem kérdez. Külön webtérképhez a beállításokat fájlba kell exportálni, majd új webtérképként importálni.
- **A *Zoomed-out load* ellenőrzés csak egyszer fut.** Export előtt a becslés nem fut újra, amíg semmi nem változott abból, amit olvas (kiterjedés, zoomszintek, a közzétett vektorrétegek adata, stílusa vagy méretarány-tartománya, a webes rétegbeállítások). Ha már válaszoltál rá, vagy megnézted a *Zoomed-out load…* gombbal, a következő export nem kérdezi újra.
