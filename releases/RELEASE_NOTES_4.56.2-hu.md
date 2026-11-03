# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.56.2)](https://github.com/danzig666/QWebMap/releases/tag/v4.56.2)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.56.2**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.56.2 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Javítva
- **A domborzat (terrain) exportja kb. tízszer gyorsabb.** Részletes DEM-mel az *Elevation layer (DEM)* (Basemap fül, Terrain) exportja nagyon lassú volt: a DEM körüli területet minden zoomszinten újra kitöltötte, ami a legnagyobbon perceket vett igénybe, és minden kicsinyített szint a teljes DEM-et olvasta. A környezet most egyszer, a legkisebb zoomon töltődik ki, a nagyobb zoomok az eggyel kisebbtől veszik át; a kicsinyített szintek a DEM egyszer felépített piramisából olvasnak. Egy település 1 m-es DEM-je: 185 s → 16 s. A DEM-en belüli magasságok nem változnak, és a kitöltés simábban csatlakozik a DEM széléhez, mint korábban.
- **A domborzati réteg eltávolítható.** Az *Elevation layer (DEM)* mező szövegét törölve a réteg visszakerült; a kiürített mező mostantól *(no terrain)*, és a mezőben törlőgomb (✕) van. Ugyanígy a többi rétegmező, amely „nincs réteg” lehetőséget kínál.
- **Raszteres másolat csak ott, ahol gyorsít.** A 4.56.1 minden más vetületű rasztert egyszer Web Mercatorba vetített; egy részletes, országos vetületű raszternél (EOV-s DEM) ez tovább tartott, mint amennyit megtakarított. Másolat már csak erősen görbülő átvetítésnél készül (sarkvidéki kép), és soha nem domborzatárnyékolásnál (hillshade), amelyet a QGIS a pixelek saját vetületbeli mérete szerint árnyékol.
