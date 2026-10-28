"""Tests for :mod:`pricing.overhead`."""
from __future__ import annotations

from pricing import overhead_model
from pricing.overhead import _clear_cache


def test_overhead_model_returns_dict() -> None:
    m = overhead_model()
    assert isinstance(m, dict)
    assert len(m) > 0


def test_overhead_has_expected_top_keys() -> None:
    m = overhead_model()
    # Based on bundled file — at least one of these core sections
    expected_any = {"_meta", "scenario", "annual_overheads_eur", "totals"}
    assert expected_any & set(m.keys()), f"no expected keys in {set(m.keys())}"


def test_overhead_model_is_cached() -> None:
    """Two consecutive calls should return the SAME dict object."""

    a = overhead_model()
    b = overhead_model()
    assert a is b


def test_clear_cache_resets() -> None:
    a = overhead_model()
    _clear_cache()
    b = overhead_model()
    # After cache invalidation, new instance
    assert a is not b
