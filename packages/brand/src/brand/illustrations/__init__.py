"""brand.illustrations — the Leo house illustration generator.

**One register, every theme.** The illustration style is universal
across every Leo theme: Matisse-naive felt-tip marker on paper,
single uniform stroke width, wobbly committed lines, black ink on
transparent, one motif per image. Themes differ in surface colour
and type, not in illustration style. The register is frozen in
``prompts/raster_bold_marker.md``.

Two lanes, both raster-derived:

- ``raster`` (default) — Gemini 3 Pro Image / Nano Banana Pro (via
  OpenRouter) + distance-from-white alpha post-processing. Returns
  PNG bytes with real alpha.
- ``vector`` — same raster, flattened onto white, then traced by
  :mod:`vtracer` to a real SVG. Returns SVG UTF-8.

Plus a reference-aware entrypoint (:func:`generate_with_references`)
for consistent-character work (same mascot in three poses, etc.).
Uses Nano Banana Pro's native multi-image chat endpoint — up to 5
reference images.

Masters are always black-on-transparent. Theme accent colours apply
at tint/composite time, not at draw time, so a single master asset
can ship across every theme.

>>> from brand.illustrations import generate
>>> png = generate(theme="warm_drift", scene="a panther prowling, half-lidded eyes, cool and relaxed")
>>> png[:8]
b'\\x89PNG\\r\\n\\x1a\\n'
"""

from __future__ import annotations

from brand.illustrations.generate import (
    Lane,
    Quality,
    generate,
    generate_with_references,
)

__all__ = ["generate", "generate_with_references", "Lane", "Quality"]
