"""``messaging.notify`` unified dispatch + channel routing."""

from __future__ import annotations

from typing import Any

import pytest

from messaging import Channel, NotifyResult, notify


class _Recorder:
    """Stand-in for :func:`send_wa_message` / :func:`send_email`."""

    def __init__(self, wa_result=None, email_result=None) -> None:
        self.wa_result = wa_result or _wa_ok()
        self.email_result = email_result or {"ok": True, "id": "eml_1"}
        self.wa_calls: list[dict] = []
        self.email_calls: list[dict] = []

    async def send_wa(self, **kwargs) -> Any:
        self.wa_calls.append(kwargs)
        return self.wa_result

    async def send_email(self, **kwargs) -> Any:
        self.email_calls.append(kwargs)
        return self.email_result


def _wa_ok(wamid: str = "wamid.ok"):
    from messaging.whatsapp import SendResult

    return SendResult(ok=True, wa_message_id=wamid)


def _wa_fail(error: str = "template_failed"):
    from messaging.whatsapp import SendResult

    return SendResult(ok=False, error=error)


@pytest.fixture
def recorder(monkeypatch) -> _Recorder:
    rec = _Recorder()
    monkeypatch.setattr("messaging.comms.send_wa_message", rec.send_wa)
    monkeypatch.setattr("messaging.comms.send_email", rec.send_email)
    return rec


class TestAutoRouting:
    @pytest.mark.asyncio
    async def test_spanish_phone_routes_whatsapp(self, recorder) -> None:
        results = await notify(phone="+34600000000", email="x@y.es", message="hola")
        assert len(results) == 1
        assert results[0].channel == "whatsapp"
        assert results[0].success
        assert len(recorder.wa_calls) == 1
        assert len(recorder.email_calls) == 0

    @pytest.mark.asyncio
    async def test_non_spanish_phone_prefers_email(self, recorder) -> None:
        results = await notify(
            phone="+14155550100", email="x@y.com", message="hi", subject="s",
        )
        assert len(results) == 1
        assert results[0].channel == "email"

    @pytest.mark.asyncio
    async def test_no_phone_uses_email(self, recorder) -> None:
        results = await notify(email="x@y.com", message="hi", subject="s")
        assert results[0].channel == "email"

    @pytest.mark.asyncio
    async def test_no_recipients_returns_empty(self, recorder) -> None:
        results = await notify(message="hi")
        assert results == []


class TestExplicitChannel:
    @pytest.mark.asyncio
    async def test_explicit_whatsapp(self, recorder) -> None:
        results = await notify(
            phone="+14155550100", email="x@y.com", message="hi", channel=Channel.WHATSAPP,
        )
        assert len(results) == 1
        assert results[0].channel == "whatsapp"

    @pytest.mark.asyncio
    async def test_explicit_email(self, recorder) -> None:
        results = await notify(
            phone="+34600000000", email="x@y.es", message="hi",
            subject="Test", channel=Channel.EMAIL,
        )
        assert len(results) == 1
        assert results[0].channel == "email"


class TestChannelAll:
    @pytest.mark.asyncio
    async def test_fans_out_to_both_channels(self, recorder) -> None:
        results = await notify(
            phone="+34600000000", email="x@y.es",
            message="update", subject="Status", channel=Channel.ALL,
        )
        channels = sorted(r.channel for r in results)
        assert channels == ["email", "whatsapp"]


class TestFailureHandling:
    @pytest.mark.asyncio
    async def test_whatsapp_failure_surfaces_as_not_success(self, monkeypatch) -> None:
        rec = _Recorder(wa_result=_wa_fail())
        monkeypatch.setattr("messaging.comms.send_wa_message", rec.send_wa)
        monkeypatch.setattr("messaging.comms.send_email", rec.send_email)
        results = await notify(phone="+34600000000", message="hi")
        assert results[0].success is False
        assert results[0].channel == "whatsapp"
        assert "template_failed" in results[0].detail

    @pytest.mark.asyncio
    async def test_whatsapp_exception_yields_detail(self, monkeypatch) -> None:
        async def _boom(**kwargs):
            raise RuntimeError("network down")

        monkeypatch.setattr("messaging.comms.send_wa_message", _boom)
        results = await notify(phone="+34600000000", message="hi")
        assert results[0].success is False
        assert "network down" in results[0].detail

    @pytest.mark.asyncio
    async def test_email_exception_yields_detail(self, monkeypatch) -> None:
        async def _boom_email(**kwargs):
            raise RuntimeError("resend 429")

        # ensure WA success is benign — not used in this path
        rec = _Recorder()
        monkeypatch.setattr("messaging.comms.send_wa_message", rec.send_wa)
        monkeypatch.setattr("messaging.comms.send_email", _boom_email)
        results = await notify(email="x@y.com", subject="hi", message="hi")
        assert results[0].success is False
        assert "resend 429" in results[0].detail


class TestNotifyResultDataclass:
    def test_defaults(self) -> None:
        r = NotifyResult(success=True, channel="whatsapp")
        assert r.success
        assert r.channel == "whatsapp"
        assert r.detail == ""
