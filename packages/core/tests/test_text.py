"""Unit tests for ``domain.text``."""

from __future__ import annotations

import pytest

from core.text import normalize_spanish, slugify, strip_accents


class TestStripAccents:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Málaga", "Malaga"),
            ("ñ", "n"),
            ("coração", "coracao"),
            ("über", "uber"),
            ("niño", "nino"),
            ("", ""),
            ("plain", "plain"),
        ],
    )
    def test_roundtrip(self, raw: str, expected: str) -> None:
        assert strip_accents(raw) == expected

    def test_preserves_spacing(self) -> None:
        assert strip_accents("Málaga Centro") == "Malaga Centro"

    def test_mixed_case_unchanged(self) -> None:
        assert strip_accents("ÁrEas") == "ArEas"


class TestNormalizeSpanish:
    def test_lowercase_by_default(self) -> None:
        assert normalize_spanish("ÁRE AS  Comunes") == "are as comunes"

    def test_lower_false_preserves_case(self) -> None:
        assert normalize_spanish("Bilbao Centro", lower=False) == "Bilbao Centro"

    def test_collapse_whitespace(self) -> None:
        assert normalize_spanish("a\t\n  b") == "a b"

    def test_trims(self) -> None:
        assert normalize_spanish("   ñandu   ") == "nandu"

    def test_empty(self) -> None:
        assert normalize_spanish("") == ""

    def test_tabs_and_newlines(self) -> None:
        assert normalize_spanish("a\tb\nc") == "a b c"

    def test_multiple_runs_of_whitespace_collapsed(self) -> None:
        assert normalize_spanish("a          b") == "a b"


class TestSlugify:
    def test_basic_slug(self) -> None:
        assert slugify("Áreas comunes") == "areas-comunes"

    def test_strips_punctuation(self) -> None:
        assert slugify("¡Hola, mundo!") == "hola-mundo"

    def test_alternative_separator(self) -> None:
        assert slugify("Áreas comunes", sep="_") == "areas_comunes"

    def test_empty(self) -> None:
        assert slugify("") == ""

    def test_only_punctuation(self) -> None:
        assert slugify("!@#$%") == ""

    def test_leading_trailing_separators_stripped(self) -> None:
        assert slugify("!hola!") == "hola"

    def test_preserves_digits(self) -> None:
        assert slugify("Piso 3 Izq") == "piso-3-izq"

    def test_collapses_multiple_separators(self) -> None:
        assert slugify("a   b") == "a-b"

    def test_ñ_becomes_n(self) -> None:
        assert slugify("niño bueno") == "nino-bueno"
