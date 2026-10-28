"""Tests for the :mod:`pricing.errors` hierarchy."""
from __future__ import annotations

import pytest

from pricing import (
    IVAConventionError,
    IndexNotFoundError,
    MarkupLookupError,
    PricingError,
    QueryEmptyError,
)


def test_all_subclass_pricing_error() -> None:
    assert issubclass(IndexNotFoundError, PricingError)
    assert issubclass(QueryEmptyError, PricingError)
    assert issubclass(IVAConventionError, PricingError)
    assert issubclass(MarkupLookupError, PricingError)


def test_pricing_error_subclasses_app_error() -> None:
    """Every pricing error must be catchable via core.errors.AppError."""

    try:
        from core.errors import AppError

        assert issubclass(PricingError, AppError)
    except ImportError:
        pytest.skip("core package not importable in this test env")


def test_raise_and_catch() -> None:
    with pytest.raises(PricingError):
        raise QueryEmptyError("empty")


def test_index_not_found_carries_message() -> None:
    e = IndexNotFoundError("no ine index at /tmp/x")
    assert "ine index" in str(e)


def test_iva_convention_error() -> None:
    with pytest.raises(IVAConventionError, match="iva"):
        raise IVAConventionError("bad iva")
