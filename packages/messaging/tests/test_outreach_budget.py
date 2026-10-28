"""Cold-outreach daily budget — quota math + queue eligibility."""

from __future__ import annotations

from typing import Any

import pytest


class _FakeResp:
    def __init__(self, status: int, body: Any = None) -> None:
        self.status_code = status
        self._body = body if body is not None else []

    def json(self):
        return self._body

    @property
    def text(self) -> str:
        import json
        return json.dumps(self._body) if not isinstance(self._body, str) else self._body


class _FakeHttp:
    def __init__(self, responses: list[_FakeResp]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict | None]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return None

    async def get(self, url: str, **_):
        self.calls.append(("GET", url, None))
        return self._responses.pop(0)

    async def post(self, url: str, json=None, **_):
        self.calls.append(("POST", url, json))
        return self._responses.pop(0)

    async def patch(self, url: str, json=None, **_):
        self.calls.append(("PATCH", url, json))
        return self._responses.pop(0)


class TestDailySentCount:
    @pytest.mark.asyncio
    async def test_counts_rows(self, stub_supabase_env, monkeypatch) -> None:
        from messaging.whatsapp import daily_sent_count

        fake = _FakeHttp([_FakeResp(200, [{"id": "1"}, {"id": "2"}, {"id": "3"}])])
        monkeypatch.setattr(
            "messaging.whatsapp.outreach_budget.http_client",
            lambda **k: fake,
        )
        n = await daily_sent_count("waba_abc")
        assert n == 3

    @pytest.mark.asyncio
    async def test_returns_zero_on_error(self, stub_supabase_env, monkeypatch) -> None:
        from messaging.whatsapp import daily_sent_count

        fake = _FakeHttp([_FakeResp(500, "boom")])
        monkeypatch.setattr(
            "messaging.whatsapp.outreach_budget.http_client",
            lambda **k: fake,
        )
        n = await daily_sent_count("waba_abc")
        assert n == 0

    @pytest.mark.asyncio
    async def test_returns_zero_on_exception(
        self, stub_supabase_env, monkeypatch,
    ) -> None:
        from messaging.whatsapp import daily_sent_count

        def _boom(**_):
            raise RuntimeError("network")

        monkeypatch.setattr(
            "messaging.whatsapp.outreach_budget.http_client", _boom,
        )
        n = await daily_sent_count("waba_abc")
        assert n == 0


class TestRequestQuota:
    @pytest.mark.asyncio
    async def test_all_approved_when_under_limit(
        self, stub_supabase_env, monkeypatch,
    ) -> None:
        from messaging.whatsapp import request_quota

        async def _already_sent(_waba):
            return 5

        monkeypatch.setattr(
            "messaging.whatsapp.outreach_budget.daily_sent_count", _already_sent,
        )
        approved, queued = await request_quota("waba", n=3, daily_limit=20)
        assert (approved, queued) == (3, 0)

    @pytest.mark.asyncio
    async def test_partial_queue_when_exceeding(
        self, stub_supabase_env, monkeypatch,
    ) -> None:
        from messaging.whatsapp import request_quota

        async def _already_sent(_waba):
            return 18

        monkeypatch.setattr(
            "messaging.whatsapp.outreach_budget.daily_sent_count", _already_sent,
        )
        approved, queued = await request_quota("waba", n=5, daily_limit=20)
        assert (approved, queued) == (2, 3)

    @pytest.mark.asyncio
    async def test_all_queued_when_at_limit(
        self, stub_supabase_env, monkeypatch,
    ) -> None:
        from messaging.whatsapp import request_quota

        async def _already_sent(_waba):
            return 20

        monkeypatch.setattr(
            "messaging.whatsapp.outreach_budget.daily_sent_count", _already_sent,
        )
        approved, queued = await request_quota("waba", n=4, daily_limit=20)
        assert (approved, queued) == (0, 4)

    @pytest.mark.asyncio
    async def test_over_sent_treated_as_zero_remaining(
        self, stub_supabase_env, monkeypatch,
    ) -> None:
        """If already_sent > daily_limit we don't report negative remaining."""
        from messaging.whatsapp import request_quota

        async def _already_sent(_waba):
            return 25

        monkeypatch.setattr(
            "messaging.whatsapp.outreach_budget.daily_sent_count", _already_sent,
        )
        approved, queued = await request_quota("waba", n=3, daily_limit=20)
        assert approved == 0
        assert queued == 3


class TestLogSend:
    @pytest.mark.asyncio
    async def test_writes_row_to_cold_outreach_log(
        self, stub_supabase_env, monkeypatch,
    ) -> None:
        from messaging.whatsapp import log_send

        fake = _FakeHttp([_FakeResp(201, [])])
        monkeypatch.setattr(
            "messaging.whatsapp.outreach_budget.http_client",
            lambda **k: fake,
        )
        await log_send(waba_id="abc", phone_digits="34600000000", job_id="j1")
        method, url, payload = fake.calls[0]
        assert method == "POST"
        assert "cold_outreach_log" in url
        assert payload["phone_digits"] == "34600000000"
        assert payload["purpose"] == "cold"
        assert payload["job_id"] == "j1"

    @pytest.mark.asyncio
    async def test_error_is_non_fatal(
        self, stub_supabase_env, monkeypatch,
    ) -> None:
        from messaging.whatsapp import log_send

        fake = _FakeHttp([_FakeResp(500, "boom")])
        monkeypatch.setattr(
            "messaging.whatsapp.outreach_budget.http_client",
            lambda **k: fake,
        )
        # Should not raise.
        await log_send(waba_id="abc", phone_digits="34600000000")


class TestEnqueueDeferred:
    @pytest.mark.asyncio
    async def test_skips_entries_without_digits(
        self, stub_supabase_env, monkeypatch,
    ) -> None:
        from messaging.whatsapp import enqueue_deferred

        fake = _FakeHttp([])  # no http calls expected
        monkeypatch.setattr(
            "messaging.whatsapp.outreach_budget.http_client",
            lambda **k: fake,
        )
        n = await enqueue_deferred(
            entries=[{"name": "no digits here"}],
            waba_id="abc",
            job_id="j",
            humanized_summary="hi",
        )
        assert n == 0
        assert fake.calls == []

    @pytest.mark.asyncio
    async def test_inserts_rows(self, stub_supabase_env, monkeypatch) -> None:
        from messaging.whatsapp import enqueue_deferred

        fake = _FakeHttp([_FakeResp(201, [])])
        monkeypatch.setattr(
            "messaging.whatsapp.outreach_budget.http_client",
            lambda **k: fake,
        )
        n = await enqueue_deferred(
            entries=[
                {"_digits": "34600000001", "name": "Alice"},
                {"_digits": "34600000002", "name": "Bob"},
            ],
            waba_id="abc",
            job_id="j1",
            humanized_summary="job update",
        )
        assert n == 2
        _, _, rows = fake.calls[0]
        assert len(rows) == 2
        assert rows[0]["phone_digits"] == "34600000001"
