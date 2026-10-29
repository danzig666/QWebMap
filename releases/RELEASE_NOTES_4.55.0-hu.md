# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.55.0)](https://github.com/danzig666/QWebMap/releases/tag/v4.55.0)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.55.0**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.55.0 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.


### Változott (a generikus 4.55.0-ból)
- **Nincs többé raszteres csempekorlát.** A 400 000 csempénél nagyobb raszterréteget a bővítmény már nem utasítja el. Export előtt egy *Very large raster layer* figyelmeztetés jelzi, hogy az export órákig tart és nagyon nagy webtérképet készít, és rétegenként megnevezi, melyik beállítás teszi naggyá (a réteg *Sharpest detail* értéke, vagy „Like the map” esetén a Map fül *Maximum tile zoom* értéke), és mivel csökkenthető: a csempeszám egy fokkal durvább részletességnél, a legfinomabb fok, amely 400 000 alá visz, és hogy mennyivel kisebb kiterjedés kellene. Az *Export anyway* folytatja, a Cancel leállítja. Az export naplója is figyelmeztet, és az Interaction fülön a réteg csempebecslése is jelzi.
- **Felhasználói útmutató telefonon.** Az útmutató (angol) keskeny kijelzőn *Contents* gombbal nyitja a tartalomjegyzéket.

### Változatlan ebben a változatban
- A generikus változatban az új beállítások alapnyelve mostantól angol; a HÉSZ változatban **továbbra is magyar** (a mentett beállítások megtartják a nyelvüket).
