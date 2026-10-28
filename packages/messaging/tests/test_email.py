"""Email dispatcher — Resend API contract + payload construction."""

from __future__ import annotations

from typing import Any

import pytest

from messaging import send_email
from messaging.email import send_email_resend


class _FakeResp:
    def __init__(self, status: int, body: dict | None = None, text: str = "") -> None:
        self.status_code = status
        self._body = body or {}
        self._text = text or (str(self._body) if self._body else "")

    def json(self) -> dict:
        return self._body

    @property
    def text(self) -> str:
        return self._text


class _FakeHttp:
    def __init__(self, resp: _FakeResp) -> None:
        self._resp = resp
        self.calls: list[tuple[str, dict, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return None

    async def post(self, url: str, json: dict, headers: dict, **_):
        self.calls.append((url, json, headers))
        return self._resp


class TestSendEmail:
    @pytest.mark.asyncio
    async def test_missing_api_key_returns_error(self) -> None:
        result = await send_email(to="a@b.com", subject="s")
        assert result["ok"] is False
        assert result["error"] == "resend_api_key_missing"

    @pytest.mark.asyncio
    async def test_success_returns_id(
        self, stub_resend_env, monkeypatch,
    ) -> None:
        fake = _FakeHttp(_FakeResp(200, {"id": "eml_abc"}))
        monkeypatch.setattr("messaging.email.resend.http_client", lambda **k: fake)

        result = await send_email(
            to="a@b.com",
            subject="Hello",
            body_html="<p>hi</p>",
            body_text="hi",
        )
        assert result["ok"] is True
        assert result["id"] == "eml_abc"
        url, payload, headers = fake.calls[0]
        assert url == "https://api.resend.com/emails"
        assert payload["to"] == "a@b.com"
        assert payload["subject"] == "Hello"
        assert payload["html"] == "<p>hi</p>"
        assert payload["text"] == "hi"
        assert "Authorization" in headers

    @pytest.mark.asyncio
    async def test_default_from_field(
        self, stub_resend_env, monkeypatch,
    ) -> None:
        fake = _FakeHttp(_FakeResp(200, {"id": "eml_1"}))
        monkeypatch.setattr("messaging.email.resend.http_client", lambda **k: fake)
        await send_email(to="a@b.com", subject="s", body_text="hi")
        assert "Leo <project-agent@projects.leo.casa>" == fake.calls[0][1]["from"]

    @pytest.mark.asyncio
    async def test_reply_to_and_tags(
        self, stub_resend_env, monkeypatch,
    ) -> None:
        fake = _FakeHttp(_FakeResp(200, {"id": "eml_1"}))
        monkeypatch.setattr("messaging.email.resend.http_client", lambda **k: fake)
        await send_email(
            to="a@b.com",
            subject="s",
            body_text="hi",
            reply_to="team@leo.casa",
            tags=[{"name": "kind", "value": "founder"}],
        )
        payload = fake.calls[0][1]
        assert payload["reply_to"] == "team@leo.casa"
        assert payload["tags"] == [{"name": "kind", "value": "founder"}]

    @pytest.mark.asyncio
    async def test_api_error_returns_failure(
        self, stub_resend_env, monkeypatch,
    ) -> None:
        fake = _FakeHttp(_FakeResp(429, text="rate limited"))
        monkeypatch.setattr("messaging.email.resend.http_client", lambda **k: fake)
        result = await send_email(to="a@b.com", subject="s")
        assert result["ok"] is False
        assert result["error"] == "resend_429"

    @pytest.mark.asyncio
    async def test_exception_returns_failure(
        self, stub_resend_env, monkeypatch,
    ) -> None:
        def _raises(**_):
            raise RuntimeError("network")

        monkeypatch.setattr("messaging.email.resend.http_client", _raises)
        result = await send_email(to="a@b.com", subject="s")
        assert result["ok"] is False
        assert "network" in result["error"]


class TestLegacyAlias:
    @pytest.mark.asyncio
    async def test_send_email_resend_delegates(
        self, stub_resend_env, monkeypatch,
    ) -> None:
        fake = _FakeHttp(_FakeResp(200, {"id": "eml_legacy"}))
        monkeypatch.setattr("messaging.email.resend.http_client", lambda **k: fake)
        result = await send_email_resend(
            to="a@b.com",
            subject="s",
            body_html="<p>x</p>",
            body_text="x",
            from_label="Scope",
            from_address="scope@leo.casa",
        )
        assert result["ok"] is True
        assert fake.calls[0][1]["from"] == "Scope <scope@leo.casa>"
