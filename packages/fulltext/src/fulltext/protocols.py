"""Structural protocols for search primitives (D7).

Why Protocols instead of ABCs: :class:`SearchIndex` is implemented by
the concrete :class:`~fulltext.index.DomainIndex`, but consumers only
depend on the *shape*. This lets us swap in a Qdrant-backed or
in-memory fake without inheriting a base class — handy for testing
and for future vector-retrieval experiments.

``SearchProvider`` is the async dual for remote providers
(:mod:`fulltext.web`, :mod:`fulltext.legal`, :mod:`fulltext.forum`). A provider
is any async callable-wrapper exposing ``.search(query, *, limit)``.
"""
from __future__ import annotations

from typing import Callable, Protocol, runtime_checkable

from .results import SearchResult

__all__ = ["SearchIndex", "SearchProvider", "Rerank"]


@runtime_checkable
class SearchIndex(Protocol):
    """Protocol for a synchronous, local full-text index."""

    def search(
        self,
        query: str,
        limit: int = 10,
        city: str = "",
    ) -> list[SearchResult]:
        """Return up to ``limit`` BM25-ranked results."""

    def count(self) -> int:
        """Return total indexed document count."""


@runtime_checkable
class SearchProvider(Protocol):
    """Protocol for an asynchronous remote search provider."""

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Return up to ``limit`` results; MAY raise
        :class:`~fulltext.errors.SearchError` subclasses."""


Rerank = Callable[[list[SearchResult]], list[SearchResult]]
"""Type alias for a rerank function (in → out, pure, stateless).

Rerankers MUST NOT mutate inputs. Use :func:`dataclasses.replace` to
emit new frozen ``SearchResult`` objects when adjusting ranks.
Composition via :func:`fulltext.rerank.chain_reranks`.
"""
