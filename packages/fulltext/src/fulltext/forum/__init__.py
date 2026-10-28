"""Forum / community-driven Q&A dispatcher.

Stub surface for the package skeleton (D14). Typical sources include
Spanish construction forums (habitissimo replies, r/spain DIY, todoexpertos)
where real contractors describe real jobs — richer than press releases.

Contract mirrors :mod:`fulltext.web` and :mod:`fulltext.legal`.
"""
from __future__ import annotations

from typing import Awaitable, Callable, Optional

from ..results import SearchResult

__all__ = ["forum_search", "set_provider"]

_Provider = Callable[..., Awaitable[list[SearchResult]]]

_provider: Optional[_Provider] = None


def set_provider(provider: Optional[_Provider]) -> None:
    """Inject a concrete async forum-search provider."""

    global _provider
    _provider = provider


async def forum_search(
    query: str, *, limit: int = 10
) -> list[SearchResult]:
    """Async forum-corpus search."""

    if _provider is None:
        return []
    return await _provider(query, limit=limit)
