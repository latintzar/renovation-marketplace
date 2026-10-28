"""Dark theme — illustration metadata.

Uses the canonical Leo illustration register (universal across every
theme — see :mod:`brand.illustrations.style`). Dark theme inherits
the default accent for now; downstream tint helpers may want to
brighten it when composited on a dark surface.
"""

from __future__ import annotations

from brand.illustrations.style import (
    LEO_ILLUSTRATION_STYLE as DEFAULT,
    IllustrationStyle,
)

__all__ = ["IllustrationStyle", "DEFAULT"]
