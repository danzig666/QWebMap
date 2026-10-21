# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.52.1)](https://github.com/danzig666/QWebMap/releases/tag/v4.52.1)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.52.1**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.52.1 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.


### Javítva (a generikus 4.52.1-ből)
- **Rétegre nagyítás Layers fül nélkül.** Ha a webtérképen nincs Layers fül (*Layers tab* kikapcsolva: csak jelmagyarázat), a jelmagyarázat eddig is mutatta a rétegek be/ki kapcsolóit; most a *Zoom to layer* gombok is ott vannak a kapcsolók mellett — kikapcsolt rétegnél is. Eddig ebben a módban nem lehetett rétegre nagyítani. A nyomtatott jelmagyarázatban a gombok nem jelennek meg.

A javításhoz a térképet újra kell exportálni (a webtérkép kódja minden kiadás része).
