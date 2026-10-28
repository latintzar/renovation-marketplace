"""Tests for :mod:`pricing.stopwords`."""
from __future__ import annotations

from pricing.stopwords import CYPE_FILLERS, PRICE_FILLERS


def test_cype_fillers_are_a_set() -> None:
    assert isinstance(CYPE_FILLERS, (set, frozenset))
    assert len(CYPE_FILLERS) > 10


def test_cype_fillers_contains_known_filler() -> None:
    assert "colocado" in CYPE_FILLERS or "colocada" in CYPE_FILLERS


def test_price_fillers_are_a_set() -> None:
    assert isinstance(PRICE_FILLERS, (set, frozenset))


def test_cype_fillers_all_lowercase() -> None:
    for w in CYPE_FILLERS:
        assert w == w.lower(), f"CYPE filler not lowercased: {w!r}"


def test_fillers_do_not_overlap_with_domain_words() -> None:
    """Filler words should NEVER include actually-important search terms."""

    important = {"azulejo", "tuberia", "pared", "cocina", "cuarto"}
    assert not (CYPE_FILLERS & important)
    assert not (PRICE_FILLERS & important)
