"""Locale-aware date formatting (Babel).

Replaces ``datetime.strftime("%-d de %B de %Y")`` at
``unmigrated/backend/routes/documents.py:138,184`` — ``%-d`` is
GNU-specific (breaks on macOS/Windows) and ``%B`` depends on the OS
``LC_TIME`` being ``es_ES.UTF-8`` (fragile in slim Docker images).
"""

from __future__ import annotations

from datetime import date

from babel.dates import format_date as _babel_format_date

__all__ = ["format_date_es", "format_date"]


def format_date_es(d: date) -> str:
    """Spanish long-form date. ``date(2026, 4, 18)`` → ``"18 de abril de 2026"``."""

    return _babel_format_date(d, format="long", locale="es_ES")


def format_date(d: date, *, locale: str = "es_ES") -> str:
    """Generic locale-aware ``long`` date formatting. Babel wrapper."""

    return _babel_format_date(d, format="long", locale=locale)
