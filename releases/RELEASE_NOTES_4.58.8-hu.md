# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.58.8)](https://github.com/danzig666/QWebMap/releases/tag/v4.58.8)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.58.8**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.58.8 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Változott
- **A raszteres csempék attól a zoomtól készülnek, ahol a réteg látható.** A raszterréteg (és a kizoomolva képként rajzolt vektorréteg) attól az első zoomtól rajzolódik, ahol legalább 8 pixel széles, nem a webtérkép első zoomjától: egy 16 km-es domborzatmodell a 0. zoomon egy pixelnél is kisebb, és a legalacsonyabb zoomok csempéin semmi sem látszott. A QGIS 4 Windows-os változatán ezek az egyszerre, minden zoomon elindított rajzolások domborzatárnyékolás exportjakor azonnal bezárták a QGIS-t. Kevesebb csempe, és az export már nem is rajzolja meg őket.
