# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.58.10)](https://github.com/danzig666/QWebMap/releases/tag/v4.58.10)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.58.10**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.58.10 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Javítva
A bővítmény teljes hiba- és használhatósági átnézése; a fő javítások:

**Közzététel**
- **A raszteres élő réteg címébe írt bejelentkezési adat többé nem kerül nyilvánosságra.** Ha egy webes csempe- vagy WMS-réteg címe felhasználónevet és jelszót tartalmazott (`https://felhasznalo:jelszo@host/…`), a réteg élőben töltődött be, és a címe a jelszóval együtt bekerült a közzétett fájlokba. Az ilyen réteget mostantól a kiadásba rendereli, mint a többi bejelentkezést igénylő réteget.
- A feltöltés előtti szivárgásellenőrzés a nagy archívumokat részletekben olvassa, nem egyben a memóriába. A `/home/` vagy `/tmp/` részt tartalmazó webcímeket, valamint a felugró ablakokban és a keresőben megjelenő attribútumértékeket többé nem jelzi helyi útvonalként.
- Objektumtár: a fájlellenőrzéseket (HEAD) és a letöltéseket átmeneti hiba után a feltöltésekhez hasonlóan újrapróbálja; egyetlen sikertelen ellenőrzés nem állítja le több ezer fájl feltöltését. A feltöltési napló írása gyorsabb.
- A közzététel utáni ellenőrzésben a szokatlan szerverválaszok sikertelen ellenőrzésként jelennek meg, nem „Publishing failed” hibaként.
- Előnézeti szerver: egy kérés közben lecserélt fájl miatt a böngésző többé nem vár a végtelenségig.

**Export**
- Egy be nem töltött függvényt (bővítményét, projektmakróét) hívó szabályszűrőt nem jegyez meg üres rétegként: a függvény elérhetőségekor a következő export megrajzolja.
- A *Merged when zoomed out* a 100-nál több osztályú rétegek osztályait is összevonja.
- Windowson a segédfolyamatok párhuzamosan indulnak (a QGIS nem fagy le, amíg egyenként elindulnak).
- Egy megszakadt másolás vagy rétegelőkészítés nem hagy félig megírt fájlt, amelyet egy későbbi export újrahasznosítana.
- A helyi megjelenítő ékezetes nevű mappákból is elindul (pl. `C:\Users\Kovács\…`).

**Stílusátalakítás**
- A *meters at scale* egységű jelméretek, jelvonal-közök és poligonon belüli körvonalak fokban vagy lábban mért projektekben is helyesek.
- A *Render only* beállítású festőeffektek megjelennek, a *Modifier only* beállításúak nem (eddig fordítva volt).
- A jel vagy felirat adatvezérelt átlátszatlansága a QGIS-hez hasonlóan felváltja a sajátját (eddig összeszorozta őket); a felirat körítése adatvezérelt szín mellett is megtartja az átlátszatlanságát.
- Az amerikai földmérő lábban és más nem méteres egységben mért projektekben a vonalvastagságok és méretek helyesen skálázódnak.

**Publish Web Map ablak**
- Ha az ablak menthetetlen módosításokkal zárul, előbb rákérdez, ahelyett hogy elvetné őket.
- Az ablak elfér egy 1366 × 768-as képernyőn: a széles fülek görgethetők.
- A rétegek listája követi a projektben az ablak nyitva tartása alatt hozzáadott, eltávolított vagy átnevezett rétegeket.
- A *Local only* cél nem mutat feltöltési mezőket, költséget és jóváhagyást; alaptérkép nélkül annak beállításai szürkék.
- Az importálási kérdésnél a *Cancel* semmit sem importál; a *Current map view* újbóli kiválasztása visszahozza az export előtti kérdést; egy eltávolított kiterjedésréteg helyett a térképnézet érvényes; egy világ kiterjedésű réteg kiterjedését arra vágja, amit egy webtérkép meg tud jeleníteni.

**Webes megjelenítő**
- A tartomány- és értékszűrők az érték nélküli objektumokat a térképen és a felugró ablakokban egyformán kezelik.
- A betöltéskor hibás alaptérkép újra kiválasztható; a kereső sikertelen indexbetöltés után is újra működik.
- A kikapcsolt mélylinkű térképek hivatkozásai nem viszik magukkal a kijelölt objektumot; a hosszú rajzok megmaradnak a megosztott hivatkozásokban.
- Kikapcsolt felugró ablakok mellett is megnyílik a telekjelentés a telekre kattintva; a jelmagyarázat a kikapcsolt csoportok rétegeit is be tudja kapcsolni.
- Az Escape bezárja a felugró ablakot, látszik a billentyűzetfókusz, a térképvezérlők magyar feliratot kaptak, a színek kontrasztosabbak, a hivatkozás másolása jelzi, sikerült-e, telefonon 44 px-esek a gombok, és a rövid cím betöltőoldala a térkép nyelvén jelenik meg.
