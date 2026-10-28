"""Dark theme — gradient palette picks.

Inherits the same runtime palettes declared in
:mod:`brand.fluid-gradient.js`; in low-light surfaces the
terra-charcoal duo reads richer than the brendan palette.

See [../DESIGN.md](../DESIGN.md) for the theme rules.
"""

from __future__ import annotations

from typing import Dict, Tuple

PALETTES: Tuple[str, ...] = (
    "terraCharcoal",
    "brendan",
)
"""Dark theme leans on terra-charcoal first."""

OVERRIDES: Dict[str, Dict[str, float]] = {}

__all__ = ["PALETTES", "OVERRIDES"]
