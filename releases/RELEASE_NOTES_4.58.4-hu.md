# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.58.4)](https://github.com/danzig666/QWebMap/releases/tag/v4.58.4)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.58.4**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.58.4 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Gyorsabb
- **A látható felületrészre tett feliratok *Horizontal*, *Free* és *Around point* elhelyezéssel kizoomolva 2–3-szor könnyebbek.** A 4.58.3 az *Over point* feliratokat gyorsította; most ezek is sorra kerültek:
  - Kizoomolva a legtöbb kis felület egy korábban elhelyezett felirat alá esik. Ezekben szabad helyet keresni volt a munka nagy része (egy frissítés 61 %-a), és nem talált egyet sem. Az ilyen felirat dobozába teljesen beleeső felületet mostantól azonnal kihagyja.
  - Minden felület csempénként egyszer dekódolódik minden elhelyezésnél (vonalaknál is), és ami csak az egész felülettől függ, zoomonként egyszer számolódik: a rangsorolt jelölt helyek (*Horizontal*), a szög (*Free*), a súlypont és a körülötte lévő helyek (*Around point*), a felirat mérete.
  - Kevesebb memóriafoglalás a közeli feliratok keresésekor.

  Egy feliratfrissítés egy 100 000 telkes tesztrétegen (Chrome szoftveres grafikával, így a számok csak egymáshoz mérhetők), 12 / 13 / 14-es zoom:

  | | 4.58.3 | 4.58.4 |
  |---|---|---|
  | Horizontal | 3,6 / 2,6 / 1,2 s | 1,1 / 0,65 / 0,4 s |
  | Free | 3,6 / 2,7 / 1,25 s | 1,2 / 1,0 / 0,7 s |
  | Around point | 1,7 / 1,0 / 0,33 s | 1,4 / 0,7 / 0,25 s |

  A feliratok ugyanazok: 540 véletlen elrendezésen (a három elhelyezés, eltolt nézetek) összevetve a 4.58.3-mal egy sem tért el.
