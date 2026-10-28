"""Unit tests for :mod:`scrapers.habitissimo` pure helpers.

The network-dependent pieces (``refresh_session``, ``reveal_phone``,
``submit_rfq``) are scaffolded with :class:`NotImplementedError`.
We assert the raise-contract so Phase 5 can't accidentally ship a
no-op.

Pure helpers covered here: phone-modal extraction,
:func:`build_submissions` cartesian, constants.
"""
from __future__ import annotations

import pytest

from scrapers.habitissimo import (
    AJAX_JS,
    HABITISSIMO_PROXY_PREFIX,
    HABITISSIMO_SESSION_FILE,
    HABITISSIMO_SESSION_TTL,
    build_submissions,
    refresh_session,
    reveal_phone,
    submit_rfq,
)
from scrapers.habitissimo.phones import extract_phone_from_modal_html


def test_proxy_prefix_is_911() -> None:
    assert HABITISSIMO_PROXY_PREFIX == "911"


def test_session_file_is_path() -> None:
    assert str(HABITISSIMO_SESSION_FILE).endswith("habitissimo_session.json")


def test_session_ttl_corrected_to_90_min() -> None:
    """Audit §1.7 I2: TTL was 5 h, now 90 min."""

    assert HABITISSIMO_SESSION_TTL == 5400.0


def test_ajax_js_has_slug_placeholder() -> None:
    assert "{slug}" in AJAX_JS


def test_extract_phone_from_tel_anchor() -> None:
    html = '<a href="tel:+34 612 345 678">call</a>'
    assert extract_phone_from_modal_html(html) == "+34612345678"


def test_extract_phone_from_data_attr() -> None:
    html = '<span data-phone="612 345 678">revealed</span>'
    assert extract_phone_from_modal_html(html) == "612345678"


def test_extract_phone_from_regex_fallback() -> None:
    html = "<div>Our line is +34 911 200 300 (real)</div>"
    phone = extract_phone_from_modal_html(html)
    assert phone is None  # 911 → proxy band → filtered


def test_extract_phone_filters_proxy_prefix() -> None:
    html = '<a href="tel:+34911200300">revealed</a>'
    assert extract_phone_from_modal_html(html) is None


def test_extract_phone_filters_proxy_prefix_with_leading_34() -> None:
    html = '<a href="tel:34911200300">revealed</a>'
    assert extract_phone_from_modal_html(html) is None


def test_extract_phone_empty_returns_none() -> None:
    assert extract_phone_from_modal_html("") is None
    assert extract_phone_from_modal_html("<html><body>no phones here</body></html>") is None


def test_build_submissions_cartesian_product() -> None:
    out = build_submissions(
        trades=["fontaneros", "electricistas"],
        cities=["madrid", "barcelona", "valencia"],
        templates=["Hola, necesito presupuesto"],
    )
    assert len(out) == 6
    assert {(o["trade"], o["city"]) for o in out} == {
        ("fontaneros", "madrid"),
        ("fontaneros", "barcelona"),
        ("fontaneros", "valencia"),
        ("electricistas", "madrid"),
        ("electricistas", "barcelona"),
        ("electricistas", "valencia"),
    }


def test_build_submissions_rotates_templates() -> None:
    out = build_submissions(
        trades=["t1", "t2"],
        cities=["c1", "c2"],
        templates=["a", "b", "c"],
    )
    messages = [o["message"] for o in out]
    assert "a" in messages and "b" in messages


def test_build_submissions_empty_inputs_return_empty() -> None:
    assert build_submissions([], ["c"], ["t"]) == []
    assert build_submissions(["t"], [], ["t"]) == []
    assert build_submissions(["t"], ["c"], []) == []


@pytest.mark.asyncio
async def test_refresh_session_is_scaffolded() -> None:
    with pytest.raises(NotImplementedError):
        await refresh_session()


@pytest.mark.asyncio
async def test_reveal_phone_is_scaffolded() -> None:
    with pytest.raises(NotImplementedError):
        await reveal_phone("slug")


@pytest.mark.asyncio
async def test_submit_rfq_is_scaffolded() -> None:
    with pytest.raises(NotImplementedError):
        await submit_rfq("t", "c", message="m")
