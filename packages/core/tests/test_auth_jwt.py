"""Tests for :mod:`core.auth.jwt`.

Safety-critical: the JWT cache must not leak identity across users.
Coverage target: 100%.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from core.auth.jwt import (
    _JWT_CACHE,
    clear_jwt_cache,
    verify_supabase_jwt,
)
from core.db import sb_auth_url


@pytest.mark.asyncio
async def test_verify_jwt_hits_supabase_on_miss(supabase_env: None) -> None:
    payload = {"id": "user-1", "email": "x@example.com"}
    async with respx.mock(base_url=sb_auth_url()) as rx:
        rx.get("/user").mock(return_value=httpx.Response(200, json=payload))
        got = await verify_supabase_jwt("jwt-1")
    assert got == payload


@pytest.mark.asyncio
async def test_verify_jwt_caches_payload(supabase_env: None) -> None:
    clear_jwt_cache()
    payload = {"id": "user-1", "email": "x@example.com"}
    async with respx.mock(base_url=sb_auth_url()) as rx:
        route = rx.get("/user").mock(
            return_value=httpx.Response(200, json=payload)
        )
        await verify_supabase_jwt("jwt-cached")
        # Second call hits cache, not the network.
        await verify_supabase_jwt("jwt-cached")
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_verify_jwt_cache_kill_switch(
    supabase_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``LEO_DISABLE_JWT_CACHE=true`` bypasses the cache."""
    monkeypatch.setenv("LEO_DISABLE_JWT_CACHE", "true")
    clear_jwt_cache()
    payload = {"id": "user-1", "email": "x@example.com"}
    async with respx.mock(base_url=sb_auth_url()) as rx:
        route = rx.get("/user").mock(
            return_value=httpx.Response(200, json=payload)
        )
        await verify_supabase_jwt("jwt-a")
        await verify_supabase_jwt("jwt-a")
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_verify_jwt_returns_none_on_401(supabase_env: None) -> None:
    async with respx.mock(base_url=sb_auth_url()) as rx:
        rx.get("/user").mock(return_value=httpx.Response(401))
        assert await verify_supabase_jwt("bad") is None


@pytest.mark.asyncio
async def test_verify_jwt_returns_none_on_network_error(
    supabase_env: None,
) -> None:
    async with respx.mock(base_url=sb_auth_url()) as rx:
        rx.get("/user").mock(side_effect=httpx.ConnectError("boom"))
        assert await verify_supabase_jwt("x") is None


@pytest.mark.asyncio
async def test_different_tokens_have_independent_cache_entries(
    supabase_env: None,
) -> None:
    """A cached payload for jwt-A must NOT be served to jwt-B."""
    clear_jwt_cache()
    async with respx.mock(base_url=sb_auth_url()) as rx:
        rx.get("/user").mock(
            side_effect=[
                httpx.Response(200, json={"id": "user-A", "email": "a@x"}),
                httpx.Response(200, json={"id": "user-B", "email": "b@x"}),
            ]
        )
        a1 = await verify_supabase_jwt("token-A")
        a2 = await verify_supabase_jwt("token-A")  # cache hit
        b1 = await verify_supabase_jwt("token-B")
    assert a1 == a2
    assert a1 != b1
    assert b1["id"] == "user-B"


def test_clear_jwt_cache_drops_entries() -> None:
    _JWT_CACHE.set("x", {"id": "u"})
    clear_jwt_cache()
    assert _JWT_CACHE.get("x") is None


def test_cache_ttl_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entries older than TTL are not served."""
    from core.auth import jwt as jwt_mod

    fake_now = [100.0]

    def fake_mono() -> float:
        return fake_now[0]

    monkeypatch.setattr(jwt_mod.time, "monotonic", fake_mono)
    cache = jwt_mod._JwtCache(maxsize=10, ttl=1.0)

    cache.set("k", {"id": "u"})
    assert cache.get("k") == {"id": "u"}
    fake_now[0] = 101.5  # past TTL
    assert cache.get("k") is None


def test_cache_lru_eviction(monkeypatch: pytest.MonkeyPatch) -> None:
    """Capacity-over-fill evicts the oldest entry first."""
    from core.auth import jwt as jwt_mod

    cache = jwt_mod._JwtCache(maxsize=2, ttl=3600.0)
    cache.set("a", {"id": "A"})
    cache.set("b", {"id": "B"})
    cache.set("c", {"id": "C"})  # evicts a

    assert cache.get("a") is None
    assert cache.get("b") == {"id": "B"}
    assert cache.get("c") == {"id": "C"}
