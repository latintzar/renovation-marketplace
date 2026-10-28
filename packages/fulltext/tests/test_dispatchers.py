"""Unit tests for the async dispatchers in :mod:`fulltext.web`,
:mod:`fulltext.legal`, and :mod:`fulltext.forum`.

All three share the same contract: async callable, returns
``list[SearchResult]``, defaults to empty, accepts a provider
injection via ``set_provider``."""
from __future__ import annotations

import pytest

from fulltext import QuotaExceeded, SearchResult, forum_search, legal_search, web_search
from fulltext import forum as forum_mod
from fulltext import legal as legal_mod
from fulltext import web as web_mod


@pytest.fixture(autouse=True)
def _reset_providers():
    yield
    web_mod.set_provider(None)
    legal_mod.set_provider(None)
    forum_mod.set_provider(None)


@pytest.mark.asyncio
async def test_web_search_empty_by_default() -> None:
    assert await web_search("plumber") == []


@pytest.mark.asyncio
async def test_legal_search_empty_by_default() -> None:
    assert await legal_search("despido") == []


@pytest.mark.asyncio
async def test_forum_search_empty_by_default() -> None:
    assert await forum_search("reforma baño") == []


@pytest.mark.asyncio
async def test_set_provider_routes_to_injected() -> None:
    calls: list[tuple[str, int]] = []

    async def fake(query: str, *, limit: int = 10) -> list[SearchResult]:
        calls.append((query, limit))
        return [SearchResult(doc_id="w1", rank=-1.0, title=query)]

    web_mod.set_provider(fake)
    out = await web_search("hello", limit=3)
    assert len(out) == 1
    assert out[0].title == "hello"
    assert calls == [("hello", 3)]


@pytest.mark.asyncio
async def test_provider_exceptions_propagate() -> None:
    async def flaky(query: str, *, limit: int = 10) -> list[SearchResult]:
        raise QuotaExceeded("over limit")

    web_mod.set_provider(flaky)
    with pytest.raises(QuotaExceeded):
        await web_search("x")
