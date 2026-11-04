# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.58.3)](https://github.com/danzig666/QWebMap/releases/tag/v4.58.3)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.58.3**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.58.3 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Gyorsabb
- **A látható felületrészre tett feliratok kizoomolva sokkal könnyebbek.** Ezeket a feliratokat (*Polygon labels: Visible polygon*, és a QGIS alapértelmezett *Centroid: visible polygon* beállítása) a megjelenítő helyezi el a térkép mozgatása közben. Sűrű rétegen, kizoomolva a szükségesnél jóval többet dolgozott:
  - Szinte minden, a képernyő körüli felülethez előre feliratot készített, átfedésvizsgálat nélkül: egy 100 000 telkes tesztrétegen 12-es zoomon 26 523 feliratot, amelyből 523 látszott. Mindegyik a MapLibre-hez került és ott tördelődött. Mostantól az előre készített feliratok is kikerülik egymást, ahogy a képernyőn fogják: 746 készül, és ugyanaz az 523 látszik.
  - Minden frissítéskor minden felületet beolvasott és levágott. A teljesen a képernyőn, vagy teljesen azon kívül lévő felület felirata mostantól csempénként egyszer kiszámolt pontra kerül; csak a képernyő vagy egy csempe szélén lévő felületek vágódnak (mindegyik egyszer dekódolva).
  - Mozgatás közben egy frissítés kétszer annyit vár, mint amennyi az előző volt, így a nehéz térkép is folyamatosan rajzol.

  A tesztrétegen 12-es zoomon (Chrome szoftveres grafikával, így a számok csak egymáshoz mérhetők): főszál-munka 74 s → 33 s, worker-munka 25 s → 1,1 s, egy képkocka mozgatás közben 1,3 s → 0,27 s (medián), a térkép megállásáig eltelt idő legfeljebb 7 s → legfeljebb 2,6 s. A képernyőn ugyanazok a feliratok látszanak. A böngésző a legkizoomoltabb nehéz zoomokon a gyorsítótárhoz kb. 50 MB-tal több memóriát használ.
  - Az *Over point* / súlypontos elhelyezésre vonatkozik; a *Horizontal*, *Free*, *Around point* és vonalfeliratok a korábbi utat követik (a fenti első és utolsó változással).
