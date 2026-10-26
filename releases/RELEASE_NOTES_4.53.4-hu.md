# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.53.4)](https://github.com/danzig666/QWebMap/releases/tag/v4.53.4)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.53.4**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.53.4 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.


### Javítva (a generikus 4.53.4-ből)
- **Vízszintes (Horizontal) poligonfeliratok ott, ahol a QGIS-ben.** A *Horizontal* elhelyezésű poligonfeliratok eddig a poligon legtágasabb pontjára kerültek. A QGIS viszont a jelölt helyek közül a poligon és a térkép szélétől mért távolság, *és* a poligon súlypontjához való közelség alapján választ. Egy hosszú sávnál a felirat a középe helyett a szélesebb végére került, és zoomolásnál vándorolt. A webtérkép most a QGIS jelölt helyeit és pontozását használja: a QGIS-hez mérve minden vizsgált zoomon néhány képponton belül egyezik. Erősen homorú (L vagy U alakú) poligonnál még lehet eltérés, mert a QGIS az ilyet előbb darabokra vágja, amire a webtérkép nem képes.

A javításhoz a térképet újra kell exportálni (a webtérkép kódja minden kiadás része).
