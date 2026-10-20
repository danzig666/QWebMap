**QWebMap 4.52.0**

QWebMap started as a fork of [GallPeters/QGIS2VectorTiles](https://github.com/GallPeters/QGIS2VectorTiles) by Jossef Kanter. It is not an official release of the original plugin, and it installs next to it.

This is the **generic** edition — the one to download. (A special Hungarian zoning-plan edition, not for general use, is released separately with a `-hu` tag.)

### New: publish from the command line
A new Processing tool, **Publish web map (saved settings)**, exports the web map of the publication settings saved in the project and publishes it to their destination, exactly as the *Publish* button of the Publish Web Map window does — without the window and without questions. So QGIS's own command-line runner can do it, e.g. from a script or a scheduled task. On Windows:

```bat
qgis_process-qgis.bat plugins enable QWebMap
qgis_process-qgis.bat run QGIS2VectorTilesFork:publish_web_map --PROJECT_PATH="C:\maps\city.qgz"
```

- `--ACTION=1` exports locally only; `--OUTPUT_DIR` exports into another folder; `--EXTENT` overrides the area; `--SETTINGS` picks one of several saved settings by title or web address.
- A publication whose review is due (the first one, or what becomes public changed) stops until it is approved in the window or with `--APPROVE=true`; `--SAVE_PROJECT=true` keeps the approval in the project file.
- Credentials come from the saved QGIS authentication configuration, or from the environment variables `QWEBMAP_ACCESS_KEY_ID` / `QWEBMAP_SECRET_ACCESS_KEY` (SSH: `QWEBMAP_SSH_PASSWORD`, or a key / ssh-agent). They are never written into the project or the output.

See *Publish from the command line* in the README for the details.
