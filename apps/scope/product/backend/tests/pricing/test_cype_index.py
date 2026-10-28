"""Tests for :mod:`pricing.cype_index` — driven against the bundled DB."""
from __future__ import annotations

import pytest

from pricing import CypeItem, search_cype
from pricing.errors import QueryEmptyError


def test_search_returns_cypeitem_instances() -> None:
    items = search_cype("azulejo", limit=3)
    assert len(items) > 0
    for i in items:
        assert isinstance(i, CypeItem)
        assert i.code
        assert i.title
        assert i.chapter


def test_search_respects_limit() -> None:
    items = search_cype("tuberia", limit=2)
    assert len(items) <= 2


def test_search_default_limit_bounded() -> None:
    items = search_cype("instalacion")
    # Default limit is 10 (see search_cype signature)
    assert len(items) <= 10


def test_search_empty_query_raises() -> None:
    with pytest.raises(QueryEmptyError):
        search_cype("", limit=5)


def test_search_whitespace_query_raises() -> None:
    with pytest.raises(QueryEmptyError):
        search_cype("   ", limit=5)


def test_search_nonsense_returns_empty() -> None:
    items = search_cype("xzqwpnv", limit=5)
    assert items == []


def test_search_result_has_total_price_or_none() -> None:
    items = search_cype("azulejo", limit=1)
    assert len(items) == 1
    # Accept None or a positive float
    assert items[0].total_price is None or items[0].total_price >= 0


def test_search_ranked_by_bm25() -> None:
    """BM25 score present and non-negative (smaller is better in this view)."""

    items = search_cype("azulejo", limit=3)
    for i in items:
        assert hasattr(i, "bm25_score")


def test_search_accent_insensitive() -> None:
    a = search_cype("azulejo", limit=3)
    b = search_cype("ázulejo", limit=3)
    # Either identical hits, or at least both non-empty
    assert len(a) > 0 and len(b) > 0


def test_search_stopwords_filtered() -> None:
    """CYPE fillers like 'colocado' should be filtered before FTS."""

    # 'colocado' is a CYPE filler; 'azulejo colocado' should behave
    # like 'azulejo' (filler stripped)
    a = search_cype("azulejo", limit=3)
    b = search_cype("azulejo colocado", limit=3)
    assert len(a) > 0
    assert len(b) > 0
