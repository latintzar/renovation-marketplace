"""Unit tests for :class:`fulltext.SearchResult`."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from fulltext import SearchResult


def test_search_result_is_frozen() -> None:
    r = SearchResult(doc_id="x", rank=-1.0, title="T")
    with pytest.raises(FrozenInstanceError):
        r.rank = -2.0  # type: ignore[misc]


def test_defaults() -> None:
    r = SearchResult(doc_id="x", rank=0.0)
    assert r.slug == ""
    assert r.title == ""
    assert r.body == ""
    assert r.meta == {}


def test_each_instance_gets_fresh_meta_dict() -> None:
    a = SearchResult(doc_id="a", rank=0.0)
    b = SearchResult(doc_id="b", rank=0.0)
    a.meta["x"] = 1
    assert "x" not in b.meta


def test_replace_creates_new_instance() -> None:
    r = SearchResult(doc_id="a", rank=-5.0, title="T")
    r2 = replace(r, rank=-10.0)
    assert r.rank == -5.0
    assert r2.rank == -10.0
    assert r2.doc_id == "a"
