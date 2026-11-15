"""
html_labels.py

QGIS labels with "Allow HTML formatting" as MapLibre ``format`` sections.

QGIS renders a subset of HTML in label text (``QgsTextDocument``). MapLibre
has no markup, but its ``format`` expression draws consecutive text sections
each with its own scale, colour and font. The exporter splits each label into
runs of equal formatting and stores them as fields (text, font scale, colour,
font), and the style lists them:

    ["format", ["get", "q2vt_label_h0"], {"font-scale": ..., "text-color": ...,
                                          "text-font": ...}, ...]

Handled, as QGIS draws them:

* sizes: ``<sub>``/``<sup>`` (2/3 size), ``<small>`` / ``<big>`` (Qt's next
  size), ``font-size`` in pt or px (absolute: relative to the label's size);
  a closing tag ends the innermost size change, as Qt does for mismatched
  tags (``<sub>..</small>``);
* colours: ``color`` in a style, ``<font color>`` (CSS colour names, #rgb,
  #rrggbb, Qt's #aarrggbb, rgb()/rgba());
* fonts: ``<b>``/``<strong>``, ``<i>``/``<em>``, ``font-weight``,
  ``font-style``, ``font-family`` / ``<font face>`` (the first family);
* ``<br>`` and the end of a ``<p>``/``<div>`` as line breaks, character
  entities.

Not drawn: background colours of a run (``background-color``, ``bgcolor``:
QGIS draws a box behind that run) - reported as approximated through a flag
field; underline and strike-out; other tags keep their text.

The parser is our own (not ``QgsTextDocument``): QGIS 3.34 and 4 report
``<small>``, ``<big>``, line breaks and backgrounds differently, and the
runs must be the same in a worker process and in tests without QGIS.
"""

import functools
import html
import re
from typing import Dict, List, NamedTuple, Optional, Tuple

from . import expressions as ex

MAX_SECTIONS = 16
TEXT_FIELD = "q2vt_label_h{}"
SCALE_FIELD = "q2vt_label_s{}"
COLOR_FIELD = "q2vt_label_c{}"
FONT_FIELD = "q2vt_label_f{}"
# Per label: 1 = a run has a background colour (not drawn), 2 = more runs
# than MAX_SECTIONS (the last section keeps the rest of the text).
FLAGS_FIELD = "q2vt_label_hf"
FLAG_BACKGROUND, FLAG_TRUNCATED = 1, 2

# QgsTextRenderer::SUPERSCRIPT_SUBSCRIPT_FONT_SIZE_SCALING_FACTOR
SUB_SUP_SCALE = 2.0 / 3.0
# Qt HTML sizes: <small> one step below the default (10 pt vs 12 pt).
SMALL_SCALE = 10.0 / 12.0
BIG_SCALE = 14.0 / 12.0
_SCALES = {"sub": SUB_SUP_SCALE, "sup": SUB_SUP_SCALE, "small": SMALL_SCALE, "big": BIG_SCALE}
_TAG = re.compile(r"<\s*(/?)\s*([a-zA-Z0-9]+)([^>]*?)(/?)\s*>")
_ATTR = re.compile(r"""([a-zA-Z-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""")
_VOID = {"br", "img", "hr", "meta", "input", "wbr"}


class Run(NamedTuple):
    """A piece of label text of one formatting. ``font``: "family|b|i" of
    what differs from the label's font ("" each part not changed: family,
    bold "1"/"0", italic "1"/"0"), "" when nothing does."""
    text: str
    scale: float = 1.0
    color: str = ""
    font: str = ""
    background: bool = False


def _style(declarations: str) -> Dict[str, str]:
    out = {}
    for part in declarations.split(";"):
        if ":" in part:
            name, value = part.split(":", 1)
            out[name.strip().lower()] = value.strip()
    return out


def css_color(value: str) -> str:
    """A colour as MapLibre reads it (CSS); Qt's #AARRGGBB as rgba()."""
    value = (value or "").strip().strip("'\"").lower()
    if re.fullmatch(r"#[0-9a-f]{8}", value):
        alpha, red, green, blue = (int(value[i:i + 2], 16) for i in (1, 3, 5, 7))
        return f"rgba({red}, {green}, {blue}, {round(alpha / 255, 3)})"
    return value


def _frame(name: str, attributes: str) -> dict:
    """What an opening tag sets."""
    frame: dict = {"tag": name}
    if name in _SCALES:
        frame["scale"] = _SCALES[name]
    if name in ("b", "strong"):
        frame["bold"] = True
    if name in ("i", "em"):
        frame["italic"] = True
    attrs = {}
    for match in _ATTR.finditer(attributes or ""):
        attrs[match.group(1).lower()] = next(v for v in match.groups()[1:] if v is not None)
    if name == "font":
        if attrs.get("color"):
            frame["color"] = css_color(attrs["color"])
        if attrs.get("face"):
            frame["family"] = attrs["face"].split(",")[0].strip().strip("'\"")
    if attrs.get("bgcolor"):
        frame["background"] = True
    style = _style(attrs.get("style", ""))
    if style.get("color"):
        frame["color"] = css_color(style["color"])
    weight = style.get("font-weight", "").lower()
    if weight:
        if weight in ("bold", "bolder"):
            frame["bold"] = True
        elif weight in ("normal", "lighter"):
            frame["bold"] = False
        elif weight.isdigit():
            frame["bold"] = int(weight) >= 600
    slant = style.get("font-style", "").lower()
    if slant:
        frame["italic"] = slant in ("italic", "oblique")
    if style.get("font-family"):
        frame["family"] = style["font-family"].split(",")[0].strip().strip("'\"")
    size = re.fullmatch(r"([0-9.]+)\s*(pt|px)", style.get("font-size", "").lower())
    if size:
        try:
            points = float(size.group(1)) * (0.75 if size.group(2) == "px" else 1.0)
            if points > 0:
                frame["points"] = points
        except ValueError:
            pass
    if style.get("background-color") or style.get("background"):
        background = (style.get("background-color") or style.get("background")).lower()
        frame["background"] = background not in ("transparent", "none", "")
    return frame


def _current(stack: List[dict], base_points: Optional[float]) -> Tuple[float, str, str, bool]:
    scale, points, color, family, bold, italic, background = 1.0, None, "", "", None, None, False
    for frame in stack:
        scale *= frame.get("scale", 1.0)
        points = frame.get("points", points)
        color = frame.get("color", color)
        family = frame.get("family", family)
        bold = frame.get("bold", bold)
        italic = frame.get("italic", italic)
        background = background or frame.get("background", False)
    if points and base_points:
        scale *= points / base_points
    flag = {None: "", True: "1", False: "0"}
    font = f"{family}|{flag[bold]}|{flag[italic]}"
    return round(scale, 4), color, "" if font == "||" else font, background


@functools.lru_cache(maxsize=4096)
def _parse(text: str, base_points: Optional[float]) -> Tuple[Tuple[Run, ...], int]:
    runs: List[Run] = []
    stack: List[dict] = []

    def add(chunk):
        if not chunk:
            return
        chunk = html.unescape(chunk)
        scale, color, font, background = _current(stack, base_points)
        if runs and runs[-1][1:] == (scale, color, font, background):
            runs[-1] = runs[-1]._replace(text=runs[-1].text + chunk)
        else:
            runs.append(Run(chunk, scale, color, font, background))

    position = 0
    for match in _TAG.finditer(text):
        add(text[position:match.start()])
        position = match.end()
        closing, name = match.group(1), match.group(2).lower()
        self_closing = bool(match.group(4))
        if name == "br":
            add("\n")
            continue
        if closing:
            index = next((i for i in range(len(stack) - 1, -1, -1) if stack[i]["tag"] == name), None)
            if index is None and name in _SCALES:  # Qt: the innermost size change ends
                index = next((i for i in range(len(stack) - 1, -1, -1) if "scale" in stack[i]), None)
            if index is not None:
                del stack[index]
            if name in ("p", "div") and runs:
                add("\n")
            continue
        if self_closing or name in _VOID:
            continue
        stack.append(_frame(name, match.group(3)))
    add(text[position:])
    flags = FLAG_BACKGROUND if any(r.background for r in runs) else 0
    if len(runs) > MAX_SECTIONS:  # the rest keeps the last section's formatting
        head, tail = runs[:MAX_SECTIONS - 1], runs[MAX_SECTIONS - 1:]
        runs = head + [tail[0]._replace(text="".join(r.text for r in tail))]
        flags |= FLAG_TRUNCATED
    return tuple(runs), flags


def html_runs(text, base_points: Optional[float] = None) -> List[Run]:
    """The runs of an HTML label (``base_points``: the label's size in
    points, for absolute ``font-size`` values)."""
    if text is None:
        return []
    return list(_parse(str(text), float(base_points) if base_points else None)[0])


def html_flags(text, base_points: Optional[float] = None) -> int:
    if text is None:
        return 0
    return _parse(str(text), float(base_points) if base_points else None)[1]


def html_sections(text) -> List[Tuple[str, float]]:
    """``[(text, scale)]`` of an HTML label, consecutive equal scales merged."""
    sections: List[Tuple[str, float]] = []
    for run in html_runs(text):
        if sections and sections[-1][1] == run.scale:
            sections[-1] = (sections[-1][0] + run.text, run.scale)
        else:
            sections.append((run.text, run.scale))
    return sections


def plain_text(text) -> str:
    """The text of an HTML label without its markup (its runs' text; a line
    break as a new line)."""
    return "".join(run.text for run in html_runs(text))


def _run(text, index: int, base_points=None) -> Optional[Run]:
    runs = html_runs(text, base_points)
    return runs[index] if index < len(runs) else None


def section_text(text, index: int) -> Optional[str]:
    """None after the last run (a NULL field: not written into the tiles)."""
    run = _run(text, index)
    return run.text if run else None


def section_scale(text, index: int, base_points=None) -> Optional[float]:
    """None: the label's size (1)."""
    run = _run(text, index, base_points)
    return run.scale if run and run.scale != 1.0 else None


def section_color(text, index: int) -> Optional[str]:
    run = _run(text, index)
    return (run.color or None) if run else None


def section_font(text, index: int) -> Optional[str]:
    run = _run(text, index)
    return (run.font or None) if run else None


def font_key_parts(key: str) -> Tuple[str, Optional[bool], Optional[bool]]:
    """(family or "", bold or None, italic or None) of a run's font key."""
    family, bold, italic = (str(key or "").split("|") + ["", "", ""])[:3]
    flag = {"1": True, "0": False}
    return family, flag.get(bold), flag.get(italic)


def format_expression(color=None, fonts: Optional[list] = None) -> list:
    """MapLibre ``text-field`` drawing the stored sections. ``color``: the
    label's ``text-color`` (a section without its own colour); ``fonts``:
    ``text-font`` per run font key (a ``match`` on the section's font field
    is built from it), None: the label's font for every section."""
    expression: list = ["format"]
    for index in range(MAX_SECTIONS):
        options: dict = {"font-scale": ex.to_number(["get", SCALE_FIELD.format(index)], 1)}
        if color is not None:
            options["text-color"] = ["to-color", ["get", COLOR_FIELD.format(index)], color]
        if fonts:
            options["text-font"] = ["match", ["coalesce", ["get", FONT_FIELD.format(index)], ""],
                                    *fonts[:-1], fonts[-1]]
        expression += [["coalesce", ["get", TEXT_FIELD.format(index)], ""], options]
    return expression


def register_expression_functions() -> None:
    """``q2vt_html_text/scale/color/font(text, i)`` and
    ``q2vt_html_flags(text)`` for the exporter's field calculation
    (idempotent)."""
    from qgis.core import QgsExpression  # pylint: disable=import-outside-toplevel
    from qgis.core import qgsfunction  # pylint: disable=import-outside-toplevel

    if QgsExpression.isFunctionName("q2vt_html_color"):
        return
    for name in ("q2vt_html_text", "q2vt_html_scale"):  # an older registration
        if QgsExpression.isFunctionName(name):
            QgsExpression.unregisterFunction(name)

    # The legacy ``args=2`` form crashes QGIS 3.34; arguments come evaluated.
    @qgsfunction(group="Custom", referenced_columns=[])
    def q2vt_html_text(text, index):
        return section_text(text, int(index))

    @qgsfunction(group="Custom", referenced_columns=[])
    def q2vt_html_scale(text, index, base_points):
        return section_scale(text, int(index), base_points)

    @qgsfunction(group="Custom", referenced_columns=[])
    def q2vt_html_color(text, index):
        return section_color(text, int(index))

    @qgsfunction(group="Custom", referenced_columns=[])
    def q2vt_html_font(text, index):
        return section_font(text, int(index))

    @qgsfunction(group="Custom", referenced_columns=[])
    def q2vt_html_flags(text):
        return html_flags(text) or None

    # QGIS keeps only a pointer: without a reference the functions are
    # garbage collected and the next evaluation crashes.
    _REGISTERED.extend([q2vt_html_text, q2vt_html_scale, q2vt_html_color, q2vt_html_font,
                        q2vt_html_flags])


_REGISTERED: list = []
