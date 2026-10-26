# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.53.1)](https://github.com/danzig666/QWebMap/releases/tag/v4.53.1)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.53.1**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.53.1 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.


### Javítva (a generikus 4.53.1-ből)
- **Hiányzó csempék az előnézetben új export után.** Ha a térképet újra exportáltad, miközben egy előnézeti oldal (*Preview* a Publish ablakban) még nyitva volt, az oldal az új csempefájlt a régi fájl szerinti helyeken olvasta: egy zoomszinten vagy egy területen eltűntek a vonalak és kitöltések, beljebb nagyítva visszajöttek. Az előnézet most jelzi a böngészőnek, ha a fájl megváltozott, és az oldal újratölti — az új export hiánytalanul megjelenik. A szerveren közzétett térképeket ez nem érintette.

Elég a bővítményt frissíteni, újraexportálni nem kell.
