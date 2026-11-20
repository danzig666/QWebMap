"""
The project's coordinate reference system, for the viewer's coordinate
readout: its id, name and PROJ definition (public, not sensitive). The
viewer shows coordinates in this CRS (EOV with its own transformation, any
other projected CRS through proj4js) next to WGS 84.
"""

import re
from typing import Optional

# Grid files of a datum shift (+nadgrids=C:/grids/x.gsb): the visitor's
# proj4js has none of them, and a local path must not be published. PROJ
# may quote a value with a space ("C:/Program Files/x.gsb").
_GRID_PARAM = re.compile(r'\+(nadgrids|geoidgrids|grids)=("[^"]*"|\S+)')


def public_proj(proj: str) -> str:
    """``proj`` with grid files named, not located, and optional (``@``):
    proj4js skips a missing optional grid (an approximate readout)."""
    def grid(item: str) -> str:
        name = re.split(r"[\\/]", item.lstrip("@"))[-1]
        return item if name == item.lstrip("@") and ":" not in name else f"@{name}"

    def param(m) -> str:
        value = m.group(2)
        quoted = value[:1] == '"'
        value = ",".join(grid(i) for i in (value[1:-1] if quoted else value).split(","))
        return f'+{m.group(1)}="{value}"' if quoted and re.search(r"\s", value) else f"+{m.group(1)}={value}"

    return _GRID_PARAM.sub(param, proj or "")


def project_crs_info(project) -> Optional[dict]:
    """``{"authid", "name", "proj", "geographic", "units"}`` of the project CRS,
    or ``None`` when it is not valid."""
    from qgis.core import QgsUnitTypes  # pylint: disable=import-outside-toplevel
    crs = project.crs()
    if crs is None or not crs.isValid():
        return None
    proj = ""
    try:
        proj = crs.toProj()
    except (AttributeError, RuntimeError):
        proj = ""
    try:
        units = QgsUnitTypes.toAbbreviatedString(crs.mapUnits())
    except (AttributeError, RuntimeError, TypeError):
        units = ""
    return {"authid": crs.authid() or "", "name": crs.description() or crs.authid() or "",
            "proj": public_proj(proj), "geographic": bool(crs.isGeographic()), "units": units or ""}
