"""Vitrina-sky theme — gradient palette picks.

Endorses the existing ``blueWhite`` palette from
:mod:`brand.fluid-gradient.js` (baby blue → white) as the hero
"animated sky with clouds" background. Leans slower and airier than
warm_drift's brendan.
"""

from __future__ import annotations

from typing import Dict, Tuple

PALETTES: Tuple[str, ...] = (
    "blueWhite",
    "brendan",
)
"""``blueWhite`` first — it's the canonical sky-and-clouds background
for the shopper surfaces. ``brendan`` kept as a secondary palette for
warmer contexts (e.g. cozy recipe detail cards)."""

OVERRIDES: Dict[str, Dict[str, float]] = {
    "blueWhite": {
        # Slower, airier drift than the default blueWhite — clouds
        # should feel like they're passing, not racing.
        "shapeWind":   0.55,
        "shapeSCurve": 0.25,
        "shapeOrbit":  0.72,
        "shapeLobe":   1.35,
    },
}
"""Airier ``blueWhite`` — less wind, gentler curvature, rounder lobes
so the cloud shapes stay soft."""

__all__ = ["PALETTES", "OVERRIDES"]
