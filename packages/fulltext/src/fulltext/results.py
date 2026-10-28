"""Canonical :class:`SearchResult` DTO (D9).

One type to rule them all — every provider (FTS, web, legal, forum)
returns a list of these. Downstream code (tools, rerankers, serialisers)
depends on this shape exclusively; providers convert their wire formats
into ``SearchResult`` at the edge.

Frozen for safety: a reranker that mutates one collection's ranks
must not leak into another. Re-rankers copy with ``replace(r, rank=...)``.

The ``body`` field is the **indexable / snippet-worthy** text; for
FTS sources it's the raw body column; for web/legal it's a short
extract or abstract. ``meta`` is the escape hatch for provider-specific
payload (price tables, jurisdiction, vote counts, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["SearchResult"]


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Single item returned by any search provider.

    :param doc_id: Opaque stable identifier. For FTS: ``"hab-fontanero"``.
        For web: the URL. For legal: the boe.es doc number.
    :param rank: Relevance score. **Lower is better** (we follow SQLite
        FTS5's ``bm25()`` convention so city boosts can simply subtract).
        Remote providers normalise to the same convention at the edge.
    :param slug: URL-friendly short identifier (may be empty).
    :param title: Human-readable title.
    :param body: Indexable body text / abstract. Never ``None``; use ``""``.
    :param meta: Provider-specific payload — URL, source, extra fields.
    """

    doc_id: str
    rank: float
    slug: str = ""
    title: str = ""
    body: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
