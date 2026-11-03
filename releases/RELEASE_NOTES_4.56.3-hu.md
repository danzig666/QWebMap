# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.56.3)](https://github.com/danzig666/QWebMap/releases/tag/v4.56.3)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.56.3**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.56.3 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Új
- **Csak a térkép.** A *Map only: nothing on screen but the map* (Interaction fül) olyan oldalt tesz közzé, amelyen csak a térkép látszik: nincs cím, panel, jelmagyarázat, gombok, aránymérték, felugró ablak vagy keresés; a látogató továbbra is mozgathatja és nagyíthatja. A térkép és az alaptérkép forrásmegjelölése (attribution) egy sarokban megmarad, ha van (a licencük előírja). Bekapcsolt állapotban a többi nézőbeállítás szürke.
- **Zoomszint-kijelzés ellenőrzéshez (`?debug`).** A térkép címéhez `?debug`-ot írva (bármely `#` elé) az aránymérték fölött egy doboz mutatja a térkép zoomszintjét és az ott rajzolt vektoros csempék zoomszintjét („overzoomed”, ha túl van az utolsó csempezoomon). A `?debug=tiles` a csempehatárokat is megrajzolja. A látogatók nem látják, hacsak maguk be nem írják.
