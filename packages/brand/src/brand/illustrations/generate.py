"""Illustration dispatcher — one register, two lanes.

Public entry points:

- :func:`generate` — text-only brief → PNG (raster) or SVG (vector).
- :func:`generate_with_references` — brief + 1..5 reference images,
  for consistent-character work. Raster-only; uses Nano Banana Pro's
  native multi-image chat endpoint under the hood.

The illustration register is universal across every Leo theme —
see :mod:`brand.illustrations` for the house style. ``theme`` is
accepted for API symmetry (and to look up the accent colour for any
downstream tint step) but does NOT vary the drawing itself.

Both lanes start from the same raster pipeline (Gemini 3 Pro Image
via OpenRouter + distance-from-white alpha). The vector lane traces
the raster with vtracer so the SVG inherits the hand character of
the raster instead of being LLM-invented.

See ``DESIGN.md`` for the rulebook.
"""

from __future__ import annotations

import importlib
from typing import Literal, Sequence

from brand.illustrations.style import IllustrationStyle

Lane = Literal["raster", "vector"]
Quality = Literal["standard", "medium", "high"]


def _load_theme_style(theme: str) -> IllustrationStyle:
    """Resolve the ``IllustrationStyle`` for *theme* via dynamic import."""
    module = importlib.import_module(
        f"brand.themes.{theme}.illustration_style"
    )
    style = getattr(module, "DEFAULT", None)
    if style is None or not isinstance(style, IllustrationStyle):
        raise ValueError(
            f"theme {theme!r}'s illustration_style.py must export "
            "DEFAULT: IllustrationStyle"
        )
    return style


def generate(
    *,
    theme: str,
    scene: str,
    lane: Lane = "raster",
    size: str = "1024x1024",
    quality: Quality = "medium",
) -> bytes:
    """Generate an illustration of *scene* in the Leo house register.

    The house register is frozen in
    ``prompts/raster_bold_marker.md`` — every call produces an image
    in the same hand. *theme* is only used to resolve the
    :class:`IllustrationStyle` dataclass (reserved for future per-
    theme knobs); current implementation does not vary the prompt by
    theme.

    Parameters
    ----------
    theme
        Theme name (matching a subpackage of ``brand.themes`` — e.g.
        ``"default"``, ``"dark"``, ``"warm_drift"``).
    scene
        Tight, single-motif brief: "a panther", "a wine bottle",
        "the letter B", "an arrow pointing right". NEVER combos —
        the house style renders one motif per image.
    lane
        ``"raster"`` (default) — PNG with real alpha.
        ``"vector"`` — raster + vtracer SVG trace.
    size
        ``WxH`` string for request shape. Output resolution is set
        by ``quality``.
    quality
        ``standard`` → 1K, ``medium`` → 2K (default), ``high`` → 4K.
        4K requires the Pro model.

    Returns
    -------
    bytes
        PNG (``lane="raster"``) or SVG UTF-8 (``lane="vector"``).
    """
    style = _load_theme_style(theme)

    if lane == "raster":
        from brand.illustrations.providers import litellm_raster

        return litellm_raster.render(
            scene=scene,
            style=style,
            size=size,
            quality=quality,
        )

    if lane == "vector":
        from brand.illustrations.providers import vtracer_vector

        return vtracer_vector.render(
            scene=scene,
            style=style,
            size=size,
            quality=quality,
        )

    raise ValueError(f"unknown lane {lane!r}; expected 'raster' or 'vector'")


def generate_with_references(
    *,
    theme: str,
    scene: str,
    references: Sequence[bytes],
    aspect_ratio: str = "1:1",
    quality: Quality = "medium",
) -> bytes:
    """Generate a raster illustration that preserves identity across refs.

    Use this when you want a character / object to stay *visually
    consistent* across multiple illustrations — e.g. a mascot in three
    different poses, or the same interior under three different themes.

    Powered by Nano Banana Pro's native multi-image chat endpoint
    (``modalities: ["image", "text"]``). Up to 5 references supported
    for identity preservation.

    Parameters
    ----------
    theme
        Theme name (for style knobs + house-style prompt).
    scene
        Instruction — what should change, what should stay the same.
    references
        Iterable of 1..5 PNG/JPEG byte-strings.
    aspect_ratio
        ``"1:1"`` (default), ``"16:9"``, ``"9:16"``, ``"3:2"``, etc.
    quality
        ``"standard"``/``"medium"``/``"high"`` — see :func:`generate`.

    Returns
    -------
    bytes
        PNG with real alpha (post-processed).
    """
    style = _load_theme_style(theme)
    from brand.illustrations.providers import litellm_raster_refs

    return litellm_raster_refs.render(
        scene=scene,
        style=style,
        references=list(references),
        aspect_ratio=aspect_ratio,
        quality=quality,
    )


__all__ = ["generate", "generate_with_references", "Lane", "Quality"]
