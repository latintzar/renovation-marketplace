"""Tests for :mod:`core.http`."""

from __future__ import annotations

import httpx
import pytest
import respx

from core import http_client, http_client_sync, sb_request


@pytest.mark.asyncio
async def test_http_client_connect_timeout_capped_at_10s() -> None:
    """Invariant: connect = min(timeout, 10.0) no matter how big timeout is."""
    async with http_client(timeout=30) as client:
        assert client.timeout.read == 30
        assert client.timeout.connect == 10.0


@pytest.mark.asyncio
async def test_http_client_connect_matches_timeout_when_small() -> None:
    async with http_client(timeout=5) as client:
        assert client.timeout.connect == 5.0


@pytest.mark.asyncio
async def test_http_client_follow_redirects_false_by_default() -> None:
    """Invariant: follow_redirects=False default."""
    async with http_client() as client:
        assert client.follow_redirects is False


@pytest.mark.asyncio
async def test_http_client_follow_redirects_override() -> None:
    """Callers can opt in to redirects."""
    async with http_client(follow_redirects=True) as client:
        assert client.follow_redirects is True


@pytest.mark.asyncio
async def test_http_client_makes_real_request() -> None:
    """End-to-end: the yielded client actually makes requests."""
    async with respx.mock(base_url="https://api.example.com") as rx:
        rx.get("/ping").mock(return_value=httpx.Response(200, text="pong"))
        async with http_client() as client:
            resp = await client.get("https://api.example.com/ping")
            assert resp.text == "pong"


@pytest.mark.asyncio
async def test_sb_request_uses_supabase_base_url(supabase_env: None) -> None:
    """Invariant: sb_request base_url is the Supabase host root (no /rest/v1)."""
    async with sb_request() as client:
        assert str(client.base_url) == "https://example.supabase.co"


@pytest.mark.asyncio
async def test_sb_request_carries_sb_headers(supabase_env: None) -> None:
    async with sb_request() as client:
        assert client.headers["apikey"] == "test-service-key"
        assert client.headers["authorization"] == "Bearer test-service-key"


def test_http_client_sync_respects_timeout() -> None:
    with http_client_sync(timeout=20) as client:
        assert client.timeout.read == 20
        assert client.timeout.connect == 10.0


def test_http_client_sync_follow_redirects_override() -> None:
    with http_client_sync(follow_redirects=True) as client:
        assert client.follow_redirects is True
