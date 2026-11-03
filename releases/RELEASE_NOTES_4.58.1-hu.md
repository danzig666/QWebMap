# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.58.1)](https://github.com/danzig666/QWebMap/releases/tag/v4.58.1)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.58.1**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.58.1 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Változott
- **A *Zoomed-out load* csak ott javasolja a *Merged* (összevont) módot, ahol az összevonás nem változtat a megjelenésen.** Az összevonás az egy stílusú elemeket egyetlen alakzattá olvasztja, ezért az ellenőrzés mostantól a réteg szimbológiáját is megnézi. *Merged* javaslatot az egyszerű kitöltésű, legfeljebb 64 stílusú felületrétegek kapnak. *Image* (kép) javaslatot kapnak inkább:
  - a **körvonalas** rétegek (az elemek közötti körvonalak elvesznének), hacsak a körvonal nem teljesen átlátszó;
  - a mintázatos, színátmenetes, shapeburst, SVG, raszteres és egyéb különleges kitöltések (az összevont alakzaton egyszer terülnének el);
  - az adatvezérelt (data-defined) stílusok (szinte minden elem külön stílus);
  - a rajzolási effektusok;
  - a 64-nél több stílus;
  - az inverz felület és a 2.5D megjelenítők.

  Az okot a buboréksúgó írja ki; a *Merged* kézzel továbbra is választható. Az összevont réteg becsült mérete a stílusok számával nő.
- Megjegyzés: a QGIS alapértelmezett felületstílusának van körvonala, így a legtöbb telekréteg *Image* javaslatot kap, hacsak a körvonalat ki nem kapcsolod.
