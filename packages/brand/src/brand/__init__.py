"""Leo brand — single source of truth for visual identity.

Canonical sources live in this package:

- :mod:`brand.tokens` — hard-contract design tokens + THEMES palette overrides
  (colours, radii, shadows, fonts).
- :mod:`brand.themes` — seven-slot aesthetic bundles (``default``, ``dark``,
  ``warm_drift``); see :doc:`themes/DESIGN.md <themes/DESIGN>`.
- :mod:`brand.translucency` — named glass recipes (``vellum`` is canonical).
- :mod:`brand.motion` — full motion system (``quiet`` is the default).
- :mod:`brand.typography` — named font recipes.
- :mod:`brand.illustrations` — theme-aware pencil illustration generator
  (fully wired, two lanes: Claude-SVG + LiteLLM-raster).
- ``brand/effects.css`` — canonical CSS effects (vellum, shimmer, bleed).
- ``brand/fluid-gradient.js`` — canonical WebGL gradient runtime.
- ``brand/assets/leo-*.svg`` — canonical logo paths.

Every derived TS/CSS surface is regenerated via :mod:`brand.build`. Read
``packages/brand/DESIGN.md`` for the narrative layer (what the brand *is*,
why the constraints exist, how to add a theme).

Usage::

    from brand import COLORS, RADIUS, SHADOWS, FONTS, THEMES
    from brand import FAVICON_SVG, FONTS_URL, LOGO_URLS, BRAND
    from brand import illustrations, translucency, motion, typography, themes

    png = illustrations.generate(theme="default", scene="a kitchen notebook", lane="raster")
    vellum_css = translucency.get("vellum").to_css(".brand-glass--vellum")
    quiet_css = motion.get("quiet").to_css()
    default_ty = typography.get("default").to_css()
"""

from __future__ import annotations

from brand import illustrations, motion, themes, translucency, typography
from brand.tokens import (
    BRAND,
    COLORS,
    FAVICON_SVG,
    FONTS,
    FONTS_URL,
    LOGO_URLS,
    RADIUS,
    SHADOWS,
    THEMES,
)

__all__ = [
    "BRAND",
    "COLORS",
    "FAVICON_SVG",
    "FONTS",
    "FONTS_URL",
    "LOGO_URLS",
    "RADIUS",
    "SHADOWS",
    "THEMES",
    "illustrations",
    "themes",
    "translucency",
    "motion",
    "typography",
]
