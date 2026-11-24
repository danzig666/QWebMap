# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.61.2)](https://github.com/danzig666/QWebMap/releases/tag/v4.61.2)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.61.2**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.61.2 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Javítva
- **A QGIS összeomolhatott térkép készítésekor** (QGIS 3.44, Windows). Az export előtti kicsinyítési terhelés-ellenőrzés a rétegek elemeinek mintáját elemazonosító szerint olvasta be, és a GDAL egyes adatoknál ebben összeomlott. Most minden réteget egyszer olvas végig a területen, és közben véletlen mintát tart meg. Ez gyorsabb is az olyan formátumoknál, ahol az azonosító szerinti olvasás lassú (GeoJSON, CSV …).
- **Az egyszerű nézet nem fagy le nagy projekteknél.** A rétegek felmérése (a *Choose automatically* és az előnézet helye számára) a háttérben fut, közben egy folyamatjelző látszik az előnézet alatt; az ablak végig reagál. A felmérés és a rajzolás leáll, ha térkép készül, ha az Advanced nézetre vált, vagy ha az ablak bezárul.
