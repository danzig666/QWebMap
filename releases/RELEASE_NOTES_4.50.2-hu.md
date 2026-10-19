# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.50.2)](https://github.com/danzig666/QWebMap/releases/tag/v4.50.2)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.50.2**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.50.2 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.


### Javítva (a generikus 4.50.2-ből)
- **A ferde feliratok egy pillanatra vízszintesen jelentek meg mozgatás után.** Nagy térképen a *Free* (szabad szögű) elhelyezésű feliratok — például a keskeny telkek mentén elforgatott helyrajzi számok — vízszintesen tűntek fel, amikor a képernyőre értek, és csak a csempék betöltése után (akár néhány másodperc múlva) fordultak el. A képernyőn kívül előre elhelyezett feliratok már a szögükkel készülnek, így azonnal elforgatva jelennek meg. Egy városi térképen mérve: mozgatásonként kb. 5 ilyen feliratról kb. ötmozgatásonként egyre csökkent.

A javításhoz a térképet újra kell exportálni (a webtérkép kódja minden kiadás része).
