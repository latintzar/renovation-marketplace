"""Tests for :mod:`pricing.price_lookup`.

The Habitissimo+CronoShare ``prices.db`` (~9 MB) is **not bundled** in
the wheel — it lives under ``scripts/ops/data/indexes/prices.db`` on
the Hetzner host. Lookups therefore raise :class:`IndexNotFoundError`
when no path is configured; tests here exercise that contract, and a
single integration test runs against the real DB when it's reachable.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pricing import MarketReport, config, lookup_market
from pricing.errors import IndexNotFoundError, QueryEmptyError


def test_missing_prices_db_raises() -> None:
    """No prices.db + no env var → :class:`IndexNotFoundError`."""

    with pytest.raises(IndexNotFoundError):
        lookup_market("azulejo", city="Madrid")


def test_empty_query_raises() -> None:
    with pytest.raises(QueryEmptyError):
        lookup_market("", city="Madrid")


def test_structured_shape_when_db_reachable() -> None:
    """Integration: runs only if the external prices.db is on disk."""

    candidates = [
        Path("scripts/ops/data/indexes/prices.db"),
        Path("apps/scope/product/backend/data/prices.db"),
    ]
    prices_db = next((p for p in candidates if p.exists()), None)
    if prices_db is None:
        pytest.skip("prices.db not available in this environment")

    config.configure(prices_db=prices_db)
    out = lookup_market("azulejo", city="Madrid", max_results=3)
    assert isinstance(out, MarketReport)
    assert out.query == "azulejo"
    assert out.city == "Madrid"
    assert isinstance(out.items, list)
    assert isinstance(out.sources_used, list)
    assert isinstance(out.city_prices_eur, list)
    assert isinstance(out.text, str)
