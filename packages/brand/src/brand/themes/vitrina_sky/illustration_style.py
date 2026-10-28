"""Vitrina-sky theme — illustration metadata.

Uses the canonical Leo illustration register (black pencil, transparent
— universal across every theme, see :mod:`brand.illustrations.style`).
Vitrina-sky's accent tint is the **Dijon honey-mustard**, used for
hairline highlights on drawings (e.g. a thin amber under-stroke under
a pencil line).
"""

from __future__ import annotations

from brand.illustrations.style import IllustrationStyle

DEFAULT = IllustrationStyle(
    name="vitrina-sky",
    accent_color="#D89B2E",  # Dijon honey-mustard; see tokens.py THEMES["vitrina_sky"].dijon
)

__all__ = ["IllustrationStyle", "DEFAULT"]
