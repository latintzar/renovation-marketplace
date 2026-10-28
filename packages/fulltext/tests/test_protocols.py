"""Unit tests for :mod:`fulltext.protocols`."""
from __future__ import annotations

from fulltext import DomainIndex, Rerank, SearchIndex, SearchProvider, SearchResult


def test_domain_index_matches_search_index_protocol(tmp_index: DomainIndex) -> None:
    assert isinstance(tmp_index, SearchIndex)


def test_search_provider_is_structural() -> None:
    class _Stub:
        async def search(
            self, query: str, *, limit: int = 10
        ) -> list[SearchResult]:
            return []

    assert isinstance(_Stub(), SearchProvider)


def test_rerank_is_callable_alias() -> None:
    def identity(rs: list[SearchResult]) -> list[SearchResult]:
        return rs

    r: Rerank = identity
    out = r([SearchResult(doc_id="x", rank=0.0)])
    assert len(out) == 1
