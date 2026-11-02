"""Label text as QGIS writes it: its type case (QgsTextFormat
capitalization, also data-defined) applied with QGIS's own
QgsStringUtils.capitalize, and the spaces at the start and end of a line
kept (MapLibre trims them; QGIS does not, so a line's alignment moves).
Ideas of QGIS2VectorTiles 4.1 (GallPeters/QGIS2VectorTiles)."""

from typing import Optional

# Data-defined "Font case" values (QgsTextFormat::updateDataDefinedProperties).
CASE_NAMES = {"nochange": 0, "upper": 1, "lower": 2, "capitalize": 4, "smallcaps": 5,
              "title": 1004, "allsmallcaps": 1006}
# Lower-case letters drawn as small capitals: upper case (MapLibre has no
# small capitals; QGIS draws them a little smaller).
_SMALL_CAPS = (5, 1006)
WORD_JOINER = "⁠"  # not whitespace to MapLibre, no width
# Direction marks a line may start or end with (the spaces go inside them).
_MARKS = "‎‏‪-‮⁦-⁩"


def case_mode(value) -> Optional[int]:
    """A Qgis.Capitalization value from a static enum or a data-defined
    value (its number or its name); None: none given."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return CASE_NAMES.get(str(value).strip().lower())


def capitalize(text, mode):
    """``text`` in the type case ``mode`` (QgsStringUtils::capitalize)."""
    from qgis.core import Qgis, QgsStringUtils  # pylint: disable=import-outside-toplevel
    if text is None or not isinstance(text, str):
        return text
    mode = case_mode(mode)
    if not mode:
        return text
    if mode in _SMALL_CAPS:
        return text.upper()
    try:
        return QgsStringUtils.capitalize(text, Qgis.Capitalization(mode))
    except (TypeError, ValueError, AttributeError):
        return text


def edge_spaces_kept(expression: str) -> str:
    """``expression`` (a label text) with a word joiner before the spaces
    that end a line and after those that start one (past direction marks)."""
    from qgis.core import QgsExpression  # pylint: disable=import-outside-toplevel
    q = QgsExpression.quotedString
    lead = f"regexp_replace({expression}, {q('(^|' + chr(10) + ')([' + _MARKS + ']*)( +)')}, " \
           f"{q(chr(92) + '1' + chr(92) + '2' + WORD_JOINER + chr(92) + '3')})"
    return f"regexp_replace({lead}, {q('( +)([' + _MARKS + ']*)($|' + chr(10) + ')')}, " \
           f"{q(chr(92) + '1' + WORD_JOINER + chr(92) + '2' + chr(92) + '3')})"


def register_expression_functions() -> None:
    """``q2vt_capitalize(text, mode)`` for the exporter's field calculation
    (idempotent; the workers register it too)."""
    from qgis.core import QgsExpression, qgsfunction  # pylint: disable=import-outside-toplevel
    if QgsExpression.isFunctionName("q2vt_capitalize"):
        return

    @qgsfunction(group="Custom", referenced_columns=[])
    def q2vt_capitalize(text, mode):
        return capitalize(text, mode)

    _REGISTERED.append(q2vt_capitalize)  # QGIS keeps only a pointer


_REGISTERED: list = []
