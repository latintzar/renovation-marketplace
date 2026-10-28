"""Reference-aware raster provider — Nano Banana Pro multi-image.

Siblings with :mod:`litellm_raster` but calls the chat-completions path
via :func:`llm.generate_image_with_references` so we can pass 1..5
reference images. Nano Banana Pro (``gemini-3-pro-image``) preserves
identity across references, which is the capability that makes this
worth a separate module.

The same house-style boilerplate + bold-marker prompt template is used
as the text-only lane, so outputs feel like part of the same family.
"""

from __future__ import annotations

from typing import Sequence

from llm import DEFAULT_IMAGE_GEN, generate_image_with_references

from brand.illustrations.post.luminosity_alpha import process as luminosity_alpha
from brand.illustrations.providers.litellm_raster import _build_prompt
from brand.illustrations.style import IllustrationStyle


def render(
    *,
    scene: str,
    style: IllustrationStyle,
    references: Sequence[bytes],
    aspect_ratio: str = "1:1",
    quality: str = "medium",
    model: str = DEFAULT_IMAGE_GEN,
) -> bytes:
    """Render a raster illustration conditioned on reference images.

    Parameters
    ----------
    scene
        Prompt telling the model what to do with the references
        ("same character, different pose", "this mascot in our brand
        colours", etc.).
    style
        Theme-provided illustration knobs.
    references
        1..5 PNG/JPEG byte-strings. Nano Banana Pro uses them for
        identity preservation across subjects.
    aspect_ratio
        ``"1:1"`` / ``"16:9"`` / ``"9:16"`` / ``"3:2"`` — matches
        OpenRouter's accepted values.
    quality
        ``"standard"`` → 1K, ``"medium"`` → 2K, ``"high"`` → 4K.

    Returns
    -------
    bytes
        Post-processed PNG with real alpha (white knocked out).
    """
    refs = list(references)
    if not 1 <= len(refs) <= 5:
        raise ValueError(
            f"references must have 1..5 items, got {len(refs)}. "
            "For no-reference text-to-image, use generate() instead."
        )
    _ = style
    prompt = _build_prompt(scene=scene)
    image_size = {"standard": "1K", "medium": "2K", "high": "4K"}.get(
        quality, "2K"
    )
    png = generate_image_with_references(
        prompt,
        references=refs,
        model=model,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        response_format="bytes",
    )
    if not isinstance(png, bytes):
        raise TypeError(
            f"generate_image_with_references returned {type(png).__name__}; "
            "expected bytes."
        )
    return luminosity_alpha(png)


__all__ = ["render"]
