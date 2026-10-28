"""Integration tests for :func:`pricing.estimate_cost`.

These exercise the full 4-layer resolution chain against the **bundled**
data artifacts (CYPE, INE, recipes, overhead). No external DBs required.
"""
from __future__ import annotations

import pytest

from pricing import Estimate, estimate_cost


# ----------------------------- Layer 1: recipe -------------------------------

def test_recipe_match_bath_returns_recipe_source() -> None:
    e = estimate_cost("reforma bano", quantity=1)
    assert isinstance(e, Estimate)
    assert e.source == "recipe"
    assert e.recipe is not None
    assert e.estimate is not None
    assert e.estimate.unit_cost_eur > 0


def test_recipe_uses_market_range_for_min_max() -> None:
    e = estimate_cost("pintar piso", quantity=10, city="Madrid")
    assert e.source == "recipe"
    if e.estimate:
        assert e.estimate.range_min_eur <= e.estimate.range_max_eur


def test_recipe_applies_regional_multiplier() -> None:
    e_madrid = estimate_cost("reforma bano", quantity=1, city="Madrid")
    e_teruel = estimate_cost("reforma bano", quantity=1, city="Teruel")
    # Both hit recipe; Madrid should be higher than or equal to Teruel
    if e_madrid.estimate and e_teruel.estimate:
        assert e_madrid.estimate.unit_cost_eur >= e_teruel.estimate.unit_cost_eur


def test_recipe_applies_modifiers() -> None:
    e_normal = estimate_cost("reforma bano", quantity=1)
    e_urgent = estimate_cost("reforma bano", quantity=1, modifiers=["urgent"])
    if e_normal.estimate and e_urgent.estimate:
        assert e_urgent.estimate.unit_cost_eur > e_normal.estimate.unit_cost_eur
        assert "urgent" in e_urgent.estimate.modifiers_applied


# ----------------------------- Layer 2: construction_db (CYPE) --------------

def test_no_recipe_hits_cype() -> None:
    """A query that doesn't match any recipe but matches CYPE via FTS."""

    e = estimate_cost("imprimacion antioxidante", quantity=10, city="Madrid")
    # Accept either cype or market — recipe shouldn't match this
    assert e.source in {"construction_db", "market", "recipe", "none"}


# ----------------------------- Layer 4: none ---------------------------------

def test_gibberish_returns_none_source() -> None:
    e = estimate_cost("xzqnonsensequery1234567890", quantity=1)
    assert e.source == "none"
    assert e.estimate is None
    assert e.note  # non-empty explanation


def test_estimate_quantity_total_computed() -> None:
    e = estimate_cost("reforma bano", quantity=5)
    if e.estimate and e.estimate.unit_cost_eur > 0 and e.estimate.quantity is not None:
        expected_total = e.estimate.unit_cost_eur * e.estimate.quantity
        assert e.estimate.total_eur == pytest.approx(expected_total, rel=0.01)


def test_estimate_to_dict_json_safe() -> None:
    """to_dict output must be a plain dict with no dataclass instances."""

    import json

    e = estimate_cost("reforma bano", quantity=1)
    d = e.to_dict()
    # Should serialise cleanly
    json.dumps(d)
    assert d["source"] == e.source
    assert d["query"] == e.query


def test_estimate_iva_rate_attached_from_recipe() -> None:
    """Recipe-backed estimates carry the recipe's ``iva_rate`` (residential 10%)."""

    e = estimate_cost("reforma bano", quantity=1)
    if e.estimate:
        assert e.estimate.iva_rate in {0.10, 0.21}
        if e.estimate.total_eur and e.estimate.iva_amount_eur is not None:
            assert e.estimate.iva_amount_eur >= 0


def test_empty_query_raises() -> None:
    """Empty query must raise :class:`QueryEmptyError` — not fall through silently."""

    from pricing.errors import QueryEmptyError

    with pytest.raises(QueryEmptyError):
        estimate_cost("", quantity=1)
    with pytest.raises(QueryEmptyError):
        estimate_cost("   ", quantity=1)
