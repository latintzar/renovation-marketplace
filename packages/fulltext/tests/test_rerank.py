"""Unit tests for :mod:`fulltext.rerank`."""
from __future__ import annotations

from fulltext import SearchResult, chain_reranks, city_boost


def _mk(doc_id: str, rank: float, **meta) -> SearchResult:
    return SearchResult(doc_id=doc_id, rank=rank, meta=meta)


def test_city_boost_lowers_rank_for_matching_city() -> None:
    results = [
        _mk("a", -1.0, city_prices=[{"city": "Madrid"}]),
        _mk("b", -2.0, city_prices=[{"city": "Barcelona"}]),
    ]
    out = city_boost("Madrid")(results)
    a = next(r for r in out if r.doc_id == "a")
    b = next(r for r in out if r.doc_id == "b")
    assert a.rank < b.rank
    assert a.rank == -21.0


def test_city_boost_is_tolerant_of_accents_and_case() -> None:
    results = [_mk("a", -1.0, city_prices=[{"city": "málaga centro"}])]
    out = city_boost("Malaga")(results)
    assert out[0].rank == -21.0


def test_city_boost_empty_city_is_identity() -> None:
    results = [_mk("a", -1.0, city_prices=[{"city": "Madrid"}])]
    out = city_boost("")(results)
    assert out[0].rank == -1.0


def test_city_boost_returns_sorted_output() -> None:
    results = [
        _mk("a", -1.0, city_prices=[{"city": "Madrid"}]),
        _mk("b", -2.0, city_prices=[]),
    ]
    out = city_boost("Madrid")(results)
    assert [r.doc_id for r in out] == ["a", "b"]


def test_city_boost_does_not_mutate_inputs() -> None:
    original = _mk("a", -1.0, city_prices=[{"city": "Madrid"}])
    _ = city_boost("Madrid")([original])
    assert original.rank == -1.0


def test_chain_reranks_composes_left_to_right() -> None:
    def add_one(rs: list[SearchResult]) -> list[SearchResult]:
        from dataclasses import replace as _r

        return [_r(r, rank=r.rank + 1) for r in rs]

    def add_ten(rs: list[SearchResult]) -> list[SearchResult]:
        from dataclasses import replace as _r

        return [_r(r, rank=r.rank + 10) for r in rs]

    out = chain_reranks(add_one, add_ten)([_mk("a", 0.0)])
    assert out[0].rank == 11.0


def test_chain_reranks_empty_is_identity() -> None:
    rs = [_mk("a", -1.0)]
    out = chain_reranks()(rs)
    assert out == rs
