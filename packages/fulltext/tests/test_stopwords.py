"""Unit tests for :mod:`fulltext.stopwords`."""
from __future__ import annotations

from fulltext import ENGLISH_GENERAL, SPANISH_GENERAL


def test_both_pools_are_frozensets() -> None:
    assert isinstance(SPANISH_GENERAL, frozenset)
    assert isinstance(ENGLISH_GENERAL, frozenset)


def test_pools_are_disjoint_enough() -> None:
    overlap = SPANISH_GENERAL & ENGLISH_GENERAL
    assert len(overlap) < 5


def test_spanish_core_stopwords_present() -> None:
    for w in ("de", "el", "la", "que", "por", "con", "para"):
        assert w in SPANISH_GENERAL


def test_english_core_stopwords_present() -> None:
    for w in ("the", "a", "is", "of", "with", "for"):
        assert w in ENGLISH_GENERAL


def test_pools_do_not_contain_domain_noise() -> None:
    """Domain-specific filler (precio, presupuesto, cype) lives in
    the consumer package, not here."""
    for w in ("precio", "presupuesto", "cype", "coste"):
        assert w not in SPANISH_GENERAL
        assert w not in ENGLISH_GENERAL
