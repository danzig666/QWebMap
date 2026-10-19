# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.50.1)](https://github.com/danzig666/QWebMap/releases/tag/v4.50.1)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.50.1**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.50.1 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.


### Javítva (a generikus 4.50.1-ből)
Teljes hibakeresés a bővítményben és a webtérképen, kb. 50 javítás, új funkció nélkül.

**QGIS oldal**
- **A Publish ablak megnyílik Python 3.10-en és 3.11-en is** (a legtöbb linuxos QGIS); ott szintaxishibával leállt.
- **Azoknak a betűtípusoknak a feliratai, amelyek normál stílusát „Normal”-nak hívják** (honosított Windows, egyes linuxos betűk) láthatatlanok voltak a webtérképen: a karakterkészletük nem készült el.
- **Felugró ablak és keresés másolt rétegeken:** a memóriarétegek, a mentetlen szerkesztésű, illesztett (join) vagy virtuális mezős rétegek egy másik elem adatait mutathatták.
- **A QGIS-ben beállított Shapefile-kódolás** (*Data source encoding*) megmarad: az ékezetes szövegek eddig elromolhattak.
- **Projekt- és rétegváltozók** (`@sajat_vastagsag`, `@layer_name`) működnek a stílusokban és szűrőkben; eddig üresek voltak, vagy az ideiglenes másolat nevét adták.
- **Az export-gyorsítótár** észreveszi a MapInfo (.tab) és más többfájlos rétegek szerkesztését.
- **A geometriai kifejezés szerinti rajzolási sorrend** (pl. `$area`) megmarad; nagyon nagy vonalrétegeken nem vesznek el az intervallum-jelek.
- **Az adatvezérelt többsoros igazítás** működik a feliratoknál.
- **Az értéklistás szűrők tizedes és igen/nem mezőkön** működnek a webtérképen (egy érték bejelölése eddig mindent elrejtett).
- **Az ablak bezárása után befejeződő feltöltés** már nem menti a beállításait egy közben megnyitott másik projektbe.
- **Az export nem távolítja el a projekt saját, rétegfában nem látható rétegeit** (illesztések és értékrelációk kerestáblái).
- Export közben a QGIS többi része le van tiltva (egy réteg export közbeni törlése összeomlást okozhatott).
- A *Title* módosítása már nem költözteti új címre a már közzétett térképet.
- A csoportos módosítások kihagyják a lista szűrője által elrejtett rétegeket; a *Visible scales…* több rétegen csak a módosított határokat változtatja.
- A szűrőcímek és az összecsukott csoportok megmaradnak; két azonos nevű réteg közül a másodikat is ki lehet választani; a *Preview* követi az új kimeneti mappát.
- A feltöltés a térkép belépőoldalát cseréli utoljára, így egy sikertelen feltöltés nem hagyhatja működésképtelenül az élő térképet.
- Élő WMS/XYZ rétegek: max. nagyítás nélkül 18-as zoomig mennek (mint a QGIS-ben); a Web Mercatorban rajzolni nem tudó WMS renderelve kerül a kiadásba üres réteg helyett; a PNG8/WebP WMS-képek átlátszók maradnak; az élő rétegek megjelennek a *Review*-ban, és új jóváhagyást igényelnek.
- A Processing eszköz hibát jelez, ha semmi sem készült el.

**Webtérkép**
- **Feliratok ugrás után** (keresés, link, ugrás a rétegre): a következő mozgatásig hiányozhattak.
- A felugró ablak, a keresés és a telekinformáció hálózati hiba után újrapróbálkozik, nem marad hibás az oldal újratöltéséig.
- Keresés: az *Enter* a begépelt szövegre hat (nem egy bezárt lista találatára); a lista nem nyílik újra „Betöltés…” állapotban.
- A hosszú szűrős linkek megtartják a szűrőket; a beágyazott térképből megosztott linkek a teljes térképet nyitják; zárolt réteget link nem rejthet el.
- A feliratok visszakapcsolnak, ha a térképnek nincs Layers füle; az élő rétegek megjelennek a csak látható elemeket mutató és a nyomtatott jelmagyarázatban; az övezeti előírások nyomtathatók bekapcsolt Street View mellett is.
- Mérés: Enter/Escape után nem marad ott a régi illesztési kör; törölt vonalhoz nem rajzolódik magassági metszet, és egy hiányzó domborzati csempe csak hézagot hagy; 3D-ből nyomtatva megmarad a dőlésszög; az áttekintő térkép nem tölti a Street View lefedettséget.
- Pontosabb feliratpozíciók kis poligonokon.
