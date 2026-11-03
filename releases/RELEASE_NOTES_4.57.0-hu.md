# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.57.0)](https://github.com/danzig666/QWebMap/releases/tag/v4.57.0)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.57.0**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.57.0 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Új
- **A sűrű rétegek kicsinyítve is látszanak, de könnyebben.** Az Interaction fül rétegtáblájának új *Zoomed out* oszlopa beállítja, hogyan rajzolódjon egy vektoros réteg egy zoomszint alatt, ahelyett hogy ott elrejtenénk (dupla kattintás a cellán, vagy *Selected layers → Zoomed out…*):
  - **merged** — az azonos stílusú (és azonos szűrőértékű) elemek csempénként egy alakzattá egyesülnek. Földrészleteknél, épületeknél sokkal könnyebb; ezeken a zoomokon eltűnnek az egyesített elemek közötti körvonalak és a felugró ablakaik, az attribútumszűrők továbbra is működnek. Az ötlet a csempekészítő eszközök (Tippecanoe, Planetiler) „coalesce” és épület-összevonó lépését követi.
  - **image** — ott a QGIS képcsempékként rajzolja meg a réteg szimbólumait, pontosan úgy, mint a QGIS-ben: ez a legkönnyebb. Ezeken a zoomokon nincs felugró ablak és kiemelés, és a réteg kategóriakapcsolói nem hatnak a képekre; a réteg kapcsolója és átlátszósága igen.
  - A feliratok mindkét esetben szövegként maradnak, a megadott zoomtól pedig minden elem a szokásos módon rajzolódik.
