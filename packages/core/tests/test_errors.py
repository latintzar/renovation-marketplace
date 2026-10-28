"""Tests for :mod:`core.errors`.

Safety-critical: the response shape is load-bearing for the SPA.
Coverage target: 100%.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from core import (
    AppError,
    Conflict,
    Forbidden,
    NotFound,
    RateLimited,
    Unauthorized,
    ValidationError,
    api_error,
)


def test_app_error_detail_shape_with_code() -> None:
    err = NotFound("Quote not found", code="QUOTE_NOT_FOUND")
    assert err.to_detail() == {
        "ok": False,
        "error": "Quote not found",
        "code": "QUOTE_NOT_FOUND",
    }


def test_app_error_detail_shape_without_code_uses_default() -> None:
    """When code=None, the subclass's default_code is used."""
    err = NotFound("x")
    assert err.to_detail() == {
        "ok": False,
        "error": "x",
        "code": "NOT_FOUND",
    }


def test_app_error_detail_omits_code_when_none() -> None:
    """Only a literal None code (AND no default) omits the key entirely."""

    class Bare(AppError):
        status = 418
        default_code = None

    err = Bare("nope")
    assert err.to_detail() == {"ok": False, "error": "nope"}


def test_app_error_to_http_uses_status() -> None:
    http = Forbidden("no").to_http()
    assert isinstance(http, HTTPException)
    assert http.status_code == 403
    assert http.detail == {
        "ok": False,
        "error": "no",
        "code": "FORBIDDEN",
    }


@pytest.mark.parametrize(
    "cls, status, default_code",
    [
        (NotFound, 404, "NOT_FOUND"),
        (Unauthorized, 401, "UNAUTHORIZED"),
        (Forbidden, 403, "FORBIDDEN"),
        (ValidationError, 422, "VALIDATION"),
        (Conflict, 409, "CONFLICT"),
        (RateLimited, 429, "RATE_LIMITED"),
    ],
)
def test_subclass_status_and_default_code(
    cls: type[AppError], status: int, default_code: str
) -> None:
    err = cls("msg")
    assert err.status == status
    assert err.default_code == default_code
    assert err.code == default_code


def test_subclasses_inherit_from_app_error() -> None:
    for cls in (
        NotFound,
        Unauthorized,
        Forbidden,
        ValidationError,
        Conflict,
        RateLimited,
    ):
        assert issubclass(cls, AppError)


def test_api_error_shape_with_code() -> None:
    http = api_error(404, "missing", code="X")
    assert isinstance(http, HTTPException)
    assert http.status_code == 404
    assert http.detail == {"ok": False, "error": "missing", "code": "X"}


def test_api_error_shape_without_code() -> None:
    http = api_error(500, "boom")
    assert http.status_code == 500
    assert http.detail == {"ok": False, "error": "boom"}


def test_api_error_is_raisable() -> None:
    with pytest.raises(HTTPException) as exc_info:
        raise api_error(403, "nope")
    assert exc_info.value.status_code == 403


def test_app_error_message_accessor() -> None:
    err = Unauthorized("invalid token")
    assert err.message == "invalid token"
    assert str(err) == "invalid token"


def test_app_error_explicit_code_overrides_default() -> None:
    err = ValidationError("x", code="CUSTOM")
    assert err.code == "CUSTOM"
    assert err.to_detail()["code"] == "CUSTOM"
