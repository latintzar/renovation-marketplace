"""Warm-drift theme — gradient palette picks.

Leans on the brendan palette (the terracotta+sky+cream trio) with a
slightly slower motion preset for a more reflective feel. Inherits
palette names from :mod:`brand.fluid-gradient.js`.
"""

from __future__ import annotations

from typing import Dict, Tuple

PALETTES: Tuple[str, ...] = (
    "brendan",
    "blueWhite",
)

OVERRIDES: Dict[str, Dict[str, float]] = {
    "brendan": {
        "shapeWind": 0.8,
        "shapeSCurve": 0.4,
    },
}
"""Slightly calmer brendan: less wind, gentler curvature."""

__all__ = ["PALETTES", "OVERRIDES"]
