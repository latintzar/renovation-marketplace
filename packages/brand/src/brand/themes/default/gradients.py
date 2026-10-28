"""Default theme — gradient palette picks.

References palettes already declared on ``window.LeoFluidGradientPalettes``
in :mod:`brand.fluid-gradient.js`. A theme declares which palettes it
endorses (+ optional per-theme overrides). The playground / brand-book
iterates :data:`PALETTES` to render side-by-side previews.

See [../DESIGN.md](../DESIGN.md) for the theme graduation path.
"""

from __future__ import annotations

from typing import Dict, Tuple

PALETTES: Tuple[str, ...] = (
    "brendan",
    "terraCharcoal",
    "blueWhite",
)
"""Palette keys the default theme endorses (defined in fluid-gradient.js)."""

OVERRIDES: Dict[str, Dict[str, float]] = {}
"""Per-palette motion-physics overrides for this theme. Empty = use runtime defaults."""


__all__ = ["PALETTES", "OVERRIDES"]
