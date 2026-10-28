"""Distance-from-white → alpha, force-black RGB: pure ink on transparent.

The illustration medium is strict black-ink-only on pure white (see
``prompts/_house_style.md``). This post-processor enforces that even if
the upstream model sneaks a stray colour through:

1. alpha_raw = 255 - min(R, G, B)  — distance-from-white. Pure white
   → 0, any non-white → higher.
2. Low-alpha cutoff — anything with ``alpha_raw <= FLOOR`` snaps to
   ``alpha = 0``. The model often renders the "white" background as
   254,254,254 or similar, which naively maps to alpha=1 — a faint
   grey veil invisible in transparent-preview UIs but visible the
   moment you composite on a mid-tone surface. The floor kills that.
3. Above the floor, alpha is rescaled to the full 0..255 range so we
   don't lose edge softness for real ink strokes.
4. RGB = (0, 0, 0) everywhere — anything that survived is pure black.

The module name is "luminosity_alpha" for stable import paths, even
though the maths is "clipped distance-from-white + recolour-to-black".
"""

from __future__ import annotations

import io

from PIL import Image, ImageChops

# Pixels with alpha_raw <= FLOOR (i.e. RGB >= 255-FLOOR) snap to fully
# transparent. 20 clears "nominally white" backgrounds (249..255) and
# the soft-white halo around strokes; real ink edges start well below
# 235 so they're untouched.
_ALPHA_FLOOR = 20


def process(image: bytes) -> bytes:
    """Knock white out, force black. Returns RGBA PNG bytes.

    Raises
    ------
    OSError
        If the input bytes don't decode as an image.
    """
    with Image.open(io.BytesIO(image)) as img:
        rgba = img.convert("RGBA")

    r, g, b, _ = rgba.split()

    # alpha_raw = 255 - min(R, G, B) — pure white → 0, any non-white → high.
    min_rgb = ImageChops.darker(ImageChops.darker(r, g), b)

    # Clipped + rescaled: [0..FLOOR]→0, (FLOOR..255]→stretched to 0..255.
    denom = 255 - _ALPHA_FLOOR
    floor = _ALPHA_FLOOR

    def _remap(v: int) -> int:
        raw = 255 - v  # alpha_raw
        if raw <= floor:
            return 0
        # Stretch (floor, 255] to (0, 255]
        return min(255, round((raw - floor) * 255 / denom))

    alpha = min_rgb.point(_remap)

    black = Image.new("L", rgba.size, 0)
    out = Image.merge("RGBA", (black, black, black, alpha))

    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


__all__ = ["process"]
