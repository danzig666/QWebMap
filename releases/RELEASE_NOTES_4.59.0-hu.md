# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.59.0)](https://github.com/danzig666/QWebMap/releases/tag/v4.59.0)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.59.0**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.59.0 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

Az eredeti bővítmény ([GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles)) novemberi verzióinak ötletei, újraírva.

### Új
- **Gyors nagyításkor nincs üres térkép.** Az egy adott nagyítási szinttől megjelenő réteg (épületek, telkek) az eggyel kisebb szint csempéibe is bekerül, ott a saját szintjéig rejtve, így a térkép azonnal kirajzolja, amíg a részletesebb csempék betöltődnek. A későn kezdődő, sűrű rétegeket tartalmazó archívumok nőnek (egy 20 000 épületes próbán legfeljebb kb. harmadával, általában jóval kevésbé).
- **Kicsinyítéskor összefűzött vonaldarabok.** Ahol a *Lighter tiles when zoomed out* kihagyja a fél képpontnál kisebb elemeket, az azonos stílusú vonalakat előbb végponttól végpontig összefűzi, így a sok rövid darabból álló folyó- vagy úthálózat egyben marad (és a csempék kisebbek). Az irányuk mentén rajzolt vonalakat (minták, eltolások) nem fűzi össze. Az összefűzött vonal ezeken a szinteken nem nyit felugró ablakot (nagyítson rá).
- **A pontjelek távol tartják a feliratokat.** Ha egy pontréteg feliratainál be van kapcsolva a *Features act as obstacles* (a QGIS alapértéke), a többi réteg feliratai a QGIS-hez hasonlóan kikerülik a jeleit.
- **Színes, formázott HTML-feliratok.** A HTML-formázású feliratok minden része megtartja a színét, félkövér és dőlt stílusát, betűcsaládját és méretét (legfeljebb 16 rész). A részek háttérszínét nem rajzolja ki (a hűségjelentés jelzi).
- **Use web zoom scales in QGIS…** (Map fül): a projekt méretarány-listáját a webtérkép nagyítási szintjeinek méretarányaira állítja, így a beállított méretarány-tartományok pontosan egy szintnél kezdődnek és végződnek.

### Változott
- **Felirathátterek:** a teljes kitöltési szimbólummal (minden rétegével) rajzolja őket, nem csak a kitöltés és a körvonal színével.
- **Széles felirat-körítés** (a szövegmagasság kb. ötödénél nagyobb): a QGIS-hez hasonlóan lekerekített dobozként rajzolja a szöveg mögé, nem szögletessé váló glóriaként.
- **A QGIS saját ogr2ogr-ja:** előbb a QGIS mellett keresi, aztán a PATH-on, használat előtt kipróbálja, és továbbadja a QGIS GDAL- és PROJ-adatait. Az exportnapló megnevezi a használt ogr2ogr-t és verzióját. Egy korábban a PATH-on lévő másik GDAL többé nem rontja el az exportot.
- **Gyorsabb első megjelenítés:** az R2/S3-ra a betűkészleteket tömörítve tölti fel (kb. ötöd méret); a feliratok 300 helyett 100 ms alatt jelennek meg.
- Egy nagyítási szint pontos méretarányától fél egységen belüli méretarány azt a szintet jelenti (az 1:1066 többé nem ad hozzá egy plusz csempeszintet).

### Javítva
- A kikapcsolt *Draw labels* beállítású (csak akadályként működő) feliratokat is exportálta és kirajzolta.
