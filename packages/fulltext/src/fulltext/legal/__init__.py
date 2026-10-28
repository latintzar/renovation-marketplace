"""Legal search dispatcher — Spanish construction / labour law.

Stub surface for the package skeleton (D14). The concrete provider
(likely a combination of boe.es scrape + a curated embeddings index
over LOE / LPRL articles) ships alongside its consumer.

Contract mirrors :mod:`fulltext.web`: async, list-of-SearchResult,
raises SearchError on upstream failures, empty list by default.
"""
from __future__ import annotations

from typing import Awaitable, Callable, Optional

from ..results import SearchResult

__all__ = ["legal_search", "set_provider"]

_Provider = Callable[..., Awaitable[list[SearchResult]]]

_provider: Optional[_Provider] = None


def set_provider(provider: Optional[_Provider]) -> None:
    """Inject a concrete async legal-search provider."""

    global _provider
    _provider = provider


async def legal_search(
    query: str, *, limit: int = 10
) -> list[SearchResult]:
    """Async legal-corpus search."""

    if _provider is None:
        return []
    return await _provider(query, limit=limit)
