"""Warm-drift theme — illustration metadata.

Uses the canonical Leo illustration register (universal across every
theme — see :mod:`brand.illustrations.style`). Warm-drift's tint
accent differs from default, so we build a local IllustrationStyle
with the warm-drift amber.
"""

from __future__ import annotations

from brand.illustrations.style import IllustrationStyle

DEFAULT = IllustrationStyle(
    name="warm-drift",
    accent_color="#F59E0B",
)

__all__ = ["IllustrationStyle", "DEFAULT"]
