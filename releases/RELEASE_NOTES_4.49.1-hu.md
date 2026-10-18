# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.49.1)](https://github.com/danzig666/QWebMap/releases/tag/v4.49.1)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.49.1**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.49.1 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Javítva (a generikus 4.49.1-ből)
- **Újra éles vonalak nagyított képernyőn.** A 4.49.0 a *Low memory web map* módban CSS-pixelenként egy eszközpixellel rajzolta a webtérképet; egy 125 %-ra nagyított (Windows) képernyőn a böngésző ezt felnagyította, és minden vonal elmosódott. A térkép ismét a képernyő saját pixelarányával készül, legfeljebb 2-vel (telefonok). A 4.49.0 többi memóriamegtakarítása megmarad: a közös feliratforrás és a feliratok memóriaszivárgásának javítása.
