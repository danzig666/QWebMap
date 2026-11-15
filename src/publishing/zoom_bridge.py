"""No blank map between zoom levels in the published viewer."""

import json
import math
from typing import Optional

# Paint properties that make a style layer's features visible, per type.
_OPACITY = {"fill": ("fill-opacity",), "line": ("line-opacity",),
            "circle": ("circle-opacity", "circle-stroke-opacity"),
            "symbol": ("text-opacity", "icon-opacity"),
            "fill-extrusion": ("fill-extrusion-opacity",)}
# Symbol layers placed by the viewer itself, animated frames (their opacity
# is the animation's): left as they are.
_OWN_DRAWING = ("q2vt:visible-polygons", "q2vt:frame")


def bridge_zoom_bands(style: dict) -> dict:
    """Widen a data layer's zoom range by one zoom where the tiles of that
    zoom hold its data, so the map does not go blank between zooms.

    While the next zoom's tiles load, MapLibre draws the tiles it has in their
    place (512 px tiles: the tiles of zoom floor(map zoom)), parsed with the
    layers of their own zoom. Each dataset is written into the tiles of its
    zoom range (``q2vt:tiles``, see core.fidelity.zoom.note_tile_zooms):

    * a layer ending where the next rule starts keeps drawing for one zoom
      more from the tiles it has (its data is not in the new zoom's tiles);
    * a layer starting at zoom N draws from the tiles of zoom N-1 when they
      hold its data: a layer that first appears at N (buildings, parcels)
      has stand-in data there (core.fidelity.zoom.stand_in_zooms). It is
      parsed from them (minzoom N-1) but invisible below N (its opacities
      stepped at N), and its labels never take room there
      (*-ignore-placement in the N-1 tiles). See ``stand_in``.

    Never twice, never at a zoom whose tiles hold its data otherwise (shared
    datasets, fractional scale limits, the last zoom's enlarged tiles keep
    their range). The range it draws its own data in stays in
    ``q2vt:zooms`` (the viewer's layer list); ``q2vt:hidden-below`` marks
    the zoom below which it is invisible (the viewer's clicks and legend)."""
    archive_max_zoom = (style.get("metadata") or {}).get("q2vt:tiles-max-zoom")
    if archive_max_zoom is None:
        return style
    for layer_def in style.get("layers", []):
        tiles = (layer_def.get("metadata") or {}).get("q2vt:tiles")
        if not tiles:
            continue
        low, high = tiles
        start, end = layer_def.get("minzoom"), layer_def.get("maxzoom")
        drawn = [start, end]
        # [start - 1, start) parses the tiles of zoom floor(start) - 1.
        if start is not None and start >= 1 and math.floor(start) - 1 >= low:
            stand_in(layer_def, start)
        # [end, end + 1) shows the tiles of zooms from floor(end) (beyond the
        # archive's last zoom: its tiles, enlarged).
        if end is not None and end + 1 <= 24 and min(math.floor(end), archive_max_zoom) > high:
            layer_def["maxzoom"] = end + 1
        if [layer_def.get("minzoom"), layer_def.get("maxzoom")] != drawn:
            layer_def["metadata"]["q2vt:zooms"] = drawn
    return style


def stand_in(layer_def: dict, start: float) -> bool:
    """Parse ``layer_def`` from the tiles of zoom floor(start) - 1 too, drawn
    only from ``start`` on (False: its opacity or placement already varies
    with the zoom in a way that cannot be stepped; left as it is)."""
    kind = layer_def.get("type")
    if kind not in _OPACITY or any(k in (layer_def.get("metadata") or {}) for k in _OWN_DRAWING):
        return False
    paint = dict(layer_def.get("paint") or {})
    for prop in _OPACITY[kind]:
        stepped = _hidden_below(paint.get(prop, 1), start)
        if stepped is None:
            return False
        paint[prop] = stepped
    layout = dict(layer_def.get("layout") or {})
    if kind == "symbol":
        # Layout is evaluated at the tile's zoom: in the stand-in tiles the
        # invisible labels and icons never keep others from their places.
        own = math.floor(start)
        for prop in ("text-ignore-placement", "icon-ignore-placement"):
            value = layout.get(prop, False)
            if value is True:
                continue
            if not isinstance(value, bool):
                return False
            layout[prop] = ["step", ["zoom"], True, own, value]
    layer_def["paint"] = paint
    if layout:
        layer_def["layout"] = layout
    layer_def["minzoom"] = math.floor(start) - 1
    layer_def.setdefault("metadata", {})["q2vt:hidden-below"] = start
    return True


def _uses_zoom(value) -> bool:
    return '"zoom"' in json.dumps(value)


def _hidden_below(value, start: float) -> Optional[list]:
    """``value`` (an opacity) as 0 below ``start``, unchanged from it on;
    None when that cannot be written (legacy functions, zoom curves with
    data-driven outputs that would have to be blended)."""
    if isinstance(value, dict):
        return None
    if not _uses_zoom(value):
        return ["step", ["zoom"], 0, start, value]
    if not isinstance(value, list) or len(value) < 3 or value[0] not in ("step", "interpolate"):
        return None
    if value[0] == "step":
        if value[1] != ["zoom"] or len(value) % 2 == 0:
            return None
        current, rest = value[2], []
        for index in range(3, len(value), 2):
            if value[index] <= start:
                current = value[index + 1]
            else:
                rest += [value[index], value[index + 1]]
        if _uses_zoom(current) or any(_uses_zoom(v) for v in rest[1::2]):
            return None
        return ["step", ["zoom"], 0, start, current, *rest]
    kind, input_ = value[1], value[2]
    stops = list(zip(value[3::2], value[4::2]))
    if input_ != ["zoom"] or not stops or any(_uses_zoom(v) for _, v in stops):
        return None
    at = _value_at(kind, stops, start)
    if at is None:
        return None
    before = start - 1e-3
    kept = [(z, v) for z, v in stops if z > start]
    return ["interpolate", kind, ["zoom"], before, 0, start, at, *[x for stop in kept for x in stop]]


def _value_at(kind, stops, zoom: float):
    """The curve's output at ``zoom`` (numbers: linear or exponential; one
    stop's output where it is reached exactly or clamped)."""
    if zoom <= stops[0][0]:
        return stops[0][1]
    if zoom >= stops[-1][0]:
        return stops[-1][1]
    for (z0, v0), (z1, v1) in zip(stops, stops[1:]):
        if z0 <= zoom <= z1:
            if zoom == z0:
                return v0
            if zoom == z1:
                return v1
            if not all(isinstance(v, (int, float)) for v in (v0, v1)) or kind[0] not in ("linear", "exponential"):
                return None
            t = (zoom - z0) / (z1 - z0)
            if kind and kind[0] == "exponential" and kind[1] != 1:
                base = kind[1]
                t = (base ** (zoom - z0) - 1) / (base ** (z1 - z0) - 1)
            return v0 + (v1 - v0) * t
    return None
