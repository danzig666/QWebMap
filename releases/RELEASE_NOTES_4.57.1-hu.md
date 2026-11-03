# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.57.1)](https://github.com/danzig666/QWebMap/releases/tag/v4.57.1)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.57.1**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.57.1 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Javítva
- ***Zoomed out*: kisebb csempék a választott zoomtól.** Az alacsony zoomon *merged* (összevont) vagy *image* (kép) módban rajzolt réteg minden felületfeliratához külön felületmásolat készült, azokon a zoomokon is, ahol minden elem a szokásos módon rajzolódik. Ettől ezek a csempék nagyjából másfélszer akkorák lettek. A másolat mostantól csak a választott zoom alatt látszó feliratokhoz készül; attól a zoomtól a csempék ugyanazok, mint a beállítás nélkül.

Mérés egy 100 000 telkes szintetikus rétegen, 15-ös zoom alatt (szoftveres grafika, így az idők csak egymáshoz mérhetők):

| | Every feature | Merged | Image |
|---|---|---|---|
| Export | 112 s | 110 s | 28 s |
| A térkép megáll (11–14. zoom) | 1,6–12 s | 0,1–1,1 s | 0,1–1,0 s |
| Letöltve | 9,6 MB | 0,4 MB | 2,6 MB |
| Böngésző memória | 359 MB | 14 MB | 31 MB |
