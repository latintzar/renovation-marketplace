"""brand.motion — movement recipes, named.

One style today (``quiet``). Themes reference by name:
``MOTION = "quiet"`` in the theme's ``__init__.py``. See ``DESIGN.md``
for the catalog rules and how to add new recipes.

>>> from brand.motion import get
>>> get("quiet").durations.fast
120
"""

from __future__ import annotations

from typing import Dict

from brand.motion.quiet import (
    QUIET,
    Durations,
    Eases,
    Entrances,
    MotionStyle,
    Scroll,
    Springs,
    Staggers,
)

STYLES: Dict[str, MotionStyle] = {
    "quiet": QUIET,
}


def get(name: str) -> MotionStyle:
    """Look up a motion style by name. Raises ``KeyError`` on miss."""
    if name not in STYLES:
        raise KeyError(
            f"unknown motion style: {name!r}. known: {sorted(STYLES)}"
        )
    return STYLES[name]


def names() -> list[str]:
    """Return the sorted list of registered motion names."""
    return sorted(STYLES)


__all__ = [
    "Durations",
    "Eases",
    "Springs",
    "Entrances",
    "Staggers",
    "Scroll",
    "MotionStyle",
    "QUIET",
    "STYLES",
    "get",
    "names",
]
