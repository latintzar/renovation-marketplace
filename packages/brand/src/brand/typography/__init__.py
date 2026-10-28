"""brand.typography — font recipes, named.

Today: one style (``default``) that re-exports ``FONTS`` from
:mod:`brand.tokens`. Themes inherit by declaring
``TYPOGRAPHY = "default"`` in their ``__init__.py``.

>>> from brand.typography import get
>>> get("default").display
"'Playfair Display', Georgia, serif"
"""

from __future__ import annotations

from typing import Dict

from brand.typography.default import DEFAULT, TypographyStyle

STYLES: Dict[str, TypographyStyle] = {
    "default": DEFAULT,
}


def get(name: str) -> TypographyStyle:
    """Look up a typography style by name. Raises ``KeyError`` on miss."""
    if name not in STYLES:
        raise KeyError(
            f"unknown typography style: {name!r}. known: {sorted(STYLES)}"
        )
    return STYLES[name]


def names() -> list[str]:
    """Return the sorted list of registered typography names."""
    return sorted(STYLES)


__all__ = ["TypographyStyle", "DEFAULT", "STYLES", "get", "names"]
