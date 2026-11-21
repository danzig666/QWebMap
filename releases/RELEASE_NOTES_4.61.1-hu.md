# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.61.1)](https://github.com/danzig666/QWebMap/releases/tag/v4.61.1)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.61.1**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.61.1 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.

### Javítva
- **A helyi megjelenítő akkor is elindul, ha a 9000-es portot egy másik program használja.** Az exportált csomag megjelenítője (*activate_server*) nem működött, ha a 9000-es porton már figyelt egy másik program (MinIO, PHP-FPM, Portainer, fejlesztői szerver …). Most a csempeszerver a következő szabad portot veszi (9001, 9002 …), és a megjelenítő, a stílusa és a böngésző is ezt a portot használja. A 9000-es porton lévő programot nem bántja.
- A megjelenítő újraindítása csak a korábbi QWebMap csempeszervert állítja le, akármelyik porton fut, így nem halmozódnak a rejtett szerverek.
- Windows-on a csempeszerver nem osztozik a porton más programmal, és megtartja a portját, ha a megjelenítő lapja még nyitva van.
