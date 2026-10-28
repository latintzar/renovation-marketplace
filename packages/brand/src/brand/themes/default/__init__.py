"""brand.themes.default — the quiet-trust Leo voice.

The default theme *is* the cream-paper look; there's no ``THEMES``
entry for it in :mod:`brand.tokens` — colours come from the root
``COLORS`` dict. Narrative + illustrations + gradients live here.

Seven slots:

- narrative: ``DESIGN.md``
- palette: ``brand.tokens.COLORS`` (no override)
- gradients: :data:`GRADIENTS` (via :mod:`.gradients`)
- illustration: :data:`ILLUSTRATION_STYLE` (via :mod:`.illustration_style`)
- translucency: ``"vellum"``
- motion: ``"quiet"``
- typography: ``"default"``
"""

from __future__ import annotations

from brand.themes.default.gradients import OVERRIDES as GRADIENT_OVERRIDES
from brand.themes.default.gradients import PALETTES as GRADIENTS
from brand.themes.default.illustration_style import DEFAULT as ILLUSTRATION_STYLE

NAME: str = "default"

TRANSLUCENCY: str = "vellum"
MOTION: str = "quiet"
TYPOGRAPHY: str = "default"


__all__ = [
    "NAME",
    "TRANSLUCENCY",
    "MOTION",
    "TYPOGRAPHY",
    "GRADIENTS",
    "GRADIENT_OVERRIDES",
    "ILLUSTRATION_STYLE",
]
