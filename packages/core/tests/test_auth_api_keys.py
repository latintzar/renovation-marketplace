"""Tests for :mod:`core.auth.api_keys`."""

from __future__ import annotations

import httpx
import pytest
import respx

from core import Unauthorized
from core.auth.api_keys import require_api_key_or_jwt, verify_api_key
from core.auth.jwt import clear_jwt_cache
from core.db import sb_auth_url, sb_url


@pytest.mark.asyncio
async def test_verify_api_key_hits_row_and_fires_patch(
    supabase_env: None,
) -> None:
    row = {
        "id": "k1",
        "name": "ACME",
        "permissions": ["read"],
        "owner_id": "o1",
    }
    async with respx.mock(base_url=sb_url()) as rx:
        rx.get("/api_keys").mock(return_value=httpx.Response(200, json=[row]))
        patch_route = rx.patch("/api_keys").mock(
            return_value=httpx.Response(204)
        )
        got = await verify_api_key("leo_key_acme")
    assert got == row
    assert patch_route.called


@pytest.mark.asyncio
async def test_verify_api_key_returns_none_on_empty_rows(
    supabase_env: None,
) -> None:
    async with respx.mock(base_url=sb_url()) as rx:
        rx.get("/api_keys").mock(return_value=httpx.Response(200, json=[]))
        assert await verify_api_key("leo_key_missing") is None


@pytest.mark.asyncio
async def test_verify_api_key_swallows_network_errors(
    supabase_env: None,
) -> None:
    async with respx.mock(base_url=sb_url()) as rx:
        rx.get("/api_keys").mock(side_effect=httpx.ConnectError("boom"))
        assert await verify_api_key("leo_key_x") is None


@pytest.mark.asyncio
async def test_verify_api_key_patch_failure_does_not_reject(
    supabase_env: None,
) -> None:
    """Invariant: failed last_used_at PATCH must not reject the request."""
    row = {"id": "k2", "name": "X", "permissions": ["read"]}
    async with respx.mock(base_url=sb_url()) as rx:
        rx.get("/api_keys").mock(return_value=httpx.Response(200, json=[row]))
        rx.patch("/api_keys").mock(side_effect=httpx.ConnectError("boom"))
        got = await verify_api_key("leo_key_x")
    assert got == row


@pytest.mark.asyncio
async def test_require_missing_both_raises_unauthorized() -> None:
    with pytest.raises(Unauthorized):
        await require_api_key_or_jwt(authorization=None, x_api_key=None)


@pytest.mark.asyncio
async def test_require_invalid_api_key_format_raises(
    supabase_env: None,
) -> None:
    with pytest.raises(Unauthorized) as info:
        await require_api_key_or_jwt(x_api_key="not_a_leo_key")
    assert info.value.code == "API_KEY_INVALID_FORMAT"


@pytest.mark.asyncio
async def test_require_invalid_api_key_value_raises(
    supabase_env: None,
) -> None:
    async with respx.mock(base_url=sb_url()) as rx:
        rx.get("/api_keys").mock(return_value=httpx.Response(200, json=[]))
        with pytest.raises(Unauthorized) as info:
            await require_api_key_or_jwt(x_api_key="leo_key_bad")
    assert info.value.code == "API_KEY_INVALID"


@pytest.mark.asyncio
async def test_require_api_key_wins_over_jwt(supabase_env: None) -> None:
    """Invariant: API key wins when both are present.

    See ``internal/refactor/packages/core/audit.md`` §auth invariant 5.
    """
    row = {
        "id": "k1",
        "name": "ACME",
        "permissions": ["read"],
        "owner_id": "o1",
    }
    async with respx.mock(base_url=sb_url()) as rx:
        rx.get("/api_keys").mock(return_value=httpx.Response(200, json=[row]))
        rx.patch("/api_keys").mock(return_value=httpx.Response(204))
        got = await require_api_key_or_jwt(
            authorization="Bearer some-jwt", x_api_key="leo_key_acme"
        )
    assert got["type"] == "api_key"
    assert got["key_id"] == "k1"


@pytest.mark.asyncio
async def test_require_jwt_when_no_api_key(supabase_env: None) -> None:
    clear_jwt_cache()
    async with respx.mock(base_url=sb_auth_url()) as rx:
        rx.get("/user").mock(
            return_value=httpx.Response(
                200, json={"id": "user-1", "email": "x@example.com"}
            )
        )
        got = await require_api_key_or_jwt(
            authorization="Bearer jwt-1", x_api_key=None
        )
    assert got == {"type": "jwt", "user_id": "user-1", "email": "x@example.com"}


@pytest.mark.asyncio
async def test_require_jwt_invalid_raises(supabase_env: None) -> None:
    async with respx.mock(base_url=sb_auth_url()) as rx:
        rx.get("/user").mock(return_value=httpx.Response(401))
        with pytest.raises(Unauthorized) as info:
            await require_api_key_or_jwt(
                authorization="Bearer bad", x_api_key=None
            )
    assert info.value.code == "JWT_INVALID"
