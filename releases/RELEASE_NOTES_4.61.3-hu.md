# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.61.3)](https://github.com/danzig666/QWebMap/releases/tag/v4.61.3)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.61.3**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.61.3 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Javítva
- **Egy egész réteg poligonfeliratai eltűnhettek.** A poligonfelirat elhelyezése előtt minden elem részei összevonásra kerülnek (dissolve). Kis nagyításon az alakzatok az adott nagyítás durva rácsához igazodnak, és néhány érvénytelenné válhat (önmagát érintő gyűrű). Ilyenkor az összevonás az egész rétegre hibát adott, és egyetlen felirata sem került közzé („Not published (rule failed): … The algorithm returned no output” az exportnaplóban). Ez előfordult például egy országos térképen, amelynek a legnagyobb nagyítása kicsi. Az ilyen alakzatokat most kijavítja és újra összevonja; ha ez sem sikerül, a részeket összevonás nélkül csoportosítja. A térkép utolsó nagyításán túl látszó feliratok az utolsó csempékből rajzolódnak, ahogy kell.
