"""Typed search errors (D8).

All remote providers raise :class:`SearchError` or a subclass. Local
FTS never raises — ``sqlite3.OperationalError`` is caught at the
``DomainIndex.search`` boundary and converted to an empty result list
with a logged warning (retrieval is best-effort; tools must degrade
gracefully, never 500).

Subclasses exist so callers can implement tiered fallback:

* :class:`ProviderTimeout` → retry once, then fall back to local FTS.
* :class:`QuotaExceeded`  → cool-down; do not retry.
* :class:`ProviderError`  → generic upstream failure; fall through.
"""
from __future__ import annotations

__all__ = [
    "SearchError",
    "ProviderError",
    "QuotaExceeded",
    "ProviderTimeout",
]


class SearchError(Exception):
    """Base class for all search-related errors."""


class ProviderError(SearchError):
    """Generic remote-provider failure (HTTP 5xx, parse error, etc.)."""


class QuotaExceeded(ProviderError):
    """Provider refused the request due to rate limit / quota / 429."""


class ProviderTimeout(ProviderError):
    """Provider did not respond within the configured timeout."""
