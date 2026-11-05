# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.58.7)](https://github.com/danzig666/QWebMap/releases/tag/v4.58.7)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.58.7**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.58.7 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Változott
- **Az export naplója megnevezi a rajzolás alatt álló raszterréteget.** A QGIS saját raszterrajzolásában bekövetkező összeomlás a QGIS 4 Windows-os változatát üzenet, hibajelentő ablak és Eseménynapló-bejegyzés nélkül zárja be, és az export raszteres része eddig semmit sem írt az `export_log.txt`-be. Mostantól minden raszterréteg (adatforrása, megjelenítője, vetülete, zoomszintjei, egyszerre rajzolt csempéinek száma), minden zoomszintje és a domborzat is bekerül a naplóba, amikor elkezdődik, így az utolsó sorok megmutatják, mit rajzolt éppen a QGIS.
