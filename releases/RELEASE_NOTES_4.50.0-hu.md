# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.50.0)](https://github.com/danzig666/QWebMap/releases/tag/v4.50.0)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.50.0**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.50.0 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.


### Új (a generikus 4.50.0-ból)
- **Élő WMS- és webes csempeszolgáltatás-rétegek.** A projekt XYZ csempe- és WMS-rétegeit a látogató böngészője közvetlenül a saját szerverükről tölti be, nem kerülnek bele a kiadásba (*Load live from its server* az *Interaction* fülön, ezeknél a rétegeknél alapból bekapcsolva). A kiadás kisebb lesz, a térkép pedig mindig a szolgáltatás aktuális képét mutatja. Feltételek: `https` cím, QGIS-bejelentkezés nélkül, és a szerver engedje, hogy más oldalak használják a képeit (CORS — exportkor ellenőrizve; ha nem, a réteg a korábbiak szerint renderelve kerül a kiadásba, a naplóban megjegyzéssel). Az átlátszóság, telítettség, kontraszt és fényerő a QGIS-ből jön. A WMTS-rétegek továbbra is renderelve kerülnek be.
- **WMS-lekérdezés kattintásra.** Ha a kattintás nem talál a térkép saját rétegein elemet, a látható élő WMS-rétegek szervereitől kérdezi le, mi van ott (GetFeatureInfo): GeoJSON, HTML-táblázat vagy szöveg, a felugró ablakban egyszerű szövegként. Ha a szerver nem engedi a válasz olvasását, a felugró ablak egy linket ad, amely új lapon nyitja meg. A jelmagyarázat a szerver saját jelmagyarázat-képét mutatja.
- **Ugrás a rétegre** (*Interaction* fül → *Zoom-to-layer buttons*, alapból kikapcsolva): a webtérkép réteglistájában minden réteg mellett egy gomb a réteg elemeire nagyít a térkép kiterjedésén belül.
