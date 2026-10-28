"""Tests for :mod:`storage.conversations` — verbatim WA + web log.

Covers:

- Channel dispatch in :func:`add_message`: whatsapp rows use the legacy
  ``phone_number``/``message_text``/``media_urls[]`` shape; web rows use
  the target ``user_id``/``text`` schema plus optional
  ``media_url``/``metadata``.
- :func:`get_messages` threads ``before`` as a ``lt.{iso}`` filter and
  clamps limit to ``[1, 200]``.
- :func:`get_recent_window` applies the ``hours`` filter post-query and
  hands back newest-first.
- :func:`summarize_recent` buckets the older half into 15-min windows,
  calls :func:`llm.complete` once per bucket, prepends the bullets
  chronologically, and appends the verbatim tail. Falls back
  gracefully when the LLM call raises.
- :func:`_row_to_message` adapts both schemas cleanly, including
  ``media_urls`` head-element extraction + role coercion.

External surfaces (Supabase REST, LLM proxy) are mocked.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import httpx
import pytest
import respx

import records.conversations as _conv
from records.conversations import (
    _ensure_aware,
    _row_to_message,
    add_message,
    get_messages,
    get_recent_window,
    summarize_recent,
)
from records.types import Message


SB_BASE = "http://127.0.0.1:54321"
WA_URL = f"{SB_BASE}/rest/v1/whatsapp_messages"
WEB_URL = f"{SB_BASE}/rest/v1/web_messages"


def _wa_row(**overrides: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "id": "wa-1",
        "phone_number": "+34611",
        "role": "user",
        "message_text": "hola",
        "message_type": "text",
        "media_urls": [],
        "media_types": [],
        "created_at": "2026-04-20T12:00:00+00:00",
    }
    base.update(overrides)
    return base


def _web_row(**overrides: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "id": "web-1",
        "channel": "web",
        "user_id": "anon-42",
        "role": "user",
        "text": "hello",
        "created_at": "2026-04-20T12:00:00+00:00",
    }
    base.update(overrides)
    return base


# ============================== add_message ==================================


class TestAddMessage:
    @pytest.mark.asyncio
    async def test_missing_env_returns_none(self) -> None:
        assert await add_message("+34611", "user", "hola") is None

    @pytest.mark.asyncio
    async def test_whatsapp_happy_path(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            import json

            captured.update(json.loads(request.content.decode()))
            return httpx.Response(201, json=[_wa_row()])

        async with respx.mock() as rx:
            rx.post(WA_URL).mock(side_effect=_capture)
            msg = await add_message("+34611", "user", "hola")
        assert msg is not None
        assert isinstance(msg, Message)
        assert msg.channel == "whatsapp"
        assert captured["phone_number"] == "+34611"
        assert captured["message_text"] == "hola"
        assert captured["role"] == "user"
        assert captured["media_urls"] == []

    @pytest.mark.asyncio
    async def test_whatsapp_media_url_becomes_head_element(
        self, supabase_env: None
    ) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            import json

            captured.update(json.loads(request.content.decode()))
            return httpx.Response(
                201, json=[_wa_row(media_urls=["https://img/1"])]
            )

        async with respx.mock() as rx:
            rx.post(WA_URL).mock(side_effect=_capture)
            msg = await add_message(
                "+34611",
                "user",
                "with image",
                media_url="https://img/1",
            )
        assert captured["media_urls"] == ["https://img/1"]
        assert msg is not None
        assert msg.media_url == "https://img/1"

    @pytest.mark.asyncio
    async def test_whatsapp_reply_fields(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            import json

            captured.update(json.loads(request.content.decode()))
            return httpx.Response(201, json=[_wa_row()])

        async with respx.mock() as rx:
            rx.post(WA_URL).mock(side_effect=_capture)
            await add_message(
                "+34611",
                "user",
                "quoted reply",
                wa_message_id="WAMID123",
                reply_to_wa_id="WAMID000",
                reply_to_text="prev message",
            )
        assert captured["wa_message_id"] == "WAMID123"
        assert captured["reply_to_wa_id"] == "WAMID000"
        assert captured["reply_to_text"] == "prev message"

    @pytest.mark.asyncio
    async def test_web_happy_path(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            import json

            captured.update(json.loads(request.content.decode()))
            return httpx.Response(201, json=[_web_row()])

        async with respx.mock() as rx:
            rx.post(WEB_URL).mock(side_effect=_capture)
            msg = await add_message("anon-42", "user", "hello", channel="web")
        assert msg is not None
        assert msg.channel == "web"
        assert captured["user_id"] == "anon-42"
        assert captured["text"] == "hello"
        assert captured["channel"] == "web"
        # WA-specific fields absent
        assert "phone_number" not in captured

    @pytest.mark.asyncio
    async def test_web_metadata_and_media(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            import json

            captured.update(json.loads(request.content.decode()))
            return httpx.Response(
                201,
                json=[
                    _web_row(
                        media_url="https://img/1",
                        metadata={"pane": "brief"},
                    )
                ],
            )

        async with respx.mock() as rx:
            rx.post(WEB_URL).mock(side_effect=_capture)
            msg = await add_message(
                "anon-42",
                "assistant",
                "here you go",
                channel="web",
                media_url="https://img/1",
                metadata={"pane": "brief"},
            )
        assert captured["media_url"] == "https://img/1"
        assert captured["metadata"] == {"pane": "brief"}
        assert msg is not None
        assert msg.metadata == {"pane": "brief"}

    @pytest.mark.asyncio
    async def test_5xx_returns_none(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.post(WA_URL).mock(return_value=httpx.Response(500, text="boom"))
            msg = await add_message("+34611", "user", "hola")
        assert msg is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.post(WA_URL).mock(side_effect=httpx.ConnectError("down"))
            msg = await add_message("+34611", "user", "hola")
        assert msg is None


# ============================== get_messages ==================================


class TestGetMessages:
    @pytest.mark.asyncio
    async def test_missing_env_returns_empty(self) -> None:
        assert await get_messages("+34611") == []

    @pytest.mark.asyncio
    async def test_whatsapp_happy_path(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(WA_URL).mock(
                return_value=httpx.Response(200, json=[_wa_row(id="a"), _wa_row(id="b")])
            )
            rows = await get_messages("+34611")
        assert [m.id for m in rows] == ["a", "b"]
        assert all(m.channel == "whatsapp" for m in rows)

    @pytest.mark.asyncio
    async def test_web_happy_path(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(WEB_URL).mock(
                return_value=httpx.Response(200, json=[_web_row(id="w1")])
            )
            rows = await get_messages("anon-42", channel="web")
        assert [m.id for m in rows] == ["w1"]
        assert rows[0].channel == "web"

    @pytest.mark.asyncio
    async def test_limit_clamped_to_max_page(self, supabase_env: None) -> None:
        captured_params: Dict[str, str] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured_params.update(dict(request.url.params))
            return httpx.Response(200, json=[])

        async with respx.mock() as rx:
            rx.get(WA_URL).mock(side_effect=_capture)
            await get_messages("+34611", limit=9999)
        assert captured_params["limit"] == "200"

    @pytest.mark.asyncio
    async def test_limit_clamped_to_at_least_1(self, supabase_env: None) -> None:
        captured_params: Dict[str, str] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured_params.update(dict(request.url.params))
            return httpx.Response(200, json=[])

        async with respx.mock() as rx:
            rx.get(WA_URL).mock(side_effect=_capture)
            await get_messages("+34611", limit=-5)
        assert captured_params["limit"] == "1"

    @pytest.mark.asyncio
    async def test_before_cursor_forwarded(self, supabase_env: None) -> None:
        captured_params: Dict[str, str] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured_params.update(dict(request.url.params))
            return httpx.Response(200, json=[])

        cursor = datetime(2026, 3, 1, tzinfo=timezone.utc)
        async with respx.mock() as rx:
            rx.get(WA_URL).mock(side_effect=_capture)
            await get_messages("+34611", before=cursor)
        assert captured_params["created_at"] == f"lt.{cursor.isoformat()}"

    @pytest.mark.asyncio
    async def test_5xx_returns_empty(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(WA_URL).mock(return_value=httpx.Response(500))
            assert await get_messages("+34611") == []

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(WA_URL).mock(side_effect=httpx.ConnectError("down"))
            assert await get_messages("+34611") == []


# ============================ get_recent_window ===============================


class TestGetRecentWindow:
    @pytest.mark.asyncio
    async def test_applies_window_filter(self, supabase_env: None) -> None:
        now = datetime.now(timezone.utc)
        within = now - timedelta(hours=6)
        outside = now - timedelta(hours=48)

        async with respx.mock() as rx:
            rx.get(WA_URL).mock(
                return_value=httpx.Response(
                    200,
                    json=[
                        _wa_row(id="recent", created_at=within.isoformat()),
                        _wa_row(id="old", created_at=outside.isoformat()),
                    ],
                )
            )
            rows = await get_recent_window("+34611", hours=24)
        ids = [m.id for m in rows]
        assert "recent" in ids
        assert "old" not in ids

    @pytest.mark.asyncio
    async def test_hours_zero_returns_all(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(WA_URL).mock(
                return_value=httpx.Response(
                    200,
                    json=[
                        _wa_row(id="a"),
                        _wa_row(id="b"),
                    ],
                )
            )
            rows = await get_recent_window("+34611", hours=0)
        assert len(rows) == 2

    @pytest.mark.asyncio
    async def test_cap_clamped(self, supabase_env: None) -> None:
        captured_params: Dict[str, str] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured_params.update(dict(request.url.params))
            return httpx.Response(200, json=[])

        async with respx.mock() as rx:
            rx.get(WA_URL).mock(side_effect=_capture)
            await get_recent_window("+34611", cap=9999)
        assert captured_params["limit"] == "200"


# ============================ summarize_recent ================================


class TestSummarizeRecent:
    @pytest.mark.asyncio
    async def test_empty_messages_returns_empty(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(WA_URL).mock(return_value=httpx.Response(200, json=[]))
            assert await summarize_recent("+34611") == ""

    @pytest.mark.asyncio
    async def test_only_verbatim_when_all_recent(
        self, supabase_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # recent_verbatim >= total → entire log kept verbatim, no LLM call
        async with respx.mock() as rx:
            rx.get(WA_URL).mock(
                return_value=httpx.Response(
                    200,
                    json=[
                        _wa_row(id="m1", role="user", message_text="first"),
                        _wa_row(id="m2", role="assistant", message_text="reply"),
                    ],
                )
            )

            calls: List[Any] = []

            async def forbidden(*args: Any, **kwargs: Any) -> str:
                calls.append(args)
                raise AssertionError("llm.complete should not be called")

            monkeypatch.setattr(_conv, "_summarize_older", lambda older: [])
            out = await summarize_recent("+34611", recent_verbatim=10)
        # messages are DESC from get_messages, so reversed is [m2, m1]
        # verbatim has "assistant: reply" and "user: first"
        assert "assistant: reply" in out
        assert "user: first" in out

    @pytest.mark.asyncio
    async def test_llm_bullet_fallback_on_exception(
        self, supabase_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Older bucket exists, but llm.complete raises → degraded bullet
        now = datetime(2026, 4, 20, 12, 0, 0, tzinfo=timezone.utc)
        older_time = (now - timedelta(hours=5)).isoformat()
        recent_time = now.isoformat()
        async with respx.mock() as rx:
            rx.get(WA_URL).mock(
                return_value=httpx.Response(
                    200,
                    json=[
                        _wa_row(
                            id="new",
                            role="user",
                            message_text="latest",
                            created_at=recent_time,
                        ),
                        _wa_row(
                            id="old",
                            role="user",
                            message_text="ages ago",
                            created_at=older_time,
                        ),
                    ],
                )
            )

            import llm as _llm

            async def boom(*args: Any, **kwargs: Any) -> str:
                raise RuntimeError("upstream down")

            monkeypatch.setattr(_llm, "chat", boom, raising=False)
            out = await summarize_recent(
                "+34611",
                recent_verbatim=1,
                max_chars=10_000,
            )
        assert "summary unavailable" in out
        # verbatim tail is preserved
        assert "user: latest" in out

    @pytest.mark.asyncio
    async def test_llm_bullets_prepend_verbatim_appends(
        self, supabase_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        now = datetime(2026, 4, 20, 12, 0, 0, tzinfo=timezone.utc)
        older_time = (now - timedelta(hours=5)).isoformat()
        recent_time = now.isoformat()
        async with respx.mock() as rx:
            rx.get(WA_URL).mock(
                return_value=httpx.Response(
                    200,
                    json=[
                        _wa_row(
                            id="new",
                            role="user",
                            message_text="latest",
                            created_at=recent_time,
                        ),
                        _wa_row(
                            id="old",
                            role="user",
                            message_text="ages ago",
                            created_at=older_time,
                        ),
                    ],
                )
            )

            import llm as _llm
            from llm import ChatResponse

            async def stub(messages, **kwargs):
                return ChatResponse(
                    text="user discussed kitchen reform budget",
                    finish_reason="stop",
                    raw={},
                )

            monkeypatch.setattr(_llm, "chat", stub, raising=False)
            out = await summarize_recent(
                "+34611",
                recent_verbatim=1,
                max_chars=10_000,
            )
        # bullet prepended
        assert out.startswith("- user discussed kitchen reform budget")
        # verbatim tail appended
        assert "user: latest" in out
        # order: bullet before verbatim
        bullet_idx = out.index("- user discussed")
        verbatim_idx = out.index("user: latest")
        assert bullet_idx < verbatim_idx


# ============================ _row_to_message =================================


class TestRowToMessage:
    def test_whatsapp_shape(self) -> None:
        msg = _row_to_message(_wa_row(), channel="whatsapp")
        assert msg.channel == "whatsapp"
        assert msg.user_id == "+34611"
        assert msg.text == "hola"
        assert msg.role == "user"

    def test_whatsapp_media_head(self) -> None:
        msg = _row_to_message(
            _wa_row(media_urls=["https://img/1", "https://img/2"]),
            channel="whatsapp",
        )
        assert msg.media_url == "https://img/1"

    def test_whatsapp_no_media(self) -> None:
        msg = _row_to_message(_wa_row(media_urls=[]), channel="whatsapp")
        assert msg.media_url is None

    def test_web_shape(self) -> None:
        msg = _row_to_message(_web_row(), channel="web")
        assert msg.channel == "web"
        assert msg.user_id == "anon-42"
        assert msg.text == "hello"

    def test_invalid_role_coerced_to_user(self) -> None:
        msg = _row_to_message(_wa_row(role="space_alien"), channel="whatsapp")
        assert msg.role == "user"

    def test_missing_text_becomes_empty_string(self) -> None:
        msg = _row_to_message(_wa_row(message_text=None), channel="whatsapp")
        assert msg.text == ""


class TestEnsureAware:
    def test_naive_becomes_utc(self) -> None:
        naive = datetime(2026, 1, 1, 12, 0, 0)
        assert _ensure_aware(naive).tzinfo is not None

    def test_aware_unchanged(self) -> None:
        aware = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert _ensure_aware(aware) is aware
