# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.51.0)](https://github.com/danzig666/QWebMap/releases/tag/v4.51.0)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.51.0**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.51.0 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.


### Új (a generikus 4.51.0-ból): QGIS 4 szimbológia
A QGIS 4 új beállításokat hozott a meglévő szimbólumokhoz és feliratokhoz. Ezek most a webtérképen is úgy jelennek meg, mint a QGIS-ben (QGIS 3-on nincs változás):

- **Marker line és Hashed line**
  - *Trim distance* az elején és a végén (QGIS 4.2): a jelölők a levágott vonalon vannak.
  - *Blank segments* (QGIS 4.0): a kihagyott szakaszokon nincs jelölő, részenként és gyűrűnként mérve, ahogy a QGIS méri.
  - *Extra items* (QGIS 4.2): a többletjelölők a saját helyükön és szögükkel.
- **Feliratok**
  - *Split label text lines over parts* (QGIS 4.0): a többrészes elem minden része a felirat saját sorát kapja.
  - Görbe feliratok *Place characters at vertices* módban: minden betű a saját töréspontján, a QGIS szerint elforgatva.
  - Görbe feliratok *Stretch character spacing* / *Stretch word spacing* módban: a felirat kitölti a vonalat (a szóköz-nyújtás közelítő: a webtérkép egész lépésekben szélesíti a szóközöket).
- **Selective masking sets** (QGIS 4.0): a maszkkészleten át maszkoló feliratok és maszkjelölők ugyanazt a kitakarást kapják, mint a saját listával maszkolók.

Ahol a webtérkép csak közelíteni tud (pl. a böngésző által elhelyezett jelölők a legnagyobb nagyításokon, vagy az *Ignore whitespace in collisions*), az export jelentése jelzi.
