"""Unit tests for `documents.dates` — locale-aware formatting."""
from __future__ import annotations

from datetime import date

from documents import format_date, format_date_es


def test_format_date_es_long_form() -> None:
    assert format_date_es(date(2026, 4, 18)) == "18 de abril de 2026"


def test_format_date_es_different_month() -> None:
    assert format_date_es(date(2025, 1, 3)) == "3 de enero de 2025"


def test_format_date_generic_es() -> None:
    assert format_date(date(2026, 4, 18), locale="es") == "18 de abril de 2026"


def test_format_date_generic_en() -> None:
    s = format_date(date(2026, 4, 18), locale="en")
    assert "2026" in s
    assert "18" in s or "April" in s
