# packages/fulltext

Shared capability: **keyword retrieval substrate**. Renamed from `packages/search` in Phase 5 Wave 1 to honestly reflect what it does — full-text / keyword search over corpora — vs. a generic "search" wrapper.

## What lives here

- `DomainIndex` — SQLite FTS5 + BM25 engine (used by pricing, CYPE, and any on-disk corpus).
- Spanish + English tokenizer, stemmer, and stopword pools (single source of truth).
- Synonym expansion (`EN_ES_SYNONYMS`, `expand_query`).
- Reranker primitives (`city_boost`, `chain_reranks`).
- Provider-injectable async dispatcher stubs for `web_search`, `legal_search`, `forum_search` (typed, `SearchError`-raising).

## What does NOT live here

- **Semantic / vector search** — lives in `packages/storage` (pgvector embeddings + mem0).
- **Scope-specific indexes** (CYPE, pricing recipes) — those build on top of this engine and live in `apps/scope/product/backend/pricing/` (demoted from `packages/pricing` in Phase 5 Wave 4).
- **Site-specific scrapers** (Habitissimo, Google Maps) — those are retrieval *sources*, not substrate; they live in `packages/scraping` / `apps/scope/`.

## Public API (blessed surface)

```python
from fulltext import (
    DomainIndex,
    SearchResult, SearchIndex, SearchProvider,
    Rerank, city_boost, chain_reranks,
    tokenize, stem_word,
    EN_ES_SYNONYMS, expand_query,
    ENGLISH_GENERAL, SPANISH_GENERAL,
    SearchError, ProviderError, ProviderTimeout, QuotaExceeded,
    web_search, legal_search, forum_search,
)
```

Submodule access (`from fulltext.web.brave import BraveSearch`) is allowed for advanced callers but is not the blessed surface.

## Why the rename

The previous name `search` collided with the English verb, with method names (`DomainIndex.search(...)`), and with scope-level concerns (Habitissimo contractor search, which is a configuration on top of this substrate, not the substrate itself). `fulltext` says exactly what it is.
