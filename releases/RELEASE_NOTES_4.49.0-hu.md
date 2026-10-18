# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.49.0)](https://github.com/danzig666/QWebMap/releases/tag/v4.49.0)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.49.0**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.49.0 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Változott (a generikus 4.49.0-ból)
- **Kevesebb memória nagyított és nagy felbontású képernyőn.** A *Low memory web map* (alapból bekapcsolva) mostantól CSS-pixelenként egy eszközpixellel rajzolja a térképet. A térkép WebGL-pufferei a képernyő nagyításának négyzetével nőnek: egy 150 %-ra nagyított 1920×1080-as képernyőn 160 MB-ot foglaltak, most 50 MB-ot (egy városi térkép lapja betöltés után 464 → 355 MB, böngészés után 692 → 523 MB). Ilyen képernyőn a térkép kissé lágyabb; teljes élességhez kapcsold ki az opciót.
- **A poligon vagy vonal látható részére helyezett feliratok egyetlen forráson osztoznak** rétegenként külön forrás helyett (egy városi térképen 14), amelyek mindegyike saját csempéket és indexet tartott a böngészőben.

### Javítva
- A feliratelhelyezés minden valaha feliratozott elemről megtartott egy bejegyzést, így egy nagy térkép böngészésekor a lap memóriája megállás nélkül nőtt.
