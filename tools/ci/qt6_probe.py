"""Prints how the QGIS / PyQt in this image take enum arguments (one
::notice annotation per check): run in the QGIS 4 (Qt 6) image to port the
plugin (.github/workflows/qt6.yml)."""

import os
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from qgis.core import (Qgis, QgsApplication, QgsPalLayerSettings, QgsProperty,  # noqa: E402
                       QgsPropertyCollection, QgsSimpleFillSymbolLayer, QgsSimpleMarkerSymbolLayer,
                       QgsSymbol, QgsSymbolLayer, QgsFillSymbol)
from qgis.PyQt.QtCore import Qt  # noqa: E402

app = QgsApplication([], False)
app.initQgis()
out = []


def check(name, fn):
    try:
        out.append(f"OK {name}: {fn()!r}"[:300])
    except Exception as error:  # noqa: BLE001
        out.append(f"FAIL {name}: {type(error).__name__}: {error}"[:300])


layer = QgsSimpleFillSymbolLayer()
marker = QgsSimpleMarkerSymbolLayer()
check("version", lambda: Qgis.QGIS_VERSION)
check("type QgsSymbolLayer.Property.PropertyStrokeWidth", lambda: type(QgsSymbolLayer.Property.PropertyStrokeWidth))
check("Qgis.SymbolLayerProperty", lambda: getattr(Qgis, "SymbolLayerProperty", None))
check("set ddp QgsSymbolLayer.Property", lambda: layer.setDataDefinedProperty(QgsSymbolLayer.Property.PropertyStrokeWidth, QgsProperty()))
check("set ddp Qgis.SymbolLayerProperty", lambda: layer.setDataDefinedProperty(Qgis.SymbolLayerProperty.StrokeWidth, QgsProperty()))
check("set ddp int", lambda: layer.setDataDefinedProperty(int(QgsSymbolLayer.Property.PropertyStrokeWidth), QgsProperty()))
check("get collection property(int)", lambda: layer.dataDefinedProperties().property(int(QgsSymbolLayer.Property.PropertyStrokeWidth)))
check("get collection property(enum)", lambda: layer.dataDefinedProperties().property(QgsSymbolLayer.Property.PropertyStrokeWidth))
check("propertyKeys", lambda: list(layer.dataDefinedProperties().propertyKeys())[:3])
check("type QgsSymbol.Property.PropertyOpacity", lambda: type(QgsSymbol.Property.PropertyOpacity))
check("Qgis.SymbolProperty", lambda: getattr(Qgis, "SymbolProperty", None))
check("symbol set ddp QgsSymbol.Property", lambda: QgsFillSymbol().setDataDefinedProperty(QgsSymbol.Property.PropertyOpacity, QgsProperty()))
check("type QgsPalLayerSettings.Property.Size", lambda: type(QgsPalLayerSettings.Property.Size))
check("pal collection setProperty", lambda: QgsPropertyCollection().setProperty(QgsPalLayerSettings.Property.Size, QgsProperty()))
check("setStrokeStyle int", lambda: marker.setStrokeStyle(0))
check("setStrokeStyle Qt.PenStyle", lambda: marker.setStrokeStyle(Qt.PenStyle.NoPen))
check("strokeStyle type", lambda: type(marker.strokeStyle()))
check("Qt.PenStyle(int)", lambda: Qt.PenStyle(0))
check("QgsUnitTypes.RenderMillimeters", lambda: __import__("qgis.core", fromlist=["QgsUnitTypes"]).QgsUnitTypes.RenderMillimeters)
check("Qgis.RenderUnit.Millimeters", lambda: Qgis.RenderUnit.Millimeters)
check("int(enum)", lambda: int(Qgis.RenderUnit.Millimeters))
check("QgsWkbTypes.PolygonGeometry", lambda: __import__("qgis.core", fromlist=["QgsWkbTypes"]).QgsWkbTypes.PolygonGeometry)
# Few annotations (at most 10 a step), each a few KB at most.
for start in range(0, len(out), 8):
    chunk = "\n".join(out[start:start + 8])
    print("::notice title=qt6 probe::" + chunk.replace("%", "%25").replace("\n", "%0A"))
