"""brand.themes.vitrina_sky — baby-blue sky, white clouds, Dijon CTA.

Seven slots:

- narrative: ``DESIGN.md``
- palette: ``brand.tokens.THEMES["vitrina_sky"]`` — baby sky-blue
  primary, white cloud surfaces, Dijon honey-mustard as the main
  accent (buttons / CTAs / highlights), warm_drift terracotta held
  back as a tertiary "fun toys" accent.
- gradients: :data:`GRADIENTS` (via :mod:`.gradients`) — the
  ``vitrina_sky_clouds`` palette is the canonical animated background.
- illustration: :data:`ILLUSTRATION_STYLE` — black pencil, transparent,
  Dijon accent tint (honey-mustard hairline highlight on drawings).
- translucency: ``"vellum"``
- motion: ``"quiet"``
- typography: ``"default"`` (warm-drift serif voice)

Naming: Python module + ``tokens.py`` ``THEMES`` key are
``vitrina_sky`` (underscore). HTML: ``<html data-theme="vitrina_sky">``.
"""

from __future__ import annotations

from brand.themes.vitrina_sky.gradients import OVERRIDES as GRADIENT_OVERRIDES
from brand.themes.vitrina_sky.gradients import PALETTES as GRADIENTS
from brand.themes.vitrina_sky.illustration_style import DEFAULT as ILLUSTRATION_STYLE

NAME: str = "vitrina_sky"

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
