# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.50.3)](https://github.com/danzig666/QWebMap/releases/tag/v4.50.3)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.50.3**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.50.3 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.


### Új (a generikus 4.50.3-ból)
- **QGIS 4 (Qt6) támogatás.** A plugin Qt6-kompatibilisnek van jelölve, így a QGIS 4 is telepíti. A teljes tesztcsomag (unit, QGIS integrációs és böngészős tesztek) átmegy a QGIS 4.2-n. A QGIS 3.44 és újabb változatán minden a régiben működik.

### Javítva
- **Jelölővonalas sraffozás QGIS 4-en.** A jelölővonallal (*Marker line*: nyílhegyek, pontok a sraffozás vonalain) rajzolt *Line pattern fill* QGIS 4-en közelítő képre esett vissza; most ugyanaz a pontos QGIS-minta, mint QGIS 3-on.
