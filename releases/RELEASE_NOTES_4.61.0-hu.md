# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.61.0)](https://github.com/danzig666/QWebMap/releases/tag/v4.61.0)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.61.0**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.61.0 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

Hibajavító kiadás: a 4.60.0 teljes kódellenőrzése 122 hibát talált (2 súlyosat, 52 közepeset, 68 kisebbet). Szinte mind javítva; a kivételek a végén.

### A legfontosabb javítások
- **Egy téves „abszolút helyi útvonal” az export legvégén leállította az exportot.** A szivárgásvizsgálat minden betűt, kettőspontot és sortörést tartalmazó szöveget (pl. `Zone:` és egy új sor egy felugró ablakban) a gépen lévő útvonalnak vett. A JSON-szövegeket most úgy olvassa, ahogy megjelennek; a manifest szövegeit az export elején ellenőrzi.
- **Online közzététel régi boto3/botocore-ral** (Linux-disztribúciók csomagjai): minden feltételes feltöltés hibát adott. Most csak az ezt támogató SDK-t használja, különben a bővítmény saját példányát, egészében. Minden S3-kompatibilis szolgáltatás csak szükség esetén kap ellenőrzőösszeget (az újabb SDK-k sok szolgáltatást elrontottak, nem csak az R2-t).
- **Képernyőegységben eltolt vonal majdnem visszaforduló törésponttal**: az export összeomlott (OverflowError).
- **A 180. hosszúsági kör közelében lévő elemek** (Fidzsi, Csukotka) kimaradtak a földrajzi vetületű rétegekből, ha a terület szélesebb volt a Földnél.
- **Hőtérképek földrajzi vagy láb alapú vetületű projektben** több százszor halványabbak voltak.
- **Elemfüggő összehasonlítást tartalmazó méretarány-szabályokat** (`"rank" -5 < 3`, `level_1 > 2`) méretarány-küszöbnek vett: az elemek rossz nagyításon jelentek meg, vagy sehol.
- **HTML-feliratok:** a csak betűméretet állító span az egész feliratot átméretezte; az entitással írt karakterekhez (`&eacute;`, `&#8364;`, `&nbsp;`) nem készült glyph; a `</p>` és `</div>` üres sort adott.
- **Vektoros rétegek raszterképei** nem vették figyelembe a réteg új szűrőjét (régi képek, kiszűrt elemekkel).
- **Belső hatások**: egész szabálycsoportok hibáztak, ha az irányablak elérte a vonal végét.
- **Kiadásbiztonság:** a kiadási folyamat a címkézett commitból újraépíti és összeveti a bővítmény zipjét, és megköveteli, hogy az ág tesztjei sikeresek legyenek.

### Export
- A rétegek olvasása vagy az adatkészletek írása közbeni Mégse tisztán megszakít (nincs félkész térkép); a köztes fájlok rétegenként törlődnek, nem a végén.
- A réteg saját `fid` mezője megtartja értékeit; a hosszú rétegazonosítók nem tesznek túl hosszúvá munkafájlneveket; a zárolt, félig írt fájl egy réteget hibáztat, nem az exportot.
- Az üres szakaszos intervallum-jelek fájlláncban is működnek; a smooth() ékezetes mezőnevekkel is működik.
- A `@map_scale`-t olvasó logikai adatvezérelt tulajdonságok működnek; a más réteg mezőjét összesítő tulajdonságokat nem kapcsolja ki; a diagramok követik a réteg méretarány-tartományát és a csak webes korlátokat.
- A Web Mercator projekteket a definíciójuk alapján ismeri fel (ESRI:102100, EPSG:3785 …), nem csak EPSG:3857 alapján.
- Az adatvezérelt felirat-negyed, -eltolás és -távolság jelentve (a stílus a fix értéküket tartja), nem ír fölösleges csempemezőket. A szövegformátum adatvezérelt tulajdonságai is jelentve (szigorú exportnál megállítják).
- A „méter méretarányban” sraffozástáv és nyílméret átváltva (láb vetületek); a kitöltött vonal megtartja átlátszóságát, eltolását és adatvezérelt szélességét/színét.
- Sprite-ok: az alszimbólumok pixelméretei helyesen túlmintavételezve; a tartalék mintázat-előnézetek kicsik (a túl nagy sprite-lapra figyelmeztet); a hosszú kiemelővonalak nincsenek levágva.
- Hibás keret-, ballon- vagy kiemelőkép esetén a feliratok megmaradnak (kép nélkül); a külső ragyogás megtartja színe átlátszóságát; a feliratakadályok egy menetben készülnek (nagy projekteken perceket gyorsít).
- A stílusváltozatok egyedi értékeit SQL-lel, gyorsítótárazva olvassa (milliós rétegeknél percekig tartott).
- A csempe-gyorsítótár észreveszi a vonalösszefűzést befolyásoló változásokat; az induló segédfolyamatok alatt a QGIS reagál; a Mégse az egyesítés és összefűzés közben is működik; az egymásba ágyazott GDAL-zár nem akad el.

### Közzététel
- A kimeneti mappa az export elejétől zárolva van (egy összeomlott QGIS által hagyott zárat eltávolít), nem csak a végén.
- A helyi térkép biztonságosan cserélődik: a helyszín-áthelyezés előre tervezett, használatban lévő fájlnál újrapróbál, a félkész kiadást eltávolítja. A korábbi munkamappákat törli; az online kiadások helyi másolataiból kettőt tart meg.
- A *MBTiles only* most MBTiles-t ír; exportonként egy MBTiles és ZIP, cserélve és megmutatva.
- A raszteres rétegek az adott projekt nagyítás ↔ méretarány viszonyát használják, nem az előző exportét.
- Helyi rácsfájlt használó projekt-vetület a fájl útvonala nélkül kerül közzé.
- A domborzat áttekintő képei csak a terület körüli DEM-részre készülnek (nem egy országos DEM-re), és a Mégse leállítja.
- Keresés: az előtag-keresés minden írásrendszerben megtalálja a rekordokat.
- Alaptérkép: megszakadt kapcsolatnál újrapróbál; sérült archívumnál érthető üzenet; nem tartja az összes csempét memóriában.
- S3: elveszett többrészes lezárási választ elfogad, ha az objektum ott van; a rossz rendszeróra meg van nevezve; a megőrzés nem törli a még futó feltöltéseket.
- Az adatközlési áttekintés felsorolja az elemek megjelenítési feliratát és mezőit (a mélylinkekhez közzétéve).
- A Windows hosszú útvonal kockázatát az export elején jelzi.

### Közzétételi ablak
- Az egyszerű nézet puszta megjelenítése már nem írja felül a nagyítási szinteket (és a mentett beállításokat); az importált beállítások megtartják nagyításaikat.
- A több soros *Visible scales…* sosem ad fordított (soha nem látható) tartományt; az ilyen mentett tartományokra figyelmeztet.
- A **Publish** csak akkor használja újra az utolsó helyi exportot, ha a rétegek adata, stílusa, forrása és vetülete nem változott.
- A *Make a ZIP to send* csak a térkép aktuális változatát csomagolja, és a lemezhibát félkész ZIP nélkül jelzi.
- Az objektumtár-kulcsokat tartalmazó beállításfájlok csak a tulajdonos számára olvashatók.
- A bővítmény eltávolítása helyi export közben megszakítja az exportot.

### Helyi megjelenítő és szerver
- A helyi csempeszerver csak a saját gép oldalainak válaszol (nincs `Access-Control-Allow-Origin: *`: más weboldalak kiolvashatták az exportált térképet).
- Az indítók csak egy korábbi QWebMap csempeszervert állítanak le, más programot a 9000-es porton soha; Windows-on a `& ( ) ^ @` karaktert tartalmazó és a hálózati (UNC) mappák működnek; macOS-en megtalálja a szerver Pythonját.
- A `#`, `?` vagy `%` karaktert tartalmazó exportmappák megnyílnak.
- A Processing export a vetület nélküli kiterjedést a projekt vetületében olvassa, a hiányzót elutasítja.

### Webes megjelenítő
- Vékony, hosszú poligonok feliratelhelyezése nem blokkolja másodpercekig az oldalt; a 180. hosszúsági kör közelében is elhelyezi a feliratokat.
- A korlátokkal (`max`, `min`, `case`, `match` …) megadott térképegységű feliratméreteket helyesen méri az ütközésekhez.
- A tartománykéréseket figyelmen kívül hagyó szervernél a keresőcsomag egyszer töltődik le, nem szilánkonként.
- A hosszú permalinkek a leghosszabb listáikat hagyják el, nem a nézetet.

### Tesztek és CI
- A CI a QGIS 3.44-et (a deklarált minimumot) teszteli 3.34 helyett; a MapLibre-, JS/Python-paritás és valódi S3 SDK tesztek futnak, nem maradnak ki; az éjszakai tesztválasztás minden bővítményfájlt figyel.

### Nem javítva (ismert korlátok)
- Ha a 9000-es porton már egy másik program figyel, a helyi megjelenítő továbbra sem indul el (azt a programot már nem állítja le).
- A feltöltési ablakok hálózati műveletei (kapcsolatteszt, kiadások listája) továbbra is az ablak szálában futnak.
- Nagyon nagy archívumokat minden közzétételkor újra kivonatol (lassú, de helyes).
- A hosszú Windows-útvonalakra csak figyelmeztet.
- Az S3 SDK választása az egész QGIS-folyamatra érvényes (dokumentálva).
- Két egyidejű export egy QGIS-ben még megoszt némi globális állapotot (nagyrészt már exportonkénti).
- A többrészes források ismétlődő `fid` értékeinél a QGIS korlátja marad.
- A Windows-indító idézőjelezési javítása csak Linuxon tesztelt.
