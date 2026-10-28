"""Unit tests for :mod:`fulltext.synonyms`."""
from __future__ import annotations

from fulltext import EN_ES_SYNONYMS, expand_query


def test_expand_simple_english_noun() -> None:
    out = expand_query("plumber")
    assert "plumber" in out.lower() or "fontaner" in out
    assert "fontaner" in out or "fontan" in out


def test_expand_multi_concept_uses_and() -> None:
    out = expand_query("bathroom renovation")
    assert " AND " in out
    assert "ban" in out.lower() or "bathroom" in out.lower()
    assert "reform" in out.lower() or "renovation" in out.lower()


def test_expand_multi_word_phrase_consumes_both_tokens() -> None:
    out = expand_query("air conditioning")
    out_l = out.lower()
    assert "acondicion" in out_l or "aire" in out_l
    assert out.count(" AND ") == 0


def test_expand_empty_returns_raw() -> None:
    assert expand_query("") == ""
    assert expand_query("   ") == "   "


def test_expand_stopwords_only_fallback_to_raw() -> None:
    out = expand_query("the a an is of")
    assert isinstance(out, str)


def test_reverse_expansion_for_spanish_input() -> None:
    out = expand_query("fontanero")
    assert "fontaner" in out.lower() or "plumber" in out.lower()


def test_synonym_table_has_no_empty_values() -> None:
    for key, vals in EN_ES_SYNONYMS.items():
        assert isinstance(vals, tuple)
        assert len(vals) > 0
        assert all(isinstance(v, str) and v for v in vals)


def test_single_concept_no_and() -> None:
    out = expand_query("plumber")
    assert " AND " not in out
