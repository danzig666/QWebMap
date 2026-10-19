# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.51.1)](https://github.com/danzig666/QWebMap/releases/tag/v4.51.1)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.51.1**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.51.1 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.


### Javítva (a generikus 4.51.1-ből: a 4.51.0 QGIS 4 szimbológiájának teljes hibakeresése)
- **Marker line és Hashed line**
  - A *Trim distance* és a *Blank segments* rossz mértékegységben mérődött a töréspont-, első/utolsó töréspont-, szakaszközép- és középpont-jelölőknél, ha a projekt koordináta-rendszere nem Web Mercator (pl. EOV). Most a projekt egységeiben mérődik, mint a QGIS-ben.
  - Az adatvezérelt trim, blank segments és extra items kifejezések most a réteg saját koordinátáit és változóit látják (`@layer_name`, `$length` a projekt ellipszoidján) és a teljes többrészes elemet; az `@map_scale` nagyításonként értékelődik, és a `@geometry_part_num` / `@geometry_ring_num` is be van állítva.
- **Feliratok**
  - A hosszú *nyújtott* görbe feliratok (kb. 1000 px felett) levágva vagy egyáltalán nem jelentek meg. Most betűnként, a vonal mentén kerülnek a helyükre, mindegyik saját ütközési dobozzal; a szóköz-nyújtás most pontos.
  - A *Place characters at vertices* többrészes poligonoknál rossz töréspontokra tette a betűket, HTML-formázott feliratnál minden töréspontra a teljes szöveget írta, és szétvágta az emojikat és ékezetes betűket. Mindhárom most a QGIS szerint működik.
  - A *Split label text lines over parts* most akkor is az i. részre teszi az i. sort, ha egy szabály más részeket kihagy, és geometriagenerátornál a generált részekre osztja, mint a QGIS. Az adatvezérelt sortörő karakter és sorhossz is érvényesül.
  - Az adatvezérelt *label every part* értéket pontosan úgy olvassa, mint a QGIS.
- **Maszkolás**: a kikapcsolt maszkjelölő, vagy amelyik csak nem közzétett rétegeket maszkol, már nem takarja le háttérszínnel az alatta lévő térképet (QGIS 3-on is).

Az ezeket a beállításokat nem használó projektek pontosan úgy exportálódnak, mint eddig. A javításokhoz a térképet újra kell exportálni.
