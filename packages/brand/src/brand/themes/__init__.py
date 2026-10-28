"""brand.themes — seven-slot aesthetic bundles.

Each subpackage (``default``, ``dark``, ``warm_drift``, ``vitrina_sky``)
ships the seven slots defined in ``DESIGN.md``. This module offers a
uniform lookup so tools can iterate the theme set programmatically
(the playground, sessionStart hook, brand-book page).

>>> from brand.themes import get, names
>>> names()
['dark', 'default', 'vitrina_sky', 'warm_drift']
>>> theme = get("default")
>>> theme.TRANSLUCENCY, theme.MOTION, theme.TYPOGRAPHY
('vellum', 'quiet', 'default')
"""

from __future__ import annotations

import importlib
import types
from typing import Dict

_THEME_MODULES: Dict[str, str] = {
    "default": "brand.themes.default",
    "dark": "brand.themes.dark",
    "warm_drift": "brand.themes.warm_drift",
    "vitrina_sky": "brand.themes.vitrina_sky",
}


def get(name: str) -> types.ModuleType:
    """Return the theme module for *name*. Raises ``KeyError`` on miss."""
    if name not in _THEME_MODULES:
        raise KeyError(
            f"unknown theme: {name!r}. known: {sorted(_THEME_MODULES)}"
        )
    return importlib.import_module(_THEME_MODULES[name])


def names() -> list[str]:
    """Return the sorted list of registered theme names."""
    return sorted(_THEME_MODULES)


__all__ = ["get", "names"]
