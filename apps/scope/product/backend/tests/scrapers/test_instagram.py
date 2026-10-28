"""Unit tests for :mod:`scrapers.instagram`."""
from __future__ import annotations

import pytest

from scrapers.instagram import (
    IG_USERNAME_SKIP,
    extract_profile_fields,
    fetch_profile,
    google_search,
    search,
)


def test_ig_username_skip_contains_known_non_accounts() -> None:
    for key in ("explore", "p", "reel", "directory", "api"):
        assert key in IG_USERNAME_SKIP


def test_extract_profile_fields_pulls_json_embed(ig_profile_html: str) -> None:
    fields = extract_profile_fields(ig_profile_html)
    assert fields["username"] == "garciaplomberia"
    assert fields["full_name"] == "Garcia Plomberia Madrid"
    assert "Madrid" in fields["biography"]
    assert fields["external_url"] == "https://garcia-plomberia.es"


def test_extract_profile_fields_extracts_phones(ig_profile_html: str) -> None:
    fields = extract_profile_fields(ig_profile_html)
    phones = fields["phones"]
    joined = " ".join(phones)
    assert "612 345 678" in joined or "910 200 300" in joined


def test_extract_profile_fields_empty_html() -> None:
    fields = extract_profile_fields("")
    assert fields["username"] == ""
    assert fields["phones"] == []


def test_extract_profile_fields_no_matches_returns_empty_phones() -> None:
    fields = extract_profile_fields(
        '<html><script>{"username":"x","biography":"no phones"}</script></html>'
    )
    assert fields["phones"] == []


@pytest.mark.asyncio
async def test_google_search_stub_returns_empty() -> None:
    assert await google_search("fontaneros madrid") == []


@pytest.mark.asyncio
async def test_fetch_profile_stub_returns_none() -> None:
    assert await fetch_profile("someuser") is None


@pytest.mark.asyncio
async def test_search_stub_returns_empty() -> None:
    assert await search("t", "c") == []
