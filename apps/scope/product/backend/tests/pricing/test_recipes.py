"""Tests for :mod:`pricing.recipes`."""
from __future__ import annotations

from pricing import Recipe, find_recipe
from pricing.recipes import load_recipes, recipe_score


def test_load_recipes_returns_list() -> None:
    recipes = load_recipes()
    assert isinstance(recipes, list)
    assert len(recipes) > 0
    for r in recipes:
        assert isinstance(r, Recipe)


def test_recipes_have_required_fields() -> None:
    for r in load_recipes():
        assert r.id
        assert r.unit
        assert r.unit_cost_eur >= 0
        assert r.market_multiplier > 0
        assert isinstance(r.tags, list)


def test_find_recipe_hits_bath_keyword() -> None:
    r = find_recipe("reforma bano")
    assert r is not None
    # Some recipe matching bath/shower/room
    assert any(kw in r.slug.lower() or kw in r.title_es.lower() or kw in r.title_en.lower()
               for kw in ("bath", "shower", "baño", "bano", "cuarto"))


def test_find_recipe_returns_none_for_gibberish() -> None:
    r = find_recipe("xzqnonsensequery")
    assert r is None


def test_find_recipe_empty_returns_none() -> None:
    assert find_recipe("") is None
    assert find_recipe("   ") is None


def test_recipe_score_exact_tag_match_high() -> None:
    """``recipe_score`` expects a pre-normalised query (accent-stripped,
    lowercased) — mirror the caller contract in :func:`find_recipe`."""

    from pricing.recipes import _normalise

    recipes = load_recipes()
    r = recipes[0]
    assert r.tags, "recipe 0 should have tags"
    score = recipe_score(r, _normalise(r.tags[0]))
    assert score > 0


def test_recipe_score_no_match_zero() -> None:
    recipes = load_recipes()
    r = recipes[0]
    score = recipe_score(r, "xzqnonsense")
    assert score == 0
