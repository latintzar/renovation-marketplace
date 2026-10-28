"""Unit tests for :mod:`scrapers.houzz`."""
from __future__ import annotations

import pytest

from scrapers.houzz import build_query, search


def test_build_query_basic() -> None:
    q = build_query("fontaneros", "madrid")
    assert "fontaneros" in q
    assert "madrid" in q
    assert "/geo/es" in q


def test_build_query_respects_country() -> None:
    q = build_query("plumbers", "london", country="uk")
    assert "/geo/uk" in q


def test_build_query_lowercases() -> None:
    q = build_query("FONTANEROS", "MADRID")
    assert "FONTANEROS" not in q
    assert "fontaneros" in q


def test_build_query_handles_spaces() -> None:
    q = build_query("kitchen remodel", "new york")
    assert "kitchen-remodel" in q or "kitchen+remodel" in q
    assert "new-york" in q or "new+york" in q


@pytest.mark.asyncio
async def test_search_stub_returns_empty() -> None:
    assert await search("t", "c") == []
