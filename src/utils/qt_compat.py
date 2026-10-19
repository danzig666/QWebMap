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
