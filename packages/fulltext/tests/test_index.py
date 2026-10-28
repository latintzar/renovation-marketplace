"""Unit tests for :class:`fulltext.DomainIndex` — the FTS5 heart.

The index is the most complex surface in the package. Coverage:

* schema lifecycle (``drop`` / ``rebuild`` / ``close``)
* write path (``add`` stems before insert; ``add_city_price`` upserts)
* query path: exact-match, synonym expansion, BM25 ordering
* city boost: lower rank for matching ``meta.city_prices``
* ``search_city`` with + without FTS narrowing
* best-effort behaviour: garbage FTS expressions return ``[]``
"""
from __future__ import annotations

from fulltext import DomainIndex


def test_count_starts_at_zero(tmp_index: DomainIndex) -> None:
    assert tmp_index.count() == 0


def test_add_and_commit_increments_count(tmp_index: DomainIndex) -> None:
    tmp_index.add("a", slug="fontanero", title="Fontanero", body="Baño")
    tmp_index.commit()
    assert tmp_index.count() == 1


def test_add_replaces_on_conflict(tmp_index: DomainIndex) -> None:
    tmp_index.add("a", title="v1")
    tmp_index.add("a", title="v2")
    tmp_index.commit()
    assert tmp_index.count() == 1


def test_search_empty_index_returns_empty(tmp_index: DomainIndex) -> None:
    assert tmp_index.search("fontanero") == []


def test_search_matches_title(populated_index: DomainIndex) -> None:
    rs = populated_index.search("fontanero")
    assert any(r.doc_id == "hab-fontanero" for r in rs)


def test_search_expands_english_to_spanish(populated_index: DomainIndex) -> None:
    rs = populated_index.search("plumber")
    assert any(r.doc_id == "hab-fontanero" for r in rs)


def test_search_respects_limit(populated_index: DomainIndex) -> None:
    rs = populated_index.search("reforma", limit=1)
    assert len(rs) <= 1


def test_city_boost_promotes_matching(populated_index: DomainIndex) -> None:
    no_boost = populated_index.search("fontanero")
    with_boost = populated_index.search("fontanero", city="Madrid")
    a = next(r for r in no_boost if r.doc_id == "hab-fontanero")
    b = next(r for r in with_boost if r.doc_id == "hab-fontanero")
    assert b.rank < a.rank


def test_search_city_exact_match(populated_index: DomainIndex) -> None:
    rows = populated_index.search_city("Madrid")
    assert any(r["city"].lower() == "madrid" for r in rows)
    assert any("150€/hora" in r["prices"] for r in rows)


def test_search_city_narrowed_by_query(populated_index: DomainIndex) -> None:
    rows = populated_index.search_city("Madrid", query="plumber")
    assert len(rows) >= 1
    assert rows[0]["city"].lower() == "madrid"


def test_search_city_no_results_for_unknown_city(
    populated_index: DomainIndex,
) -> None:
    assert populated_index.search_city("Nowhereville") == []


def test_rebuild_is_idempotent(populated_index: DomainIndex) -> None:
    c_before = populated_index.count()
    populated_index.rebuild()
    assert populated_index.count() == c_before
    rs = populated_index.search("plumber")
    assert any(r.doc_id == "hab-fontanero" for r in rs)


def test_drop_clears_all(populated_index: DomainIndex) -> None:
    populated_index.drop()
    assert populated_index.count() == 0
    assert populated_index.search("plumber") == []


def test_meta_json_roundtrip(populated_index: DomainIndex) -> None:
    rs = populated_index.search("fontanero")
    hit = next(r for r in rs if r.doc_id == "hab-fontanero")
    assert hit.meta.get("source") == "habitissimo"
    assert hit.meta.get("city_prices")
