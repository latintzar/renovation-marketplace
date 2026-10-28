"""Canonical Leo illustration style — shared across every theme.

The illustration register (Matisse-naive, single-width wobbly marker,
black ink on transparent) is the same for every theme. It's frozen in
``prompts/raster_bold_marker.md`` — no per-theme prompt variation.

This dataclass used to carry per-theme knobs (line_weight, grain,
mood words) and a scene vocabulary. Those were fighting the frozen
prompt and causing style drift, so they're gone. What remains is the
one thing that genuinely differs per theme: ``accent_color``, which
downstream tint steps use to re-colour the black master onto a
themed surface.

Themes import and re-export :data:`LEO_ILLUSTRATION_STYLE` (or build
their own copy with a different ``accent_color``) from their
``illustration_style.py``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IllustrationStyle:
    """Theme-level illustration metadata.

    Only ``accent_color`` is used today — and only by downstream tint
    helpers, never by the render itself. The master is always pure
    black ink on transparent (see ``prompts/raster_bold_marker.md``).
    """

    name: str
    accent_color: str  # hex — theme metadata only; NOT in master render.


# The canonical Leo illustration style. Themes may re-export this
# directly, or build their own IllustrationStyle with a different
# accent_color when they want a distinct tint downstream.
LEO_ILLUSTRATION_STYLE = IllustrationStyle(
    name="leo",
    accent_color="#DA654D",
)


__all__ = ["IllustrationStyle", "LEO_ILLUSTRATION_STYLE"]
