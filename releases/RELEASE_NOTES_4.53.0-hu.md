# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.53.0)](https://github.com/danzig666/QWebMap/releases/tag/v4.53.0)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.53.0**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.53.0 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.


### Javítva (a generikus 4.53.0-ből)
- **A raszteres rétegek olyan élesek, mint a QGIS-ben.** A szkennelt tervlapok, ortofotók a webtérképen eddig elmosódottabbak voltak, életlen szélekkel (a QGIS saját — bilineáris — rajzához mérve 70–85 %-os élesség). Három ok, mindhárom javítva:
  - A *Like the image* felbontás egy zoomszinttel korábban megállt; tovább nagyítva a böngésző a már átmintázott csempéket nagyította, kétszer simítva. Most egy szinttel finomabb, mint a kép (kb. 2,7× nagyobb raszter-archívum; rétegenként továbbra is választható durvább pixelméret). Az online csempeszolgáltatások a saját legfinomabb szintjükön maradnak.
  - A csempéket zoomszintek között és nagyított kijelzőn (125 %, 200 %) felnagyította; most a következő finomabb csempéket tölti be, és csak kicsinyít.
  - A kicsinyített csempéket elmosott, fél méretű másolatból rajzolta; most magából a csempéből, ahogy a QGIS.
  - Eredmény: a QGIS élességének 87–100 %-a (többnyire 90–100 %). Az élő XYZ / WMS rétegek változatlanul töltődnek.
- **Csak raszteres rétegekből álló térkép.** Most már exportálható webtérkép csupa raszteres réteggel (helyi kép, élő XYZ vagy WMS, alaptérképpel vagy anélkül). Eddig az export a „Select at least one vector layer to publish” üzenettel leállt.
- **SciPy nélkül is betöltődik.** A bővítmény nem igényli többé a SciPy csomagot (egyes új QGIS 4 telepítésekben nincs, és ott nem töltődött be). OpenCV-t vagy SciPy-t használ, ha van, különben egy pontos beépített változatot.

A javításhoz a térképet újra kell exportálni (a webtérkép kódja minden kiadás része).
