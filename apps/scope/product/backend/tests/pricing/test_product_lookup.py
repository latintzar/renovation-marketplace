"""Tests for :mod:`pricing.product_lookup`.

The Leroy Merlin+manufacturer ``products.db`` (~78 MB) is NOT bundled
in the wheel. Lookups therefore raise :class:`IndexNotFoundError` when
no path is configured.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pricing import ProductList, config, lookup_product
from pricing.errors import IndexNotFoundError, QueryEmptyError


def test_missing_products_db_raises() -> None:
    with pytest.raises(IndexNotFoundError):
        lookup_product("azulejo")


def test_empty_query_raises() -> None:
    with pytest.raises(QueryEmptyError):
        lookup_product("")


def test_structured_shape_when_db_reachable() -> None:
    """Integration: runs only if the external products.db is on disk."""

    candidates = [
        Path("scripts/ops/data/indexes/products.db"),
        Path("apps/scope/product/backend/data/products.db"),
    ]
    products_db = next((p for p in candidates if p.exists()), None)
    if products_db is None:
        pytest.skip("products.db not available in this environment")

    config.configure(products_db=products_db)
    out = lookup_product("azulejo")
    assert isinstance(out, ProductList)
    assert out.query == "azulejo"
    assert isinstance(out.items, list)
    assert isinstance(out.text, str)
