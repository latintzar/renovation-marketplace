"""brand.translucency — glass recipes, named.

One canonical style today (``vellum``). Themes reference by name via
``TRANSLUCENCY = "vellum"`` in their ``__init__.py``. See ``DESIGN.md``
for the catalog rules.

>>> from brand.translucency import get, STYLES
>>> STYLES["vellum"].backdrop_blur
'blur(7px)'
>>> get("vellum").to_css(".brand-glass--vellum")[:40]
'.brand-glass--vellum {\\n  -webkit-backdrop'
"""

from __future__ import annotations

from typing import Dict

from brand.translucency.vellum import VELLUM, TranslucencyStyle

STYLES: Dict[str, TranslucencyStyle] = {
    "vellum": VELLUM,
}


def get(name: str) -> TranslucencyStyle:
    """Look up a translucency style by name. Raises ``KeyError`` on miss."""
    if name not in STYLES:
        raise KeyError(
            f"unknown translucency style: {name!r}. "
            f"known: {sorted(STYLES)}"
        )
    return STYLES[name]


def names() -> list[str]:
    """Return the sorted list of registered style names."""
    return sorted(STYLES)


__all__ = ["TranslucencyStyle", "VELLUM", "STYLES", "get", "names"]
