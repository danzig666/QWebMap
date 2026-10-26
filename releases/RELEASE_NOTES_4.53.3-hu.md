# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.53.3)](https://github.com/danzig666/QWebMap/releases/tag/v4.53.3)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.53.3**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.53.3 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.


### Javítva (a generikus 4.53.3-ból)
- **Aktív nézet csoport kikapcsolása után.** A nézetsáv aktívként jelöli a kiválasztott nézetet, amíg a megjelenített rétegek nem változnak. Egy réteg kikapcsolása eddig is levette a jelölést, egy egész csoport kikapcsolása viszont nem — a nézet jelölve maradt, pedig a térkép már nem azt mutatta. Most leveszi, a csoport visszakapcsolásakor pedig újra jelöli.

A javításhoz a térképet újra kell exportálni (a webtérkép kódja minden kiadás része).
