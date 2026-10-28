"""Unified WhatsApp sender — behavior under various API responses."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from messaging.whatsapp import SendResult, send_wa_message


class _FakeResp:
    def __init__(self, status: int, body: dict) -> None:
        self.status_code = status
        self._body = body

    def json(self) -> dict:
        return self._body

    @property
    def text(self) -> str:
        import json
        return json.dumps(self._body)


class _FakeHttpClient:
    """Context-manager-style fake for :func:`core.http_client`."""

    def __init__(self, responses: list[_FakeResp]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, dict]] = []

    async def __aenter__(self) -> "_FakeHttpClient":
        return self

    async def __aexit__(self, *exc_info) -> None:
        return None

    async def post(self, url: str, json: dict | None = None, **_kw) -> _FakeResp:
        self.calls.append((url, json or {}))
        return self._responses.pop(0)

    async def get(self, url: str, **_kw) -> _FakeResp:
        self.calls.append((url, {}))
        return self._responses.pop(0)


@pytest.fixture
def no_window(monkeypatch):
    """Force :func:`check_24h_window` to return False (cold number)."""
    from messaging.whatsapp import send as send_mod

    async def _closed(*a, **k):
        return False

    monkeypatch.setattr(send_mod, "check_24h_window", _closed)


@pytest.fixture
def open_window(monkeypatch):
    """Force :func:`check_24h_window` to return True (inside 24h window)."""
    from messaging.whatsapp import send as send_mod

    async def _open(*a, **k):
        return True

    monkeypatch.setattr(send_mod, "check_24h_window", _open)


@pytest.fixture
def stub_store(monkeypatch):
    """Replace :func:`store_message` with a no-op coroutine."""
    from messaging.whatsapp import send as send_mod

    async def _noop(*a, **k):
        return {}

    monkeypatch.setattr(send_mod, "store_message", _noop)


@pytest.fixture
def stub_log_send(monkeypatch):
    """Replace cold-send counter with no-op (mutates the imported alias)."""
    from messaging.whatsapp import send as send_mod

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(send_mod, "_log_send", _noop)


class TestSendWaMessage:
    """Behaviours that do not require network or Supabase reachability."""

    @pytest.mark.asyncio
    async def test_missing_config_returns_error(self) -> None:
        # No WHATSAPP_TOKEN / WHATSAPP_PHONE_NUMBER_ID set
        result = await send_wa_message(phone="+34600000000", text="hello")
        assert result.ok is False
        assert "WhatsApp not configured" in result.error

    @pytest.mark.asyncio
    async def test_invalid_phone_returns_error(self, stub_meta_env) -> None:
        result = await send_wa_message(phone="+1", text="hi")
        assert result.ok is False
        assert "Invalid phone number" in result.error

    @pytest.mark.asyncio
    async def test_open_window_sends_text(
        self,
        stub_meta_env,
        open_window,
        stub_store,
        stub_log_send,
        monkeypatch,
    ) -> None:
        fake = _FakeHttpClient([_FakeResp(200, {"messages": [{"id": "wamid.abc"}]})])

        def _fake_http(**_kw):
            return fake

        monkeypatch.setattr("messaging.whatsapp.send.http_client", _fake_http)

        result = await send_wa_message(phone="+34600000000", text="hola")

        assert result.ok is True
        assert result.method == "text"
        assert result.wa_message_id == "wamid.abc"
        assert result.window_was_open is True
        body = fake.calls[0][1]
        assert body["type"] == "text"
        assert body["text"]["body"] == "hola"
        assert body["to"] == "34600000000"

    @pytest.mark.asyncio
    async def test_url_triggers_preview_url_flag(
        self,
        stub_meta_env,
        open_window,
        stub_store,
        stub_log_send,
        monkeypatch,
    ) -> None:
        fake = _FakeHttpClient([_FakeResp(200, {"messages": [{"id": "wamid.1"}]})])
        monkeypatch.setattr("messaging.whatsapp.send.http_client", lambda **k: fake)

        result = await send_wa_message(phone="+34600000000", text="see https://leo.casa")
        assert result.ok is True
        assert fake.calls[0][1]["text"]["preview_url"] is True

    @pytest.mark.asyncio
    async def test_closed_window_uses_template(
        self,
        stub_meta_env,
        no_window,
        stub_store,
        stub_log_send,
        monkeypatch,
    ) -> None:
        fake = _FakeHttpClient([_FakeResp(200, {"messages": [{"id": "wamid.xyz"}]})])
        monkeypatch.setattr("messaging.whatsapp.send.http_client", lambda **k: fake)

        result = await send_wa_message(
            phone="+34600000000", text="hola", purpose="outreach", name="Juan",
        )
        assert result.ok is True
        assert result.method == "template"
        body = fake.calls[0][1]
        assert body["type"] == "template"
        assert body["template"]["name"] == "contractor_intro_v2"
        assert body["template"]["language"]["code"] == "es"

    @pytest.mark.asyncio
    async def test_template_door_opener_note_for_general_purpose(
        self,
        stub_meta_env,
        no_window,
        stub_store,
        stub_log_send,
        monkeypatch,
    ) -> None:
        fake = _FakeHttpClient([_FakeResp(200, {"messages": [{"id": "wamid.general"}]})])
        monkeypatch.setattr("messaging.whatsapp.send.http_client", lambda **k: fake)

        result = await send_wa_message(phone="+34600000000", text="hi", purpose="general")
        assert result.method == "template_door_opener"
        assert "must reply" in result.note

    @pytest.mark.asyncio
    async def test_skip_window_check_forces_text(
        self,
        stub_meta_env,
        stub_store,
        stub_log_send,
        monkeypatch,
    ) -> None:
        # Don't set the check_24h_window fixture — the flag should skip it.
        fake = _FakeHttpClient([_FakeResp(200, {"messages": [{"id": "wamid.int"}]})])
        monkeypatch.setattr("messaging.whatsapp.send.http_client", lambda **k: fake)

        result = await send_wa_message(
            phone="+34600000000", text="founder ping", skip_window_check=True,
        )
        assert result.ok is True
        assert result.method == "text"

    @pytest.mark.asyncio
    async def test_exception_yields_ok_false(
        self,
        stub_meta_env,
        open_window,
        monkeypatch,
    ) -> None:
        def _raises(**_kw):
            raise RuntimeError("boom")

        monkeypatch.setattr("messaging.whatsapp.send.http_client", _raises)
        result = await send_wa_message(phone="+34600000000", text="hi")
        assert result.ok is False
        assert "boom" in result.error


class TestSendResultDefaults:
    def test_default_method_is_empty(self) -> None:
        r = SendResult(ok=True)
        assert r.method == ""
        assert r.window_was_open is False
        assert r.wa_message_id == ""
