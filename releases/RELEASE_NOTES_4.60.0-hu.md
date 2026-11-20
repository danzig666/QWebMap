# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.60.0)](https://github.com/danzig666/QWebMap/releases/tag/v4.60.0)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.60.0**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.60.0 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Új
- **Egyszerű nézet.** A Publish Web Map ablaknak van egy **Simple** (egyszerű) nézete az első webtérképekhez és az alkalmi felhasználóknak. Csak a lényeges beállításokat mutatja, közérthetően:
  - **Cím.**
  - **Rétegek:** *On the map* (a térképen), és *Show its information when clicked* (kattintásra az objektum adatai jelennek meg, azonosítók nélkül; ezeket bárki láthatja, aki megnyitja a térképet). A *Use the layers visible in QGIS* a QGIS-ben látható rétegeket jelöli be.
  - **Terület:** amit most a QGIS-térkép mutat, vagy egy réteg kiterjedése, a méretével és a csempék számával.
  - **Meddig nagyíthatnak a látogatók** (lásd lent).
  - **Háttértérkép:** nincs, vagy OpenStreetMap.
  - **Mentés mappába.**

  Egyetlen **Make web map** gomb ezen a gépen elkészíti a térképet, utána **Open in browser** (megnyitás böngészőben), **Open folder** (mappa megnyitása) vagy **Make a ZIP to send** (ZIP küldéshez). Az **Advanced** (haladó) nézet a korábbiak szerint minden beállítást mutat, az online közzétételt is. A két nézet ugyanazokat a beállításokat mutatja, így a váltás bármikor lehetséges, semmi sem változik és semmi sem vész el, a csak a haladó nézetben látható beállításokat pedig megtartja és felsorolja. Az ablak első megnyitáskor egyszer megkérdezi, melyik nézettel induljon; aki korábban már használta, annak haladó nézetben marad.
- **A nagyítás mértéke méretarányként.** Az egyszerű nézetben a részletesség QGIS-méretarány (1:100 000-től 1:500-ig, a projekt vetületében), nem nagyítási szint. A *Choose automatically from the project* (új beállításoknál bekapcsolva) azt a méretarányt választja, amelyen a közzétett rétegek legkisebb jellemző elemei jól láthatók. Legalább annyi részletet ad, amennyit egy csak nagyításkor megjelenő réteg igényel, nagyon nagy területnél pedig kevesebbet, és megmondja, miért. Az **előnézet** a rétegeket azon a méretarányon mutatja, ahogy a QGIS rajzolja, ott, ahol a terület a legrészletesebb.
