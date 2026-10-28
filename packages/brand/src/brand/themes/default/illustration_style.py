"""Default theme — illustration metadata.

The illustration register (Matisse-naive, wobbly single-width marker,
black ink on transparent) is universal across every Leo theme. It
lives in :mod:`brand.illustrations.style`. Themes only differ in the
``accent_color`` downstream tint helpers use when re-colouring the
black master onto a themed surface.

The default theme uses the canonical Leo accent, so we re-export the
shared :data:`LEO_ILLUSTRATION_STYLE` directly.
"""

from __future__ import annotations

from brand.illustrations.style import (
    LEO_ILLUSTRATION_STYLE as DEFAULT,
    IllustrationStyle,
)

__all__ = ["IllustrationStyle", "DEFAULT"]
