"""The curated public API of ``@scope/fulltext`` is a contract; changing
it touches every consumer (pricing tools, agent tools, forum bridge).
These tests lock the surface so a slip triggers CI immediately."""
from __future__ import annotations

import fulltext


EXPECTED_SYMBOLS = {
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
}


def test_all_contains_expected_symbols() -> None:
    assert set(fulltext.__all__) == EXPECTED_SYMBOLS


def test_every_symbol_is_importable() -> None:
    for name in EXPECTED_SYMBOLS:
        assert hasattr(fulltext, name), f"missing {name}"
        assert getattr(fulltext, name) is not None


def test_all_list_has_no_duplicates() -> None:
    assert len(fulltext.__all__) == len(set(fulltext.__all__))
