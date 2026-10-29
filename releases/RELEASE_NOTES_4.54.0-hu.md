# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.54.0)](https://github.com/danzig666/QWebMap/releases/tag/v4.54.0)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.54.0**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.54.0 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.


### Új (a generikus 4.54.0-ból)
- **A nézetek publikálják a rétegeiket.** Ha a Map fülön a *Map themes offered as views in the web map* listában bepipálsz egy témát, a téma által mutatott rétegek publikálva lesznek, induláskor láthatóként. Csak hozzáad: egyetlen réteget sem vesz ki, így több téma kombinálható. Eddig egy nézet mutathatott nem publikált rétegeket (azok egyszerűen hiányoztak belőle).
- **Lassúság-ellenőrzés export előtt.** Minden export előtt a bővítmény megbecsüli, mennyire lesz nehéz a webtérkép kicsinyítve (ugyanazzal a becsléssel, mint a *Zoomed-out load…* gomb). Ha egyes rétegek lassítanák, kiírja, melyek, és melyik zoomtól érdemes a jeleiket vagy feliratukat rajzolni: a *Make it faster…* megnyitja a javaslatokat (egy kattintással alkalmazhatók, utána az export folytatódik), az *Export as it is* változatlanul exportál. A *Don't check this before exports* pipával az ellenőrzés kikapcsolható; a *Zoomed-out load…* gomb továbbra is működik.

### Változott
- **Nagyobb bővítményikon.** Az ikon körül széles átlátszó margó volt, ezért kisebbnek látszott a többi eszköztár-ikonnál; most kitölti a négyzetét.
