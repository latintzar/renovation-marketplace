"""Unit tests for :mod:`fulltext.errors` — hierarchy contract."""
from __future__ import annotations

from fulltext import ProviderError, ProviderTimeout, QuotaExceeded, SearchError


def test_provider_error_is_search_error() -> None:
    assert issubclass(ProviderError, SearchError)


def test_quota_exceeded_is_provider_error() -> None:
    assert issubclass(QuotaExceeded, ProviderError)
    assert issubclass(QuotaExceeded, SearchError)


def test_provider_timeout_is_provider_error() -> None:
    assert issubclass(ProviderTimeout, ProviderError)
    assert issubclass(ProviderTimeout, SearchError)


def test_errors_are_exception_subclasses() -> None:
    for cls in (SearchError, ProviderError, QuotaExceeded, ProviderTimeout):
        assert issubclass(cls, Exception)


def test_errors_carry_message() -> None:
    e = QuotaExceeded("brave rate limit")
    assert str(e) == "brave rate limit"
