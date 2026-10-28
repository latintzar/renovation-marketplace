"""brand.themes.dark — late-hours Leo.

Seven slots:

- narrative: ``DESIGN.md``
- palette: ``brand.tokens.THEMES["dark"]``
- gradients: :data:`GRADIENTS` (via :mod:`.gradients`)
- illustration: :data:`ILLUSTRATION_STYLE` (via :mod:`.illustration_style`)
- translucency: ``"vellum"``
- motion: ``"quiet"``
- typography: ``"default"``
"""

from __future__ import annotations

from brand.themes.dark.gradients import OVERRIDES as GRADIENT_OVERRIDES
from brand.themes.dark.gradients import PALETTES as GRADIENTS
from brand.themes.dark.illustration_style import DEFAULT as ILLUSTRATION_STYLE

NAME: str = "dark"

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
