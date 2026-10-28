"""Raster illustration provider — LiteLLM image-gen + Pillow.

Two-block prompt: frozen STYLE boilerplate + tight SUBJECT line. The
style is never parameterised — every call produces an image in the
same hand. Theme knobs on :class:`IllustrationStyle` (line_weight,
grain_strength, mood) are retained on the dataclass for future use
but are NOT mixed into the prompt: they were causing style drift by
fighting the frozen register.

Pipeline:

1. ``generate_image`` with the frozen prompt + caller's scene.
2. ``luminosity_alpha`` knocks white to transparent and force-blacks
   any surviving RGB, enforcing the ink-only rule.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from llm import DEFAULT_IMAGE_GEN, generate_image

from brand.illustrations.post.chroma_key import process as chroma_key
from brand.illustrations.post.luminosity_alpha import process as luminosity_alpha
from brand.illustrations.style import IllustrationStyle

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_PROMPT_PATH = _PROMPTS_DIR / "raster_bold_marker.md"


def _load_template() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _build_prompt(*, scene: str) -> str:
    return _load_template().replace("{scene}", scene.strip())


def render(
    *,
    scene: str,
    style: IllustrationStyle,
    size: str = "1024x1024",
    model: str = DEFAULT_IMAGE_GEN,
    post: Literal["luminosity_alpha", "chroma_key"] = "luminosity_alpha",
    quality: Literal["standard", "medium", "high"] = "medium",
) -> bytes:
    """Render a raster illustration of *scene* in the Leo house register.

    Returns PNG bytes with a real alpha channel.

    Parameters
    ----------
    scene
        Tight description of ONE motif — "a panther", "a wine bottle",
        "the letter B", "an arrow pointing right". Never combos.
    style
        Theme-level metadata. Currently only its existence is used by
        this provider; per-image knobs (line_weight, grain_strength,
        mood) are intentionally not forwarded — the style is frozen
        in the prompt to keep every generation in the same hand.
    size
        ``WxH`` — 1024x1024 is universal; 512x512 and 1792x1024 also
        accepted by most upstream models.
    model
        Image-gen model id. Defaults to :data:`llm.DEFAULT_IMAGE_GEN`.
    post
        ``luminosity_alpha`` (default) computes alpha from darkness
        and force-blacks the RGB; ``chroma_key`` is a hard fallback
        that strips a single specified colour.
    quality
        ``standard`` → 1K, ``medium`` → 2K, ``high`` → 4K (Nano
        Banana Pro only). 2K is the sweet spot.
    """
    # IllustrationStyle is accepted for API stability + future use but
    # not currently forwarded into the prompt. See module docstring.
    _ = style
    prompt = _build_prompt(scene=scene)
    png = generate_image(
        prompt,
        model=model,
        size=size,
        response_format="bytes",
        extra={"quality": quality},
    )
    if not isinstance(png, bytes):
        raise TypeError(
            f"generate_image returned {type(png).__name__}; expected bytes. "
            "Did you accidentally pass response_format='url'?"
        )
    if post == "chroma_key":
        return chroma_key(png, color=(255, 255, 255), tolerance=12)
    return luminosity_alpha(png)


__all__ = ["render"]
