# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.58.6)](https://github.com/danzig666/QWebMap/releases/tag/v4.58.6)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.58.6**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.58.6 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Javítva
- **A segédfolyamatok elindulnak a QGIS 4 Windows-os változatán.** A nagy exportok az adatkészleteket segéd-QGIS-folyamatokra bízzák. A QGIS 4 Windows-os változatán ezek sosem indultak el (az export naplója: *worker message: PyQt6.QtCore.QDateTime not allowed*): a PyQt6 a projekt egy dátum-változóját (pl. `@project_creation_date`) olyan formában küldi, amelyet a segédfolyamatok elutasítottak, így minden export magában a QGIS-ben futott, lassabban. A Qt dátumokat, időpontokat, színeket és hasonló értékeket mostantól elfogadják (minden mást továbbra is elutasítanak).
