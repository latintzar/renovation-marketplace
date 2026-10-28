"""Rerank helpers (D11).

A rerank is a pure function ``list[SearchResult] → list[SearchResult]``.
Two rerankers ship in this module:

* :func:`city_boost` — preferential treatment for results that mention a
  specific Spanish city in their ``meta["city_prices"]`` payload.
* :func:`chain_reranks` — compose multiple rerankers left-to-right.

Convention: because :class:`~fulltext.results.SearchResult` is frozen,
rerankers MUST emit fresh instances (via :func:`dataclasses.replace`)
rather than attempting to write back. Callers are responsible for
sorting the output if their reranker alters ranks — some do (city
boost), some only filter or reorder (diversity reranker in a future
wave).
"""
from __future__ import annotations

from dataclasses import replace

from core.text import strip_accents

from ._stemmer import stem_word
from .protocols import Rerank
from .results import SearchResult

__all__ = ["city_boost", "chain_reranks"]


def city_boost(city: str, *, amount: float = 20.0) -> Rerank:
    """Return a reranker that subtracts ``amount`` from the rank of
    any result whose ``meta["city_prices"]`` mentions ``city``.

    Rationale (D11): BM25 scores from SQLite FTS5 are **negative**
    (lower = better). Subtracting lowers further, promoting the
    match. The default ``20.0`` is a hard override — enough to
    beat almost any BM25 delta but still tunable per consumer.

    Matching uses stemmed accent-stripped substrings so
    ``"Málaga"`` matches ``"Malaga centro"`` and vice versa.
    """

    target = stem_word(strip_accents(city.lower())) if city else ""

    def _run(results: list[SearchResult]) -> list[SearchResult]:
        if not target:
            return list(results)
        out: list[SearchResult] = []
        for r in results:
            city_prices = r.meta.get("city_prices", []) if isinstance(r.meta, dict) else []
            boost = False
            for cp in city_prices:
                cp_city_raw = cp.get("city", "") if isinstance(cp, dict) else ""
                cp_city = strip_accents(str(cp_city_raw).lower())
                if not cp_city:
                    continue
                if target in cp_city or cp_city in target:
                    boost = True
                    break
            if boost:
                out.append(replace(r, rank=r.rank - amount))
            else:
                out.append(r)
        out.sort(key=lambda x: x.rank)
        return out

    return _run


def chain_reranks(*rerankers: Rerank) -> Rerank:
    """Compose rerankers left-to-right.

    ``chain_reranks(a, b, c)(results)`` is equivalent to
    ``c(b(a(results)))``. Zero rerankers returns an identity.
    """

    def _run(results: list[SearchResult]) -> list[SearchResult]:
        current = list(results)
        for r in rerankers:
            current = list(r(current))
        return current

    return _run
