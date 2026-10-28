"""Unit tests for :mod:`fulltext.tokenizer`.

The tokenizer is the single source of truth for normalisation;
index-time and query-time both flow through it, so drift here breaks
recall everywhere. Behaviours under test:

* Lowercasing.
* Accent stripping (delegates to :mod:`core.text`).
* Stopword removal (default and custom).
* ``min_len`` cutoff.
* Deterministic Spanish stemming.
"""
from __future__ import annotations

from fulltext import stem_word, tokenize


def test_lowercases_input() -> None:
    out = tokenize("Fontanero MADRID")
    assert all(tok == tok.lower() for tok in out)


def test_strips_accents() -> None:
    out = tokenize("fontanería")
    assert "fontaneria" == stem_word("fontaneria") or out[0].startswith("fontan")
    for tok in out:
        assert "í" not in tok
        assert "á" not in tok


def test_drops_default_stopwords() -> None:
    assert tokenize("el que un una los las") == []


def test_respects_custom_stopwords() -> None:
    out = tokenize("fontanero madrid", stopwords={"madrid"})
    stems = set(out)
    assert "madrid" not in stems
    assert len(out) == 1


def test_min_len_filter() -> None:
    assert tokenize("a de hola mundo", min_len=4) == [stem_word("hola"), stem_word("mundo")]


def test_stems_spanish_inflections() -> None:
    forms = [
        tokenize("fontanero"),
        tokenize("fontanera"),
        tokenize("fontaneros"),
    ]
    stems = {f[0] for f in forms}
    assert len(stems) == 1


def test_empty_returns_empty_list() -> None:
    assert tokenize("") == []
    assert tokenize("   ") == []


def test_stem_word_is_deterministic() -> None:
    assert stem_word("fontaneria") == stem_word("fontaneria")
    assert stem_word("reforma") == stem_word("reforma")


def test_stem_word_monotonic_on_shorter_stems() -> None:
    """Snowball isn't strictly idempotent (``fontaner`` → ``fontan`` →
    ``font``), but applying it twice never *grows* the string."""
    once = stem_word("fontanero")
    twice = stem_word(once)
    assert len(twice) <= len(once)
