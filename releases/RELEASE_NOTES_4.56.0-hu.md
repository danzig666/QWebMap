# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.56.0)](https://github.com/danzig666/QWebMap/releases/tag/v4.56.0)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.56.0**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.56.0 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

A kiadás nagy része az eredeti bővítmény ([GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles)) 2026. október–novemberi változataiból átvett ötlet, a QWebMap saját exportálójában és nézőjében újra megvalósítva. Minden tételnél szerepel, honnan jön az ötlet.

### Szimbólumok
- **Szimbólumpuffer** (*Buffer*): a jelölőszimbólum puffere egyszer, az egész szimbólum körül, minden rétege alatt rajzolódik, ahogy a QGIS rajzolja (eddig rétegenként). Szövegként rajzolt betűjelölőnél szöveghalo lesz belőle. *Ötlet: GallPeters/QGIS2VectorTiles (pufferjavítás).*
- **Adatvezérelt vonalvágás** (*Trim lines*) és **adatvezérelt kitöltés-eltolás** (*Offset*) elemenként. *Ötlet: GallPeters/QGIS2VectorTiles.*
- **Point displacement címkék**: a *Point displacement* megjelenítő címkéi a széthúzott pontok mellett. *Ötlet: GallPeters/QGIS2VectorTiles.*
- **Nyilak** (*Arrow*): adatvezérelt szélesség, fejméret, eltolás, fejtípus és nyíltípus elemenként. *Ötlet: GallPeters/QGIS2VectorTiles.*

### Címkék
- **Betűméret-írásmód** (*Type case*: *All uppercase*, *Title case*, …) a QGIS szerint, adatvezérelten is; a címke eleji és végi szóközök megmaradnak. *Ötlet: GallPeters/QGIS2VectorTiles.*
- **Adatvezérelt prioritás** (*Priority*) dönti el, melyik címke marad ütközéskor; **adatvezérelt betűcsalád** elemenként. *Ötlet: GallPeters/QGIS2VectorTiles.*
- **Force point inside polygon**: a felület címkéje a felületen belül marad. *Ötlet: GallPeters/QGIS2VectorTiles.*
- **Kiemelővonalak** (*Callouts*) pontcímkéknél: *Simple*, *Manhattan*, *Curved* és *Balloon*, ahogy a QGIS rajzolja. *Ötlet: GallPeters/QGIS2VectorTiles (ballon és alakos kiemelők).*
- **Látható felületrészek címkéi** a felületek saját csempéiben utaznak, nem a felületek külön másolatában: kisebb webtérkép, gyorsabb export. *Ötlet: GallPeters/QGIS2VectorTiles (címkék a megjelenítő elemeiből).*

### Gyorsabb
- **A néző indulása**: a modulok előtöltve, a stílus, az archívumok és a nyelv egyszerre töltődik. *Ötlet: GallPeters/QGIS2VectorTiles (párhuzamos indulás).*
- **Export**: elég szabad memória esetén a csempék memóriában készülnek (különben lemezen), a minden elemet megtartó szabályszűrők nem másolódnak, olcsóbb a kiterjedésre vágás, tömör JSON-fájlok. *Ötlet: GallPeters/QGIS2VectorTiles (memóriabeli ogr2ogr munkaadatbázis, tömör JSON, gyorsabb GDAL-export).*

### Biztonság
- Az export munkafolyamata csak a bővítmény saját adatait fogadja el (osztály-engedélylista), a nem biztonsági hash-ek így vannak jelölve. *Ötlet: GallPeters/QGIS2VectorTiles (Bandit-észrevételek).*
