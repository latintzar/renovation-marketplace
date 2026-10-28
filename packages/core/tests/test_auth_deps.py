"""Tests for :mod:`core.auth.deps`."""

from __future__ import annotations

import httpx
import pytest
import respx

from core import Forbidden, Unauthorized
from core.auth.deps import (
    optional_auth,
    require_auth,
    require_contractor,
    require_homeowner,
)
from core.auth.jwt import clear_jwt_cache
from core.db import sb_auth_url, sb_url


async def _mock_authenticated_user(
    rx: respx.MockRouter, user_id: str, email: str, contractor_id: str | None
) -> None:
    rx.get("/user").mock(
        return_value=httpx.Response(
            200, json={"id": user_id, "email": email}
        )
    )


@pytest.mark.asyncio
async def test_require_auth_missing_header_raises() -> None:
    with pytest.raises(Unauthorized):
        await require_auth(authorization=None)


@pytest.mark.asyncio
async def test_require_auth_non_bearer_raises() -> None:
    with pytest.raises(Unauthorized):
        await require_auth(authorization="Basic xxx")


@pytest.mark.asyncio
async def test_require_auth_invalid_jwt_raises(supabase_env: None) -> None:
    clear_jwt_cache()
    async with respx.mock(base_url=sb_auth_url()) as rx:
        rx.get("/user").mock(return_value=httpx.Response(401))
        with pytest.raises(Unauthorized):
            await require_auth(authorization="Bearer bad")


@pytest.mark.asyncio
async def test_require_auth_homeowner_flow(supabase_env: None) -> None:
    """No claimed contractor row → role=homeowner."""
    clear_jwt_cache()
    async with respx.mock() as rx:
        rx.get(f"{sb_auth_url()}/user").mock(
            return_value=httpx.Response(
                200, json={"id": "u1", "email": "h@example.com"}
            )
        )
        rx.get(f"{sb_url()}/contractors").mock(
            return_value=httpx.Response(200, json=[])
        )
        user = await require_auth(authorization="Bearer ok")
    assert user.id == "u1"
    assert user.email == "h@example.com"
    assert user.role == "homeowner"
    assert user.contractor_id is None


@pytest.mark.asyncio
async def test_require_auth_contractor_flow(supabase_env: None) -> None:
    """Claimed contractor row exists → role=contractor + contractor_id set."""
    clear_jwt_cache()
    async with respx.mock() as rx:
        rx.get(f"{sb_auth_url()}/user").mock(
            return_value=httpx.Response(
                200, json={"id": "u1", "email": "c@example.com"}
            )
        )
        rx.get(f"{sb_url()}/contractors").mock(
            return_value=httpx.Response(200, json=[{"id": "contractor-123"}])
        )
        user = await require_auth(authorization="Bearer ok")
    assert user.role == "contractor"
    assert user.contractor_id == "contractor-123"


@pytest.mark.asyncio
async def test_require_auth_missing_email_raises(supabase_env: None) -> None:
    clear_jwt_cache()
    async with respx.mock(base_url=sb_auth_url()) as rx:
        rx.get("/user").mock(
            return_value=httpx.Response(200, json={"id": "u1", "email": ""})
        )
        with pytest.raises(Unauthorized) as info:
            await require_auth(authorization="Bearer ok")
    assert info.value.code == "JWT_NO_EMAIL"


@pytest.mark.asyncio
async def test_optional_auth_returns_none_without_header() -> None:
    assert await optional_auth(authorization=None) is None


@pytest.mark.asyncio
async def test_optional_auth_returns_none_on_invalid(supabase_env: None) -> None:
    clear_jwt_cache()
    async with respx.mock(base_url=sb_auth_url()) as rx:
        rx.get("/user").mock(return_value=httpx.Response(401))
        assert await optional_auth(authorization="Bearer bad") is None


@pytest.mark.asyncio
async def test_optional_auth_returns_user_on_valid(
    supabase_env: None,
) -> None:
    clear_jwt_cache()
    async with respx.mock() as rx:
        rx.get(f"{sb_auth_url()}/user").mock(
            return_value=httpx.Response(
                200, json={"id": "u1", "email": "x@y.com"}
            )
        )
        rx.get(f"{sb_url()}/contractors").mock(
            return_value=httpx.Response(200, json=[])
        )
        user = await optional_auth(authorization="Bearer ok")
    assert user is not None
    assert user.role == "homeowner"


@pytest.mark.asyncio
async def test_require_contractor_forbids_homeowner(
    supabase_env: None,
) -> None:
    clear_jwt_cache()
    async with respx.mock() as rx:
        rx.get(f"{sb_auth_url()}/user").mock(
            return_value=httpx.Response(
                200, json={"id": "u1", "email": "h@y.com"}
            )
        )
        rx.get(f"{sb_url()}/contractors").mock(
            return_value=httpx.Response(200, json=[])
        )
        with pytest.raises(Forbidden) as info:
            await require_contractor(authorization="Bearer ok")
    assert info.value.code == "ROLE_NOT_CONTRACTOR"


@pytest.mark.asyncio
async def test_require_homeowner_forbids_contractor(
    supabase_env: None,
) -> None:
    clear_jwt_cache()
    async with respx.mock() as rx:
        rx.get(f"{sb_auth_url()}/user").mock(
            return_value=httpx.Response(
                200, json={"id": "u1", "email": "c@y.com"}
            )
        )
        rx.get(f"{sb_url()}/contractors").mock(
            return_value=httpx.Response(200, json=[{"id": "contractor-1"}])
        )
        with pytest.raises(Forbidden) as info:
            await require_homeowner(authorization="Bearer ok")
    assert info.value.code == "ROLE_NOT_HOMEOWNER"
