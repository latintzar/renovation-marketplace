"""Tests for :mod:`pricing.ine_drift`."""
from __future__ import annotations

from pricing import compute_ine_material_drift
from pricing.ine_drift import load_ine_index


def test_load_ine_index_nonempty() -> None:
    idx = load_ine_index()
    assert isinstance(idx, dict)
    assert len(idx) > 0


def test_known_categories_present() -> None:
    idx = load_ine_index()
    assert "ceramica" in idx
    assert "plasticos" in idx
    assert "madera" in idx


def test_known_category_has_history_structure() -> None:
    idx = load_ine_index()
    cat = idx["ceramica"]
    assert "history" in cat
    assert isinstance(cat["history"], list)
    for entry in cat["history"]:
        assert "index" in entry or entry is None


def test_drift_multiplier_in_capped_range() -> None:
    """All categories must produce a multiplier in [0.85, 1.15]."""

    for slug in ["ceramica", "plasticos", "cobre", "acero", "madera", "cemento",
                 "ligantes", "vidrio", "aluminio"]:
        m = compute_ine_material_drift(slug)
        assert 0.85 <= m <= 1.15, f"{slug} drift {m} out of cap"


def test_unknown_category_returns_1() -> None:
    assert compute_ine_material_drift("nonsense_category") == 1.0


def test_empty_slug_returns_1() -> None:
    assert compute_ine_material_drift("") == 1.0


def test_drift_is_float() -> None:
    m = compute_ine_material_drift("ceramica")
    assert isinstance(m, float)
