"""Web search dispatcher — generic open-web retrieval.

This module is a **stub** for the package skeleton (D14): the
concrete HTTP provider wiring (Brave / Tavily / Exa) ships with the
consumer that needs it. What's guaranteed here is the *contract*:

* Public surface: :func:`web_search` — ``async (query, *, limit=10) → list[SearchResult]``.
* Errors: raises subclasses of :class:`~fulltext.errors.SearchError`.
* Imports: no side effects at module load.

The default implementation returns ``[]`` — good enough for L1 backend
tests that must run offline, and forces a real provider to be wired
before the search is effective. A consumer that wants a different
provider calls :func:`set_provider` at bootstrap.
"""
from __future__ import annotations

from typing import Awaitable, Callable, Optional

from ..results import SearchResult

__all__ = ["web_search", "set_provider"]

_Provider = Callable[..., Awaitable[list[SearchResult]]]

_provider: Optional[_Provider] = None


def set_provider(provider: Optional[_Provider]) -> None:
    """Inject a concrete async provider. ``None`` reverts to the stub
    (empty-result) behaviour. Intended for app bootstrap + tests."""

    global _provider
    _provider = provider


async def web_search(query: str, *, limit: int = 10) -> list[SearchResult]:
    """Async open-web search. Returns ``[]`` unless a provider has
    been installed via :func:`set_provider`.

    Providers MAY raise :class:`~fulltext.errors.ProviderError` and
    subclasses. The function itself never raises for the stub case."""

    if _provider is None:
        return []
    return await _provider(query, limit=limit)
