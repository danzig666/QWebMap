# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.58.0)](https://github.com/danzig666/QWebMap/releases/tag/v4.58.0)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.58.0**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.58.0 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Változott
- **A *Zoomed-out load* ellenőrzés összevont vagy képes megjelenítést is javasol.** Az ellenőrzés (*Zoomed-out load…* a Map fülön, és export előtt) eddig csak a réteg elrejtését javasolta, és csak ott, ahol az elemei egy-két pixelnél kisebbek. Az a réteg, amely nehéz, de az elemei még jól láthatók (telkek, épületek), nem kapott javaslatot. Mostantól az új *Drawn zoomed out* oszlopban kap: *Merged* (összevont, felületrétegeknél) vagy *Image* (kép), az első olyan zoom alatt, ahol már minden elem elég könnyű. Akkor van bepipálva, ha olyan zoomokat rajzol, amelyeket a *Features from* nem rejt el; a *Features from* pipáját kivéve a réteg minden kizoomolt szinten látható marad. Az *Apply the checked settings* gomb a rétegek listájának *Zoomed out* oszlopába írja.
- A már összevontan vagy képként rajzolt réteget a becslés így számolja (összevonva a csempe kb. 5 %-a, képként nincs vektoros adat), így az export előtti ellenőrzés nem kérdez rá újra. Ha a mód túl alacsony zoomtól indul, közelebbi zoomot javasol.
