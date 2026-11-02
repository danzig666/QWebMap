"""Callouts of point labels drawn at their point (an idea of QGIS2VectorTiles
4.1-4.2, GallPeters/QGIS2VectorTiles; the balloon outline is ported from its
symbol_geometry._balloon, both GPL-2).

A point label with a fixed side (an anchor and an offset in screen units)
has its box at a fixed place from its point whatever its text: the point of
the box nearest the point (QGIS's default label anchor, "point on
exterior") is a corner or the middle of a side. So the callout QGIS draws
from there to the point (QgsSimpleLineCallout, QgsManhattanLineCallout,
QgsCurvedLineCallout) is the same for every feature: one image, drawn with
the label (an icon of its symbol layer, shown and hidden with it). A
balloon (QgsBalloonCallout) is the label's stretched icon: the rounded box
around the text, its wedge pointing at the point.

Coordinates: CSS pixels around the label's point, y down (the painter's).
"""

import math
from typing import List, Optional, Sequence, Tuple

Point = Tuple[float, float]

# QgsCurvedLineCallout::Orientation
AUTOMATIC, CLOCKWISE, COUNTER_CLOCKWISE = 0, 1, 2


def radial_offset(anchor: str, radius: float) -> Point:
    """MapLibre's text-offset (ems) of ``text-radial-offset`` ``radius`` for
    ``anchor`` (style-spec fromRadialOffset: corners at 45 degrees)."""
    corner = radius / math.sqrt(2)
    return {"top": (0.0, radius), "bottom": (0.0, -radius), "left": (radius, 0.0), "right": (-radius, 0.0),
            "top-left": (corner, corner), "top-right": (-corner, corner),
            "bottom-left": (corner, -corner), "bottom-right": (-corner, -corner)}.get(anchor, (0.0, 0.0))


def box_point(anchor: str, offset: Point) -> Point:
    """The point of the label's box nearest its point: the box's ``anchor``
    point sits at ``offset`` (px). A box reaching across the point's axis
    (centred on it, or its offset pointing back) has it on that axis (its
    text assumed wider than its offset)."""
    ox, oy = offset
    x = max(ox, 0.0) if "left" in anchor else min(ox, 0.0) if "right" in anchor else 0.0
    y = max(oy, 0.0) if anchor.startswith("top") else min(oy, 0.0) if anchor.startswith("bottom") else 0.0
    return x, y


# The side of the box the callout leaves from (QgsGeometryUtilsBase::
# closestSideOfRectangle: 1 bottom, 2 bottom right, 3 right, 4 top right,
# 5 top, 6 top left, 7 left, 8 bottom left), by the label's anchor.
_SIDES = {"bottom-left": 8, "bottom-right": 2, "top-left": 6, "top-right": 4,
          "bottom": 1, "top": 5, "left": 7, "right": 3}


def _automatic(anchor: str, start: Point, end: Point) -> int:
    """QgsCurvedLineCallout's automatic orientation (its createCalloutLine,
    y down). The label is centred on the start where a straight vertical /
    horizontal line decides by the box's middle."""
    side = _SIDES.get(anchor, 1)
    (sx, sy), (ex, ey) = start, end
    near = lambda a, b: abs(a - b) < 1e-9  # noqa: E731
    if side == 1:
        if near(ex, sx):
            return CLOCKWISE  # start.x() at the box's middle: not left of it
        return COUNTER_CLOCKWISE if ex > sx else CLOCKWISE
    if side == 2:
        if ex < sx:
            return CLOCKWISE
        if ey < sy:
            return COUNTER_CLOCKWISE
        return CLOCKWISE if ex - sx < ey - sy else COUNTER_CLOCKWISE
    if side == 3:
        if near(ey, sy):
            return COUNTER_CLOCKWISE
        return COUNTER_CLOCKWISE if ey < sy else CLOCKWISE
    if side == 4:
        if ex < sx:
            return COUNTER_CLOCKWISE
        if ey > sy:
            return CLOCKWISE
        return COUNTER_CLOCKWISE if ex - sx < sy - ey else CLOCKWISE
    if side == 5:
        if near(ex, sx):
            return COUNTER_CLOCKWISE
        return COUNTER_CLOCKWISE if ex < sx else CLOCKWISE
    if side == 6:
        if ex > sx:
            return CLOCKWISE
        if ey > sy:
            return COUNTER_CLOCKWISE
        return CLOCKWISE if sx - ex < sy - ey else COUNTER_CLOCKWISE
    if side == 7:
        if near(ey, sy):
            return CLOCKWISE
        return COUNTER_CLOCKWISE if ey > sy else CLOCKWISE
    if ex > sx:
        return COUNTER_CLOCKWISE
    if ey < sy:
        return CLOCKWISE
    return COUNTER_CLOCKWISE if sx - ex < ey - sy else CLOCKWISE


def _arc(start: Point, mid: Point, end: Point, segments: int = 32) -> List[Point]:
    """The circular arc through three points, as a polyline."""
    (ax, ay), (bx, by), (cx, cy) = start, mid, end
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return [start, end]
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    radius = math.hypot(ax - ux, ay - uy)
    a0, a1, am = (math.atan2(p[1] - uy, p[0] - ux) for p in (start, end, mid))

    def between(a, b, m):  # m on the way from a to b counter-clockwise (in these coordinates)
        return (m - a) % (2 * math.pi) < (b - a) % (2 * math.pi)
    sweep = (a1 - a0) % (2 * math.pi)
    if not between(a0, a1, am):
        sweep -= 2 * math.pi
    return [(ux + radius * math.cos(a0 + sweep * i / segments), uy + radius * math.sin(a0 + sweep * i / segments))
            for i in range(segments + 1)]


def callout_line(kind: str, anchor: str, start: Point, curvature: float = 0.0,
                 orientation: int = AUTOMATIC) -> List[Point]:
    """The callout from the label (``start``) to its point (0, 0): straight,
    Manhattan (up or down from the label, then across to the point) or
    curved (an arc through the middle, moved aside by ``curvature`` x the
    length, QgsCurvedLineCallout's ``curvature()`` as a fraction)."""
    end = (0.0, 0.0)
    if kind == "manhattan":
        return [start, (start[0], end[1]), end]
    if kind == "curved":
        if orientation == AUTOMATIC:
            orientation = _automatic(anchor, start, end)
        length = math.hypot(end[0] - start[0], end[1] - start[1])
        if length <= 0:
            return [start, end]
        distance = (1 if orientation == CLOCKWISE else -1) * length * curvature
        # QgsGeometryUtilsBase::perpendicularOffsetPointAlongSegment: along
        # the normal (-(y1 - y2), x1 - x2), normalised.
        dx, dy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
        mid = (start[0] + 0.5 * (end[0] - start[0]) + dy * distance,
               start[1] + 0.5 * (end[1] - start[1]) - dx * distance)
        return _arc(start, mid, end)
    return [start, end]


def length_of(points: Sequence[Point]) -> float:
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))


def substring(points: Sequence[Point], start: float, end: float) -> List[Point]:
    """The part of a polyline from ``start`` to ``end`` along it."""
    out, walked = [], 0.0
    for a, b in zip(points, points[1:]):
        step = math.hypot(b[0] - a[0], b[1] - a[1])
        if step <= 0:
            continue
        lo, hi = max(start, walked), min(end, walked + step)
        if lo <= hi:
            for t in ((lo - walked) / step, (hi - walked) / step):
                point = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
                if not out or math.hypot(point[0] - out[-1][0], point[1] - out[-1][1]) > 1e-9:
                    out.append(point)
        walked += step
    return out


def trimmed(points: Sequence[Point], from_label: float, from_anchor: float,
            minimum: float) -> Optional[List[Point]]:
    """QgsSimpleLineCallout::draw: no callout shorter than ``minimum`` (the
    straight line), then shortened by the offsets from the label and from
    the point."""
    straight = math.hypot(points[-1][0] - points[0][0], points[-1][1] - points[0][1])
    if straight <= 1e-9 or (minimum > 0 and straight < minimum):
        return None
    total = length_of(points)
    if from_label <= 0 and from_anchor <= 0:
        return list(points)
    if total - from_anchor <= from_label:
        return None
    return substring(points, from_label, total - from_anchor)


# --- balloons -----------------------------------------------------------------

def _qgis_sides(rect, r: float):
    """The sides QgsShapeGenerator::createBalloon walks, as QGIS passes the
    label's box (QgsVectorLayerLabelProvider::drawCallout: from its bottom
    left corner, a negative height): bottom (left to right), right (up),
    top (right to left), left (down); ``rect`` (left, top, right, bottom)
    on screen, y down, each inset by the corner radius."""
    left, top, right, bottom = rect
    return [((left + r, bottom), (right - r, bottom)), ((right, bottom - r), (right, top + r)),
            ((right - r, top), (left + r, top)), ((left, top + r), (left, bottom - r))]


def _closest_on(segment, p: Point) -> Point:
    (x1, y1), (x2, y2) = segment
    dx, dy = x2 - x1, y2 - y1
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((p[0] - x1) * dx + (p[1] - y1) * dy) / length2))
    return x1 + t * dx, y1 + t * dy


def balloon(origin: Point, rect, wedge_width: float, radius: float, arc_steps: int = 8) -> List[Point]:
    """QgsShapeGenerator::createBalloon: the box ``rect`` (left, top, right,
    bottom; y down) with rounded corners and a wedge ``wedge_width`` wide
    from its side nearest ``origin`` to ``origin`` (none when origin is
    inside it). A closed ring, clockwise on screen."""
    left, top, right, bottom = rect
    r = max(0.0, min(radius, min(bottom - top, right - left) / 2))
    sides = _qgis_sides(rect, r)
    wedge_side, p1, p2 = -1, None, None
    if not (left <= origin[0] <= right and top <= origin[1] <= bottom):
        best = None
        for i, seg in enumerate(sides):
            p = _closest_on(seg, origin)
            d = (p[0] - origin[0]) ** 2 + (p[1] - origin[1]) ** 2
            if best is not None and abs(d - best[0]) <= 1e-9 * max(1.0, d):
                theta = (math.degrees(math.atan2(p[0] - origin[0], p[1] - origin[1])) + 360) % 360
                prefer = ((theta < 45 or theta > 315) and i == 0) or (45 <= theta < 135 and i == 3) \
                    or (135 <= theta < 225 and i == 2) or (225 <= theta <= 315 and i == 1)
            else:
                prefer = best is None or d < best[0]
            if prefer:
                best = (d, i, p, seg)
        _, wedge_side, p1, seg = best
        (ax, ay), (bx, by) = seg
        length = math.hypot(bx - ax, by - ay)
        w = max(0.0, min(wedge_width, length))
        if math.hypot(p1[0] - bx, p1[1] - by) < w and length > 0:
            p1 = (bx + (ax - bx) / length * w, by + (ay - by) / length * w)
        to_b = (bx - p1[0], by - p1[1])
        distance = math.hypot(*to_b)
        p2 = (p1[0] + to_b[0] / distance * w, p1[1] + to_b[1] / distance * w) if distance else p1
    # Walked clockwise on screen: top, right, bottom, left (each QGIS side
    # backwards, so the wedge is p2, origin, p1).
    walk = [(2, (left + r, top), (right - r, top)), (1, (right, top + r), (right, bottom - r)),
            (0, (right - r, bottom), (left + r, bottom)), (3, (left, bottom - r), (left, top + r))]
    centres = [(right - r, top + r), (right - r, bottom - r), (left + r, bottom - r), (left + r, top + r)]
    starts = [-90.0, 0.0, 90.0, 180.0]
    ring: List[Point] = []
    for k, (qgis_index, a, b) in enumerate(walk):
        ring.append(a)
        if qgis_index == wedge_side:
            ring += [p2, origin, p1]
        ring.append(b)
        if r > 0:
            cx, cy = centres[k]
            for step in range(1, arc_steps):
                angle = math.radians(starts[k] + 90.0 * step / arc_steps)
                ring.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    ring.append(ring[0])
    return ring
