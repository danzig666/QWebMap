# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.58.11)](https://github.com/danzig666/QWebMap/releases/tag/v4.58.11)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.58.11**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.58.11 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Javítva
- **Kifejezések EPSG-kód nélküli vetületben.** Ha egy réteg vagy a projekt vetületének nincs hatósági kódja – például a QGIS nem tudja azonosítani a `.prj` fájlt („Unknown CRS”), vagy a projektben készült egyéni vetületet nem mentették felhasználói vetületként –, az export a kifejezéseket Web Mercatorban értékelte ki, nem abban a vetületben. Ez elrontotta a feliratokban, szűrőkben és adatvezérelt tulajdonságokban szereplő `$area`, `$length`, `$x`/`$y` értékét, a geometriagenerátorok távolságait (`buffer(@geometry, 10)`), a térképegységben megadott kitöltés-eltolásokat és a minták helyzetét: Magyarországon például a terület nagyjából 2,2-szer nagyobbra jött ki. Mostantól a réteg vagy a projekt saját vetületében értékeli ki őket, ahogy a QGIS is.
