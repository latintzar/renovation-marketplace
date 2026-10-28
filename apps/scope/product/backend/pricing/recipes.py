"""Curated residential-renovation recipes.

``residential_recipes.json`` bundles ~128 hand-authored templates
covering common Spanish home-renovation tasks (bathroom, kitchen,
painting, tiling, plumbing, electrical, HVAC). Each recipe has:

- ``unit_cost_eur`` — the raw cost-of-inputs (materials + labour at
  Convenio rates).
- ``market_multiplier`` — the typical CYPE → market markup for the
  trade.
- ``market_range_eur`` — the typical market price range (``min``,
  ``max``).
- ``key_variables`` — free-text hints the LLM uses to ask the right
  follow-up questions.

Public API:

- :func:`load_recipes` — lazy-load and cache the recipe list.
- :func:`find_recipe(query)` — best-match lookup via tokenizer + score.
- :func:`recipe_score` — per-recipe relevance score (exposed for
  tests + debugging).
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from core.text import strip_accents

from . import config
from .errors import IndexNotFoundError
from .types import Recipe

logger = logging.getLogger(__name__)

__all__ = [
    "load_recipes",
    "find_recipe",
    "recipe_score",
]


_recipes_cache: Optional[List[Recipe]] = None


def _clear_cache() -> None:
    """Drop the in-memory recipe cache. Called from :func:`pricing.configure`."""

    global _recipes_cache
    _recipes_cache = None


def load_recipes() -> List[Recipe]:
    """Return the in-memory recipe list, loading once.

    Empty list if the file is missing (graceful degradation — the caller
    falls back through CYPE/market layers).
    """

    global _recipes_cache
    if _recipes_cache is not None:
        return _recipes_cache

    path = config.recipes_path()
    if path is None or not path.exists():
        logger.warning("residential_recipes.json not found at %s", path)
        _recipes_cache = []
        return _recipes_cache

    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise IndexNotFoundError(
            f"Could not load recipes from {path!s}: {exc}"
        ) from exc

    raw = data.get("recipes", [])
    _recipes_cache = [Recipe.from_dict(r) for r in raw]
    logger.info("loaded %d curated recipes", len(_recipes_cache))
    return _recipes_cache


def _normalise(text: str) -> str:
    return strip_accents(text).lower().strip()


def recipe_score(recipe: Recipe, query_normalized: str) -> float:
    """Per-recipe relevance score against a normalised query.

    Weights match the legacy ``_recipe_score`` in
    ``leo_agent/price_engine.py`` verbatim (slug:2, title:1.5, tag:1.0)
    so the recipe fallback behaves identically during migration.
    """

    if not query_normalized:
        return 0.0

    slug_norm = _normalise(recipe.slug)
    title_en_norm = _normalise(recipe.title_en)
    title_es_norm = _normalise(recipe.title_es)
    tags_norm = [_normalise(t) for t in recipe.tags]

    score = 0.0
    for token in query_normalized.split():
        if token in slug_norm:
            score += 2.0
        if token in title_en_norm or token in title_es_norm:
            score += 1.5
        for tag in tags_norm:
            if token in tag or tag in token:
                score += 1.0

    return score


def find_recipe(query: str, threshold: float = 1.0) -> Optional[Recipe]:
    """Best-match recipe for a free-text query.

    Returns None if no recipe scores above ``threshold``. Mirrors the
    legacy implementation so the recipe layer is bit-for-bit equivalent
    during migration.
    """

    if not query or not query.strip():
        return None

    query_norm = _normalise(query)

    best_score = 0.0
    best_recipe: Optional[Recipe] = None

    for recipe in load_recipes():
        score = recipe_score(recipe, query_norm)
        if score > best_score:
            best_score = score
            best_recipe = recipe

    if best_score >= threshold:
        return best_recipe
    return None
