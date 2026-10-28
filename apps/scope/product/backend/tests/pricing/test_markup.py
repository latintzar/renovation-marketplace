"""Tests for :mod:`pricing.markup`."""
from __future__ import annotations

from pricing import DEFAULT_MARKUP_BY_CHAPTER, FALLBACK_MARKUP, markup_for_chapter
from pricing.markup import material_fraction_for_chapter


class TestMarkupForChapter:
    def test_known_chapter_returns_configured(self) -> None:
        m = markup_for_chapter("Instalaciones")
        assert m.min >= 1.0
        assert m.mid >= m.min
        assert m.max >= m.mid

    def test_unknown_falls_back(self) -> None:
        m = markup_for_chapter("Not_a_real_chapter")
        assert m == FALLBACK_MARKUP

    def test_empty_string_falls_back(self) -> None:
        m = markup_for_chapter("")
        assert m == FALLBACK_MARKUP

    def test_none_falls_back(self) -> None:
        m = markup_for_chapter(None)  # type: ignore[arg-type]
        assert m == FALLBACK_MARKUP


class TestMaterialFractionForChapter:
    def test_known_chapter(self) -> None:
        frac = material_fraction_for_chapter("Instalaciones")
        assert 0 <= frac <= 1.0

    def test_unknown_default(self) -> None:
        frac = material_fraction_for_chapter("Not_a_chapter")
        assert 0 <= frac <= 1.0


def test_default_markup_table_nonempty() -> None:
    assert len(DEFAULT_MARKUP_BY_CHAPTER) > 0


def test_markup_monotonic_min_mid_max() -> None:
    for chapter, entry in DEFAULT_MARKUP_BY_CHAPTER.items():
        assert entry.min <= entry.mid <= entry.max, f"bad ordering in {chapter}: {entry}"
        assert entry.min >= 1.0, f"{chapter} markup.min must be >=1 (it's cost-of-inputs → retail)"


def test_fallback_markup_reasonable() -> None:
    assert FALLBACK_MARKUP.min >= 1.0
    assert FALLBACK_MARKUP.min <= FALLBACK_MARKUP.mid <= FALLBACK_MARKUP.max
