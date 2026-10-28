"""Provider modules for the illustration dispatcher.

Two lanes today, both raster-derived:

- :mod:`brand.illustrations.providers.litellm_raster` — the raster
  pipeline (Gemini 2.5 Flash Image via OpenRouter + Pillow alpha).
- :mod:`brand.illustrations.providers.vtracer_vector` — reuses the
  raster lane and traces the PNG with vtracer into SVG.

See ``../DESIGN.md`` for why we removed the Claude-writes-SVG lane.
"""
