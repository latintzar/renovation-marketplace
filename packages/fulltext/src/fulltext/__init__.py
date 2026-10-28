"""``@scope/fulltext`` — retrieval substrate for the Leo platform.

The package provides three layers:

1. **Local full-text search** — :class:`DomainIndex` (SQLite FTS5 + BM25),
   the engine behind pricing lookups, CYPE rubric search, and any
   future on-disk collection.
2. **Tokenisation & query expansion** — :func:`tokenize`, :func:`expand_query`,
   :data:`EN_ES_SYNONYMS`, split-by-concern stopword pools. A single
   deterministic pipeline used at both index-time and query-time.
3. **Remote dispatcher stubs** — :func:`web_search`, :func:`legal_search`,
   :func:`forum_search`. Async, provider-injectable, SearchError-typed.

Shared primitives (:class:`SearchResult`, :class:`SearchIndex`,
:class:`SearchProvider`, :data:`Rerank`, :func:`city_boost`,
:func:`chain_reranks`, and the :class:`SearchError` family) round out
the 20-symbol public API (D2). Everything else is implementation
detail; import through the package root, not the submodules.
"""
from __future__ import annotations

from .errors import (
    ProviderError,
    ProviderTimeout,
    QuotaExceeded,
    SearchError,
)
from .forum import forum_search
from .index import DomainIndex
from .legal import legal_search
from .protocols import Rerank, SearchIndex, SearchProvider
from .rerank import chain_reranks, city_boost
from .results import SearchResult
from .stopwords import ENGLISH_GENERAL, SPANISH_GENERAL
from .synonyms import EN_ES_SYNONYMS, expand_query
from .tokenizer import stem_word, tokenize
from .web import web_search

__all__ = [
    "DomainIndex",
    "SearchResult",
    "SearchIndex",
    "SearchProvider",
    "Rerank",
    "tokenize",
    "stem_word",
    "SPANISH_GENERAL",
    "ENGLISH_GENERAL",
    "EN_ES_SYNONYMS",
    "expand_query",
    "city_boost",
    "chain_reranks",
    "web_search",
    "legal_search",
    "forum_search",
    "SearchError",
    "ProviderError",
    "QuotaExceeded",
    "ProviderTimeout",
]
