"""Tests for :mod:`core.db`.

Uses ``respx`` to mock the Supabase REST endpoint.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from core import db as db_module
from core import (
    check_supabase_health,
    close_supabase_pool,
    get_supabase,
    sb_auth_url,
    sb_headers,
    sb_key,
    sb_url,
)
from core.db import Supabase


@pytest.fixture(autouse=True)
async def reset_supabase_singleton() -> None:
    """Make each test start from a clean singleton."""
    db_module._client = None
    db_module._supabase = None
    yield
    if db_module._client is not None:
        try:
            await db_module._client.aclose()
        except Exception:
            pass
    db_module._client = None
    db_module._supabase = None


def test_sb_url_builds_rest_base(supabase_env: None) -> None:
    assert sb_url() == "https://example.supabase.co/rest/v1"


def test_sb_auth_url_builds_auth_base(supabase_env: None) -> None:
    assert sb_auth_url() == "https://example.supabase.co/auth/v1"


def test_sb_key_prefers_service_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    assert sb_key() == "service"


def test_sb_key_falls_back_to_anon_when_service_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invariant: sb_key returns anon key when service role is absent.

    Some dev environments run without service role. See
    ``internal/refactor/packages/core/audit.md`` §db invariant 3.
    """
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    assert sb_key() == "anon"


def test_sb_headers_include_prefer_representation(supabase_env: None) -> None:
    """Invariant: every write returns the affected row.

    SPA relies on ``Prefer: return=representation``; dropping it would
    change response bodies on INSERT/UPDATE.
    """
    headers = sb_headers()
    assert headers["apikey"] == "test-service-key"
    assert headers["Authorization"] == "Bearer test-service-key"
    assert headers["Content-Type"] == "application/json"
    assert headers["Prefer"] == "return=representation"


@pytest.mark.asyncio
async def test_get_supabase_returns_singleton(supabase_env: None) -> None:
    a = await get_supabase()
    b = await get_supabase()
    assert a is b
    assert isinstance(a, Supabase)


@pytest.mark.asyncio
async def test_pooled_client_has_300s_read_timeout(
    supabase_env: None,
) -> None:
    """Invariant: 300s read, 30s connect for pooled client.

    Agent runtime can block Supabase waiting for LLM generations.
    See ``internal/refactor/packages/core/audit.md`` §db invariant 1.
    """
    sb = await get_supabase()
    timeout = sb.client.timeout
    assert timeout.read == 300.0
    assert timeout.connect == 30.0


@pytest.mark.asyncio
async def test_close_supabase_pool_resets_singleton(
    supabase_env: None,
) -> None:
    first = await get_supabase()
    await close_supabase_pool()
    second = await get_supabase()
    assert first is not second


@pytest.mark.asyncio
async def test_check_health_200_is_healthy(supabase_env: None) -> None:
    async with respx.mock(base_url=sb_url()) as rx:
        rx.get("/", params={"limit": "0"}).mock(return_value=httpx.Response(200))
        assert await check_supabase_health() is True


@pytest.mark.asyncio
async def test_check_health_404_is_also_healthy(supabase_env: None) -> None:
    """Invariant: 404 at /rest/v1/ is expected (auth worked, no index)."""
    async with respx.mock(base_url=sb_url()) as rx:
        rx.get("/", params={"limit": "0"}).mock(return_value=httpx.Response(404))
        assert await check_supabase_health() is True


@pytest.mark.asyncio
async def test_check_health_swallows_exceptions(supabase_env: None) -> None:
    """Invariant: check_health returns False on any exception."""
    async with respx.mock(base_url=sb_url()) as rx:
        rx.get("/", params={"limit": "0"}).mock(
            side_effect=httpx.ConnectError("boom")
        )
        assert await check_supabase_health() is False


@pytest.mark.asyncio
async def test_supabase_select(supabase_env: None) -> None:
    async with respx.mock(base_url=sb_url()) as rx:
        rx.get("/quotes").mock(
            return_value=httpx.Response(200, json=[{"id": "q1"}])
        )
        sb = await get_supabase()
        rows = await sb.select("quotes", columns="id", limit=1)
        assert rows == [{"id": "q1"}]


@pytest.mark.asyncio
async def test_supabase_insert_returns_inserted_row(
    supabase_env: None,
) -> None:
    async with respx.mock(base_url=sb_url()) as rx:
        route = rx.post("/quotes").mock(
            return_value=httpx.Response(201, json=[{"id": "q1", "amount": 100}])
        )
        sb = await get_supabase()
        row = await sb.insert("quotes", {"amount": 100})
        assert row == {"id": "q1", "amount": 100}
        # Default Prefer header is preserved.
        request = route.calls[0].request
        assert "return=representation" in request.headers.get("prefer", "")


@pytest.mark.asyncio
async def test_supabase_insert_with_minimal_prefer(
    supabase_env: None,
) -> None:
    async with respx.mock(base_url=sb_url()) as rx:
        rx.post("/quotes").mock(return_value=httpx.Response(201, json=None))
        sb = await get_supabase()
        result = await sb.insert(
            "quotes", {"amount": 100}, prefer="return=minimal"
        )
        assert result is None


@pytest.mark.asyncio
async def test_supabase_update_applies_filters(supabase_env: None) -> None:
    async with respx.mock(base_url=sb_url()) as rx:
        route = rx.patch("/quotes").mock(
            return_value=httpx.Response(
                200, json=[{"id": "q1", "status": "paid"}]
            )
        )
        sb = await get_supabase()
        rows = await sb.update(
            "quotes", {"status": "paid"}, filters={"id": "eq.q1"}
        )
        assert rows == [{"id": "q1", "status": "paid"}]
        request = route.calls[0].request
        assert request.url.params["id"] == "eq.q1"


@pytest.mark.asyncio
async def test_supabase_delete_returns_rows(supabase_env: None) -> None:
    async with respx.mock(base_url=sb_url()) as rx:
        rx.delete("/quotes").mock(
            return_value=httpx.Response(200, json=[{"id": "q1"}])
        )
        sb = await get_supabase()
        rows = await sb.delete("quotes", filters={"id": "eq.q1"})
        assert rows == [{"id": "q1"}]


@pytest.mark.asyncio
async def test_supabase_upsert_sets_merge_duplicates_prefer(
    supabase_env: None,
) -> None:
    async with respx.mock(base_url=sb_url()) as rx:
        route = rx.post("/contractors").mock(
            return_value=httpx.Response(201, json=[{"id": "c1"}])
        )
        sb = await get_supabase()
        row = await sb.upsert(
            "contractors", {"id": "c1"}, on_conflict="id"
        )
        assert row == {"id": "c1"}
        request = route.calls[0].request
        assert "resolution=merge-duplicates" in request.headers["prefer"]
        assert request.url.params["on_conflict"] == "id"


@pytest.mark.asyncio
async def test_supabase_request_escape_hatch(supabase_env: None) -> None:
    async with respx.mock(base_url=sb_url()) as rx:
        rx.get("/rpc/compute").mock(
            return_value=httpx.Response(200, json={"answer": 42})
        )
        sb = await get_supabase()
        resp = await sb.request("GET", "rpc/compute")
        assert resp.status_code == 200
        assert resp.json() == {"answer": 42}
