"""Lane 2 — raster-derived SVG via vtracer.

We learned the hard way that asking an LLM to write SVG by hand
produces visibly-synthetic output (too few paths, too clean, no
pencil-grain character). The fix: generate a high-quality raster via
the same pipeline as the raster lane, then vectorise it with
`vtracer` — a Rust-core tracer with decent Python bindings.

The result is a real SVG (scalable, editable, diffable) that inherits
the pencil-grain character of the raster source. Takes roughly 2–4x
longer than raster alone because we pay for both the LLM image-gen and
the CPU-bound trace.

Why `colormode='binary'`:
    The raster pipeline outputs a black-pencil-on-transparent RGBA
    PNG. Tracing in binary mode produces a single-colour SVG (black
    paths on transparent) — the right shape for the brand's
    illustration medium (black pencil, transparent background). Colour
    mode would invent unnecessary fill layers.

Why `filter_speckle=4`:
    Removes stray sub-4-pixel specks from the tracer output. Default.
    Higher (8+) smooths more aggressively at the cost of pencil grain
    fidelity.
"""

from __future__ import annotations

import io

import vtracer
from PIL import Image

from brand.illustrations.providers.litellm_raster import render as render_raster
from brand.illustrations.style import IllustrationStyle


def _flatten_on_white(rgba_png: bytes) -> bytes:
    """Composite a transparent RGBA PNG onto pure white → opaque RGB PNG.

    vtracer's binary mode thresholds a single image channel. Feeding it
    our pencil-on-transparent RGBA output confuses the thresholder
    (every non-transparent pixel is ~black, so the whole image reads as
    one big fill). Flattening onto white first gives vtracer the
    black-on-white image it expects.
    """
    src = Image.open(io.BytesIO(rgba_png)).convert("RGBA")
    white = Image.new("RGB", src.size, (255, 255, 255))
    white.paste(src, mask=src.split()[3])  # alpha channel as mask
    buf = io.BytesIO()
    white.save(buf, format="PNG")
    return buf.getvalue()


def render(
    *,
    scene: str,
    style: IllustrationStyle,
    size: str = "1024x1024",
    filter_speckle: int = 4,
    quality: str = "medium",
) -> bytes:
    """Render a vector SVG for *scene* under *style*, raster-then-trace.

    Parameters
    ----------
    scene
        Description of what to draw (passed straight to the raster lane).
    style
        Theme-provided illustration knobs (passed to the raster lane).
    size
        ``WxH`` — raster generation size. vtracer preserves whatever
        pixel grid the raster came in at.
    filter_speckle
        Minimum speck size (in pixels) kept during tracing. Lower =
        more pencil-grain fidelity; higher = smoother paths.
    quality
        ``standard`` / ``medium`` / ``high`` — forwarded to the raster
        lane.
    """
    rgba_png = render_raster(
        scene=scene,
        style=style,
        size=size,
        quality=quality,
    )
    opaque_png = _flatten_on_white(rgba_png)
    svg_str = vtracer.convert_raw_image_to_svg(
        opaque_png,
        img_format="png",
        colormode="binary",
        filter_speckle=filter_speckle,
    )
    return svg_str.encode("utf-8")


__all__ = ["render"]
