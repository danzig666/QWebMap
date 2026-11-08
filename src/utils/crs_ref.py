"""
crs_ref.py

A CRS as a string the export can pass around: in QGIS expressions
(``transform(@geometry, 'EPSG:3857', '<ref>')``), to
``QgsCoordinateReferenceSystem(<ref>)`` and as a cache key.

``authid()`` is that string for most CRSs, but it is empty for a CRS
without an authority code: a .prj QGIS cannot match ("Unknown CRS"), a
custom CRS made in a project and never saved as a user CRS. With the
empty string the export silently skipped every "in the layer CRS" step
(``$area``, ``$x``, geometry generator distances, map-unit offsets were
evaluated in Web Mercator). Such a CRS is referred to by its WKT (QGIS
3.44+ reads a WKT in expressions), or by its PROJ string.
"""

from typing import Optional

from qgis.core import Qgis, QgsCoordinateReferenceSystem

_CACHE = {}


def _wkt(crs) -> str:
    variant = getattr(getattr(Qgis, "CrsWktVariant", None), "Preferred", None)
    if variant is None:  # (older names)
        variant = QgsCoordinateReferenceSystem.WKT_PREFERRED
    try:
        return crs.toWkt(variant)
    except (AttributeError, TypeError):
        return crs.toWkt()


def crs_ref(crs: Optional[QgsCoordinateReferenceSystem]) -> str:
    """``crs.authid()``, or (no authority code) a WKT or ``PROJ:`` string
    that reads back as the same CRS; "" for no or an invalid CRS. Never
    holds a single quote (it goes into expression string literals)."""
    if crs is None or not crs.isValid():
        return ""
    authid = crs.authid()
    if authid:
        return authid
    wkt = _wkt(crs)
    if wkt in _CACHE:
        return _CACHE[wkt]
    candidates = [wkt]
    proj = crs.toProj()
    if proj:
        candidates.append(f"PROJ:{proj}")
    usable = [ref for ref in candidates if ref and "'" not in ref]
    ref = next((r for r in usable if QgsCoordinateReferenceSystem(r) == crs), usable[0] if usable else "")
    _CACHE[wkt] = ref
    return ref
