# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.58.5)](https://github.com/danzig666/QWebMap/releases/tag/v4.58.5)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.58.5**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.58.5 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Javítva
- **A QGIS 4 bezáródhatott raszterrétegeket tartalmazó térkép exportja közben.** Amíg az export a raszterrétegeket (és a kizoomolt képeket, a domborzatot) rajzolja, a csempék a háttérben készülnek; ez a rész az export GeoPackage-fájljait is megnyitotta a GDAL-lal a QGIS-en belül. A QGIS 4.2 Windows-os változatán a kettő a GDAL-ban összeakadt, és a QGIS üzenet nélkül bezáródott (az export naplójában hozzáférési hiba látszott). A GeoPackage-fájlokat mostantól csak a GeoPackage meghajtóval nyitja meg (a GDAL nem próbálja végig rajtuk az összes meghajtóját), és a háttérben futó GDAL-munka megvárja, amíg a raszterrétegek elkészülnek. A csempék vágása közben folytatódik: egy két domborzati réteget és 107 réteget tartalmazó tesztprojekt ugyanannyi idő alatt exportálódott, mint korábban.
- **Az export naplója mostantól azt is megírja, miért nem indultak el a segédfolyamatok.** A nagy exportok segéd-QGIS-folyamatokat használnak; ha ezek nem indulnak el, az export magában a QGIS-ben folytatódik (lassabban). Az `export_log.txt` mostantól tartalmazza a hibaüzenetüket, amely eddig csak egy ideiglenes mappában volt.
