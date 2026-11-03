# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.58.2)](https://github.com/danzig666/QWebMap/releases/tag/v4.58.2)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.58.2**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.58.2 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Változott
- **Élesebb, vékonyabb vonalak a kizoomolt képeken.** A kizoomolva képként rajzolt réteg (*Zoomed out* oszlop: *image*) normál felbontásban készült, így a QGIS hajszálvonalai (nulla vastagságú vonalak, pl. telekhatárok) ott egy teljes pixel szélesek voltak, nagy felbontású képernyőn pedig elmosódtak. A sűrű telekháló egybefolyt, éppen az, amit a *Thin hairlines* (Output beállítások, alapból bekapcsolva) a vektoros vonalaknál elkerül. Ha ez be van kapcsolva, a képek mostantól kétszeres felbontásban készülnek: a hajszálvonalak ugyanolyan vékonyak, mint a vektorosak, minden más méret ugyanaz marad, és a vonalak nagy felbontású képernyőn is élesek. A képek kb. háromszor nagyobbak (100 000 telek 15-ös zoom alatt: 3,6 MB → 10,1 MB, még mindig harmada annak, mintha minden elem rajzolódna), az export alig lassabb.
