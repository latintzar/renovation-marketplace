"""brand.themes.warm_drift — evening golden hour voice.

Seven slots:

- narrative: ``DESIGN.md``
- palette: ``brand.tokens.THEMES["warm_drift"]``
- gradients: :data:`GRADIENTS` (via :mod:`.gradients`)
- illustration: :data:`ILLUSTRATION_STYLE` (via :mod:`.illustration_style`)
- translucency: ``"vellum"``
- motion: ``"quiet"``
- typography: ``"default"``

Naming: the Python module and ``tokens.py`` ``THEMES`` key are
``warm_drift`` (underscore, matching the existing ``"dark"`` pattern).
HTML usage: ``<html data-theme="warm_drift">`` — the attribute value
is emitted literally by ``brand.build``.
"""

from __future__ import annotations

from brand.themes.warm_drift.gradients import OVERRIDES as GRADIENT_OVERRIDES
from brand.themes.warm_drift.gradients import PALETTES as GRADIENTS
from brand.themes.warm_drift.illustration_style import DEFAULT as ILLUSTRATION_STYLE

NAME: str = "warm_drift"

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
