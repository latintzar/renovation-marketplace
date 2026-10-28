"""Post-processors for raster illustrations.

Two today:

- :func:`luminosity_alpha.process` — preserves pencil grain by mapping
  luminance to alpha (default for raster lane).
- :func:`chroma_key.process` — removes a single near-uniform colour;
  used as the fallback when the upstream model returns a coloured
  (non-white) background.

Both accept and return PNG bytes. Keep the signature stable:
``process(image: bytes, **kwargs) -> bytes``. This lets the raster
provider swap strategies per call.
"""

from __future__ import annotations

from brand.illustrations.post.chroma_key import process as chroma_key
from brand.illustrations.post.luminosity_alpha import process as luminosity_alpha

__all__ = ["luminosity_alpha", "chroma_key"]
