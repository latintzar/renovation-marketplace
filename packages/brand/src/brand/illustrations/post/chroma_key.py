"""Chroma-key: fallback for coloured backgrounds.

When the upstream model ignores the white-background instruction and
returns (say) a light beige or pastel backdrop, :func:`process` removes
a specified colour within a small tolerance. Harder edges than
luminosity-alpha — use only when the default doesn't work.
"""

from __future__ import annotations

import io
from typing import Tuple

from PIL import Image


def process(
    image: bytes,
    *,
    color: Tuple[int, int, int] = (255, 255, 255),
    tolerance: int = 12,
) -> bytes:
    """Make pixels within *tolerance* of *color* transparent.

    Parameters
    ----------
    image
        Input PNG bytes.
    color
        ``(r, g, b)`` triple. Default: pure white.
    tolerance
        Per-channel max absolute delta (0–255) that still counts as the
        target colour. 12 is a good default for "near-white paper."

    Returns
    -------
    bytes
        RGBA PNG with matching pixels' alpha set to 0.

    Notes
    -----
    Unlike :func:`brand.illustrations.post.luminosity_alpha.process`,
    this does **not** preserve pencil grain — any pixel within the
    tolerance snaps to alpha=0, every other pixel keeps its original
    colour and alpha=255. Use for flat backgrounds; use luminosity for
    pencil-on-paper.
    """
    with Image.open(io.BytesIO(image)) as img:
        rgba = img.convert("RGBA")

    tr, tg, tb = color
    pixels = rgba.load()
    if pixels is None:
        raise RuntimeError("Pillow failed to load pixel buffer")
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, _ = pixels[x, y]
            if (
                abs(r - tr) <= tolerance
                and abs(g - tg) <= tolerance
                and abs(b - tb) <= tolerance
            ):
                pixels[x, y] = (r, g, b, 0)

    buf = io.BytesIO()
    rgba.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


__all__ = ["process"]
