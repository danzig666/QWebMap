"""Enum values across PyQt5 (QGIS 3: enums are ints) and PyQt6 (QGIS 4:
Python enums, not equal to ints, and methods refuse plain ints).

``propertyKeys()`` of a property collection gives ints on both: a key passed
on to ``setDataDefinedProperty`` or compared with an enum member goes
through these helpers.
"""


def enum_int(value, default=None):
    """Integer value of a Qt/QGIS enum (Qt5 ints and Qt6/Python enums alike)."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        pass
    inner = getattr(value, "value", None)
    if isinstance(inner, int):
        return inner
    return default


def as_enum(enum_type, value):
    """``value`` (an int or a member) as a member of ``enum_type``."""
    if isinstance(value, enum_type):
        return value
    return enum_type(enum_int(value))


def symbol_layer_key(key):
    """A data-defined property key of a symbol layer (QgsSymbolLayer.Property)."""
    from qgis.core import QgsSymbolLayer  # pylint: disable=import-outside-toplevel
    return as_enum(QgsSymbolLayer.Property, key)


def symbol_key(key):
    """A data-defined property key of a symbol (QgsSymbol.Property)."""
    from qgis.core import QgsSymbol  # pylint: disable=import-outside-toplevel
    return as_enum(QgsSymbol.Property, key)


# Multi-part label behaviour (label_multipart_mode).
MULTIPART_LARGEST = "largest"
MULTIPART_EVERY = "every"
MULTIPART_SPLIT = "split"

# Curved label modes (curved_label_mode).
CURVED_DEFAULT = "default"
CURVED_AT_VERTICES = "vertices"
CURVED_STRETCH_CHARS = "stretch_chars"
CURVED_STRETCH_WORDS = "stretch_words"


def _label_property(settings, name):
    """(active, static value) of the data-defined label property ``name``;
    the value is None unless the property is a static value."""
    from qgis.core import QgsPalLayerSettings, QgsProperty  # pylint: disable=import-outside-toplevel
    key = getattr(QgsPalLayerSettings.Property, name, None)
    if key is None:
        return False, None
    prop = settings.dataDefinedProperties().property(key)
    if prop is None or not prop.isActive():
        return False, None
    if enum_int(prop.propertyType()) != enum_int(QgsProperty.StaticProperty):
        return True, None
    return True, prop.staticValue()


def _static_label_property(settings, name):
    """(active and static, value) of the data-defined label property
    ``name``; the value may be NULL."""
    from qgis.core import QgsPalLayerSettings, QgsProperty  # pylint: disable=import-outside-toplevel
    key = getattr(QgsPalLayerSettings.Property, name, None)
    prop = settings.dataDefinedProperties().property(key) if key is not None else None
    if prop is None or not prop.isActive() or \
            enum_int(prop.propertyType()) != enum_int(QgsProperty.StaticProperty):
        return False, None
    return True, prop.staticValue()


def label_mode_data_defined(settings, name: str) -> bool:
    """True when the data-defined label property ``name`` (LabelAllParts,
    CurvedLabelMode, WhitespaceCollisionHandling) reads a field or an
    expression: the mode then changes per feature, the export keeps one."""
    if settings is None:
        return False
    active, _ = _label_property(settings, name)
    return active and not _static_label_property(settings, name)[0]


def label_multipart_mode(settings) -> str:
    """How a label treats a multi-part feature: MULTIPART_LARGEST (the
    largest part only), MULTIPART_EVERY (the whole label on every part) or
    MULTIPART_SPLIT (the text's lines shared out over the parts, one line
    per part).

    QGIS 4 replaced ``labelPerPart`` by
    ``QgsLabelPlacementSettings::multiPartBehavior()``
    (Qgis::MultiPartLabelingBehavior); ``labelPerPart`` stays for Python as
    a lossy shim that reads SplitLabelTextLinesOverParts as False. A static
    data-defined "LabelAllParts" overrides it as QGIS reads it: on QGIS 4
    (QgsLabelPlacementSettings::updateDataDefinedProperties) a behaviour
    name first (trimmed, any case), else - as on QGIS 3
    (QgsPalLayerSettings::registerFeature) - QgsProperty::valueAsBool: the
    value's QVariant::toBool (variant_bool), a NULL value keeping "every
    part" (QGIS 4: split becomes "largest part only")."""
    if settings is None:
        return MULTIPART_LARGEST
    placement = settings.placementSettings() if hasattr(settings, "placementSettings") else None
    behaviour = None
    if placement is not None and hasattr(placement, "multiPartBehavior"):
        behaviour = enum_int(placement.multiPartBehavior())
    if behaviour is None:
        mode = MULTIPART_EVERY if settings.labelPerPart else MULTIPART_LARGEST
    else:
        mode = {1: MULTIPART_EVERY, 2: MULTIPART_SPLIT}.get(behaviour, MULTIPART_LARGEST)
    static, value = _static_label_property(settings, "LabelAllParts")
    if not static:
        return mode
    if behaviour is not None and not _is_null(value):  # QGIS 4: a behaviour name first
        named = {"largestpartonly": MULTIPART_LARGEST, "labeleverypart": MULTIPART_EVERY,
                 "splitlabeltextlinesoverparts": MULTIPART_SPLIT}.get(_variant_text(value).strip().lower())
        if named:
            return named
    every = variant_bool(value, mode == MULTIPART_EVERY)
    return MULTIPART_EVERY if every else MULTIPART_LARGEST


def _is_null(value) -> bool:
    """A NULL QVariant (None, or a null QVariant on QGIS 3)."""
    return value is None or (hasattr(value, "isNull") and not isinstance(value, str) and value.isNull())


def _variant_text(value) -> str:
    """QVariant::toString of a property value ("true" / "false" for a bool)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def variant_bool(value, default: bool) -> bool:
    """QgsProperty::valueAsBool of a static value: ``default`` for NULL,
    else QVariant::toBool - a string is false only when it is empty, "0"
    or "false" (any case, not trimmed: " false" is true), a number when it
    is 0."""
    if _is_null(value):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.lower() not in ("", "0", "false")
    return bool(value)


def curved_label_mode(settings) -> str:
    """The curved label mode of a Curved / PerimeterCurved label (QGIS 4,
    ``QgsLabelLineSettings::curvedLabelMode()``, Qgis::CurvedLabelMode):
    CURVED_DEFAULT, CURVED_AT_VERTICES (one character at each vertex),
    CURVED_STRETCH_CHARS or CURVED_STRETCH_WORDS (the character or word
    spacing stretched so the text fills the line). A static data-defined
    "CurvedLabelMode" overrides it (QgsLabelLineSettings::
    updateDataDefinedProperties). Other placements and QGIS 3: CURVED_DEFAULT."""
    if settings is None or enum_int(settings.placement) not in (3, 7):  # Curved, PerimeterCurved
        return CURVED_DEFAULT
    line_settings = settings.lineSettings()
    if not hasattr(line_settings, "curvedLabelMode"):
        return CURVED_DEFAULT
    mode = {1: CURVED_AT_VERTICES, 2: CURVED_STRETCH_CHARS, 3: CURVED_STRETCH_WORDS}.get(
        enum_int(line_settings.curvedLabelMode()), CURVED_DEFAULT)
    _, value = _label_property(settings, "CurvedLabelMode")
    if value is not None:
        mode = {"default": CURVED_DEFAULT, "charactersatvertices": CURVED_AT_VERTICES,
                "stretchcharacterspacingtofit": CURVED_STRETCH_CHARS,
                "stretchwordspacingtofit": CURVED_STRETCH_WORDS}.get(str(value).strip().lower(), mode)
    return mode


def ignores_whitespace_collisions(settings) -> bool:
    """QGIS 4 "Ignore whitespace collisions"
    (``QgsLabelPlacementSettings::whitespaceCollisionHandling()``): the
    blanks of a curved label do not collide with other labels."""
    if settings is None or not hasattr(settings, "placementSettings"):
        return False
    placement = settings.placementSettings()
    if not hasattr(placement, "whitespaceCollisionHandling"):
        return False
    ignored = enum_int(placement.whitespaceCollisionHandling()) == 1
    _, value = _label_property(settings, "WhitespaceCollisionHandling")
    if value is not None:
        ignored = {"treatwhitespaceascollision": False, "ignorewhitespacecollisions": True}.get(
            str(value).strip().lower(), ignored)
    return ignored
