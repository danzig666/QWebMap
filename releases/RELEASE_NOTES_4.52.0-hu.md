# ⚠️ NOT FOR GENERAL USE

**This is a special edition for Hungarian zoning plans (HÉSZ, `szab_ov` layer conventions), made for one office's own projects. If you are not sure you need it, you don't.**

## 👉 [Download the generic edition instead (QWebMap 4.52.0)](https://github.com/danzig666/QWebMap/releases/tag/v4.52.0)

or always the newest generic version: [latest release](https://github.com/danzig666/QWebMap/releases/latest).

---
**QWebMap HÉSZ 4.52.0**

QWebMap (formerly QGIS2VectorTiles (fork)) started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin.

Ez a **magyar HÉSZ változat** (`hu-hesz` ág): a generikus 4.52.0 minden funkciója, plusz a magyar
településrendezési terv előbeállítása. Leírás: `docs/hu/HESZ.md`.


### Új (a generikus 4.52.0-ból): közzététel parancssorból
Új Processing eszköz, a **Publish web map (saved settings)**: a projektben mentett közzétételi beállítások webtérképét exportálja és teszi közzé a beállított célhelyre, pontosan úgy, mint a Publish Web Map ablak *Publish* gombja — ablak és kérdések nélkül. Így a QGIS saját parancssori futtatója is el tudja végezni, pl. szkriptből vagy ütemezett feladatból. Windowson:

```bat
qgis_process-qgis.bat plugins enable QWebMap
qgis_process-qgis.bat run QGIS2VectorTilesFork:publish_web_map --PROJECT_PATH="C:\terkepek\varos.qgz"
```

- `--ACTION=1`: csak helyi export; `--OUTPUT_DIR`: másik mappába; `--EXTENT`: más terület; `--SETTINGS`: több mentett beállítás közül a cím vagy webcím szerint.
- Ha a közzétételhez jóváhagyás kell (az első, vagy változott, mi lesz nyilvános), megáll, amíg az ablakban vagy a `--APPROVE=true` kapcsolóval jóvá nem hagyják; a `--SAVE_PROJECT=true` a jóváhagyást a projektfájlba menti.
- A hitelesítő adatok a mentett QGIS hitelesítési beállításból, vagy a `QWEBMAP_ACCESS_KEY_ID` / `QWEBMAP_SECRET_ACCESS_KEY` környezeti változókból jönnek (SSH: `QWEBMAP_SSH_PASSWORD`, vagy kulcs / ssh-agent). Sosem kerülnek a projektbe vagy a kimenetbe.

Részletek a README *Publish from the command line* részében.
