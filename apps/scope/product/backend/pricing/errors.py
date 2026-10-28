"""Custom exceptions for :mod:`pricing`.

Narrow hierarchy. ``PricingError`` subclasses ``core.errors.AppError`` so
FastAPI's global handler produces ``{"ok": false, "error": ..., "code": ...}``
JSON without an adapter. Status codes mirror the semantics:

- ``IndexNotFoundError``: 503 (service unavailable — configured DB is missing).
- ``QueryEmptyError``, ``IVAConventionError``, ``MarkupLookupError``: 422
  (validation-style — the input is malformed).
"""

from __future__ import annotations

from core.errors import AppError


class PricingError(AppError):
    """Base class for every error the :mod:`pricing` package raises.

    Subclasses ``core.errors.AppError`` (see `design.md` D20) so the
    FastAPI global handler returns ``{"ok": false, ...}`` without an
    extra adapter.
    """

    status = 422
    default_code = "PRICING_ERROR"


class IndexNotFoundError(PricingError):
    """Raised when a configured on-disk index is missing or unreadable.

    Translated to HTTP 503 — the DB file is not where the package
    expected and the caller should retry after redeploy or data refresh.
    """

    status = 503
    default_code = "INDEX_NOT_FOUND"


class QueryEmptyError(PricingError):
    """Raised when a search/estimate function is called with an empty
    or whitespace-only query string."""

    status = 422
    default_code = "QUERY_EMPTY"


class IVAConventionError(PricingError):
    """Raised when IVA inputs are ambiguous or out-of-range.

    Triggered when:
      - both ``iva_rate`` (fraction) and ``iva_percent`` (integer) are given,
      - ``iva_rate`` is outside ``[0, 1]``,
      - ``iva_percent`` is outside ``[0, 100]``.
    """

    status = 422
    default_code = "IVA_CONVENTION"


class MarkupLookupError(PricingError):
    """Raised when a markup chapter lookup explicitly fails (vs. falling back)."""

    status = 422
    default_code = "MARKUP_LOOKUP"


__all__ = [
    "PricingError",
    "IndexNotFoundError",
    "QueryEmptyError",
    "IVAConventionError",
    "MarkupLookupError",
]
