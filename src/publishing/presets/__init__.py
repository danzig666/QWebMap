"""
Configuration presets (extension point).

A preset fills publication settings from conventions of a domain, e.g. the
layer and field names of a national zoning plan. Every module in this
package that defines ``PRESET_ID``, ``TITLE`` and ``apply(project, profile)
-> List[str]`` (notes for the user) is offered in the Publish window.

A preset module may also define ``DEFAULT_LOCALE`` (e.g. "hu"): the viewer
language of new settings in that edition (default_locale; else English).

The generic plugin ships none. Country- or office-specific variants add
modules here (only new files), so they merge with the generic code
without conflicts (see docs/BRANCHES.md).
"""

import importlib
import pkgutil
from typing import List


def available() -> List[object]:
    """Preset modules found in this package, by title."""
    found = []
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{info.name}")
        if all(hasattr(module, name) for name in ("PRESET_ID", "TITLE", "apply")):
            found.append(module)
    return sorted(found, key=lambda module: module.TITLE)


def default_locale() -> str:
    """The viewer language of new settings: a preset's DEFAULT_LOCALE, else "en"."""
    try:
        for module in available():
            locale = getattr(module, "DEFAULT_LOCALE", None)
            if locale:
                return locale
    except Exception:  # noqa: BLE001 - a broken preset must not break new settings
        pass
    return "en"
