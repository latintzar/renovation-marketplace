"""Tests for :mod:`storage.leads` — ``cs_leads`` + ``early_access_signups``.

Covers the three public entry points plus the two load-bearing legacy
invariants pulled into Phase 4 verbatim:

- Dual-table fallback: on ``cs_leads`` write failure, the lead is
  re-attempted against ``early_access_signups`` with a mangled
  ``source`` string. ``LeadSaveResult.table_written`` must distinguish
  the two code paths (design.md D14).
- ``---LEO_STRUCTURED---`` marker + 4000-char cap on
  :func:`patch_lead_structured`. A prior blob is stripped, the new JSON
  is appended after the marker, and the result is truncated to
  :const:`storage.leads._MAX_CHAT_SUMMARY_CHARS`.
- :func:`get_lead_by_phone` runs a single ``ORDER BY created_at DESC
  LIMIT 1`` query and maps the row into a :class:`Lead`.

All Supabase I/O is intercepted with :mod:`respx` against ``sb_url()``
and returns deterministic JSON. Environment leakage is neutralised
by the ``env_isolated`` + ``supabase_env`` fixtures in
:mod:`conftest`.
"""
from __future__ import annotations

import json
from typing import Any, Dict

import httpx
import pytest
import respx

from records.leads import (
    _MAX_CHAT_SUMMARY_CHARS,
    _STRUCTURED_MARKER,
    _parse_ts,
    _row_to_lead,
    get_lead_by_phone,
    patch_lead_structured,
    save_lead,
)
from records.types import Lead, LeadSaveResult


SB_BASE = "http://127.0.0.1:54321"
CS_LEADS_URL = f"{SB_BASE}/rest/v1/cs_leads"
EA_URL = f"{SB_BASE}/rest/v1/early_access_signups"


# ---------------------------------- helpers -----------------------------------


def _row(**overrides: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "id": "lead-1",
        "name": "Ana",
        "whatsapp": "+34612345678",
        "location": "Madrid",
        "source": "leo_chat",
        "chat_summary": "kitchen reform 15k",
        "chat_history": None,
        "audience": "homeowner",
        "created_at": "2026-04-20T12:00:00+00:00",
    }
    base.update(overrides)
    return base


# ============================= save_lead ======================================


class TestSaveLeadCredentials:
    @pytest.mark.asyncio
    async def test_returns_db_not_configured_when_env_missing(self) -> None:
        result = await save_lead("Ana", "+34612345678", "Madrid")
        assert isinstance(result, LeadSaveResult)
        assert result.ok is False
        assert result.error == "db_not_configured"
        assert result.table_written is None


class TestSaveLeadPrimaryPath:
    @pytest.mark.asyncio
    async def test_happy_path_writes_to_cs_leads(self, supabase_env: None) -> None:
        async with respx.mock(assert_all_called=True) as rx:
            rx.post(CS_LEADS_URL).mock(
                return_value=httpx.Response(201, json=[_row()])
            )
            result = await save_lead(
                "Ana",
                "+34612345678",
                "Madrid",
                chat_summary="kitchen reform 15k",
            )
        assert result.ok is True
        assert result.table_written == "cs_leads"
        assert result.lead_id == "lead-1"

    @pytest.mark.asyncio
    async def test_strips_whitespace_in_core_fields(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(201, json=[_row()])

        async with respx.mock() as rx:
            rx.post(CS_LEADS_URL).mock(side_effect=_capture)
            await save_lead(
                "  Ana  ",
                " +34612345678 ",
                "  Madrid ",
                chat_summary="  hola  ",
            )
        assert captured["name"] == "Ana"
        assert captured["whatsapp"] == "+34612345678"
        assert captured["location"] == "Madrid"
        assert captured["chat_summary"] == "hola"

    @pytest.mark.asyncio
    async def test_empty_core_fields_become_none(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(201, json=[_row()])

        async with respx.mock() as rx:
            rx.post(CS_LEADS_URL).mock(side_effect=_capture)
            await save_lead("   ", "   ", "   ", chat_summary="   ")
        assert captured["name"] is None
        assert captured["whatsapp"] is None
        assert captured["location"] is None
        assert captured["chat_summary"] is None

    @pytest.mark.asyncio
    async def test_chat_history_forwarded_when_nonempty(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}
        history = [{"role": "user", "text": "hola"}]

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(201, json=[_row()])

        async with respx.mock() as rx:
            rx.post(CS_LEADS_URL).mock(side_effect=_capture)
            await save_lead(
                "Ana",
                "+34612345678",
                "Madrid",
                chat_history=history,
            )
        assert captured["chat_history"] == history

    @pytest.mark.asyncio
    async def test_chat_history_omitted_when_empty(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(201, json=[_row()])

        async with respx.mock() as rx:
            rx.post(CS_LEADS_URL).mock(side_effect=_capture)
            await save_lead("Ana", "+34612345678", "Madrid", chat_history=None)
        assert "chat_history" not in captured

    @pytest.mark.asyncio
    async def test_custom_source_forwarded(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(201, json=[_row()])

        async with respx.mock() as rx:
            rx.post(CS_LEADS_URL).mock(side_effect=_capture)
            await save_lead(
                "Ana",
                "+34612345678",
                "Madrid",
                source="landing_v2",
            )
        assert captured["source"] == "landing_v2"

    @pytest.mark.asyncio
    async def test_lead_id_from_dict_response(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.post(CS_LEADS_URL).mock(
                return_value=httpx.Response(201, json=_row(id="solo-dict"))
            )
            result = await save_lead("Ana", "+34612345678", "Madrid")
        assert result.ok is True
        assert result.lead_id == "solo-dict"

    @pytest.mark.asyncio
    async def test_lead_id_absent_when_response_has_no_id(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.post(CS_LEADS_URL).mock(return_value=httpx.Response(200, json=[]))
            result = await save_lead("Ana", "+34612345678", "Madrid")
        assert result.ok is True
        assert result.table_written == "cs_leads"
        assert result.lead_id is None


class TestSaveLeadFallbackPath:
    @pytest.mark.asyncio
    async def test_5xx_on_cs_leads_falls_back_to_early_access(self, supabase_env: None) -> None:
        fallback_row = {
            "id": "ea-1",
            "email": None,
            "whatsapp": "+34612345678",
        }
        async with respx.mock() as rx:
            rx.post(CS_LEADS_URL).mock(
                return_value=httpx.Response(500, text="bang")
            )
            rx.post(EA_URL).mock(
                return_value=httpx.Response(201, json=[fallback_row])
            )
            result = await save_lead(
                "Ana",
                "+34612345678",
                "Madrid",
                chat_summary="kitchen reform 15k",
            )
        assert result.ok is True
        assert result.table_written == "early_access_signups"
        assert result.lead_id == "ea-1"

    @pytest.mark.asyncio
    async def test_fallback_row_contains_mangled_source(
        self, supabase_env: None
    ) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(201, json=[{"id": "ea-99"}])

        async with respx.mock() as rx:
            rx.post(CS_LEADS_URL).mock(return_value=httpx.Response(400, text="schema drift"))
            rx.post(EA_URL).mock(side_effect=_capture)
            await save_lead(
                "Ana",
                "+34612345678",
                "Madrid",
                source="landing_v2",
                chat_summary="kitchen reform 15k budget tight",
            )
        assert captured["source"].startswith("landing_v2 [Ana] ")
        assert "kitchen reform" in captured["source"]
        assert captured["email"] is None
        assert captured["whatsapp"] == "+34612345678"
        assert captured["location"] == "Madrid"

    @pytest.mark.asyncio
    async def test_both_writes_fail_returns_combined_error(
        self, supabase_env: None
    ) -> None:
        async with respx.mock() as rx:
            rx.post(CS_LEADS_URL).mock(return_value=httpx.Response(500))
            rx.post(EA_URL).mock(return_value=httpx.Response(503))
            result = await save_lead("Ana", "+34612345678", "Madrid")
        assert result.ok is False
        assert result.error == "cs_leads=500,ea=503"
        assert result.table_written is None


# ============================== patch_lead_structured =========================


class TestPatchLeadStructuredGuards:
    @pytest.mark.asyncio
    async def test_empty_phone_returns_false(self) -> None:
        assert await patch_lead_structured("") is False

    @pytest.mark.asyncio
    async def test_missing_credentials_returns_false(self) -> None:
        assert await patch_lead_structured("+34612345678") is False


class TestPatchLeadStructuredHappyPath:
    @pytest.mark.asyncio
    async def test_no_prior_blob_appends_marker_and_json(self, supabase_env: None) -> None:
        existing = "user summary so far"
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(204)

        async with respx.mock() as rx:
            rx.get(CS_LEADS_URL).mock(
                return_value=httpx.Response(200, json=[{"chat_summary": existing}])
            )
            rx.patch(CS_LEADS_URL).mock(side_effect=_capture)
            ok = await patch_lead_structured(
                "+34612345678",
                brief={"trade": "plumbing"},
                profile={"budget_eur": 1500},
            )
        assert ok is True
        new_summary: str = captured["chat_summary"]
        base, _, blob = new_summary.partition(_STRUCTURED_MARKER)
        assert base == "user summary so far"
        payload = json.loads(blob)
        assert payload == {
            "brief": {"trade": "plumbing"},
            "profile": {"budget_eur": 1500},
        }

    @pytest.mark.asyncio
    async def test_replaces_existing_blob(self, supabase_env: None) -> None:
        existing = (
            "head content"
            + _STRUCTURED_MARKER
            + json.dumps({"brief": {"trade": "old"}, "profile": {"budget_eur": 1}})
        )
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(204)

        async with respx.mock() as rx:
            rx.get(CS_LEADS_URL).mock(
                return_value=httpx.Response(200, json=[{"chat_summary": existing}])
            )
            rx.patch(CS_LEADS_URL).mock(side_effect=_capture)
            ok = await patch_lead_structured(
                "+34612345678",
                brief={"trade": "new"},
            )
        assert ok is True
        new_summary: str = captured["chat_summary"]
        # base must be preserved verbatim; only the new blob appended
        base, _, blob = new_summary.partition(_STRUCTURED_MARKER)
        assert base == "head content"
        payload = json.loads(blob)
        # previously we passed brief only; profile must be absent
        assert payload == {"brief": {"trade": "new"}}

    @pytest.mark.asyncio
    async def test_truncates_to_max_chars(self, supabase_env: None) -> None:
        existing = "x" * (_MAX_CHAT_SUMMARY_CHARS + 500)
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(204)

        async with respx.mock() as rx:
            rx.get(CS_LEADS_URL).mock(
                return_value=httpx.Response(200, json=[{"chat_summary": existing}])
            )
            rx.patch(CS_LEADS_URL).mock(side_effect=_capture)
            ok = await patch_lead_structured(
                "+34612345678",
                brief={"trade": "plumbing"},
            )
        assert ok is True
        assert len(captured["chat_summary"]) == _MAX_CHAT_SUMMARY_CHARS

    @pytest.mark.asyncio
    async def test_empty_payload_is_noop(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(CS_LEADS_URL).mock(
                return_value=httpx.Response(200, json=[{"chat_summary": "anything"}])
            )
            # no PATCH route — if we call PATCH this test blows up on
            # respx.assert_all_mocked (default True)
            ok = await patch_lead_structured("+34612345678")
        assert ok is True

    @pytest.mark.asyncio
    async def test_no_rows_returns_false(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(CS_LEADS_URL).mock(return_value=httpx.Response(200, json=[]))
            ok = await patch_lead_structured(
                "+34612345678",
                brief={"trade": "x"},
            )
        assert ok is False

    @pytest.mark.asyncio
    async def test_read_failure_returns_false(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(CS_LEADS_URL).mock(return_value=httpx.Response(500))
            ok = await patch_lead_structured(
                "+34612345678",
                brief={"trade": "x"},
            )
        assert ok is False

    @pytest.mark.asyncio
    async def test_patch_failure_returns_false(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(CS_LEADS_URL).mock(
                return_value=httpx.Response(200, json=[{"chat_summary": ""}])
            )
            rx.patch(CS_LEADS_URL).mock(return_value=httpx.Response(500))
            ok = await patch_lead_structured(
                "+34612345678",
                brief={"trade": "x"},
            )
        assert ok is False


# ============================== get_lead_by_phone =============================


class TestGetLeadByPhone:
    @pytest.mark.asyncio
    async def test_empty_phone_returns_none(self) -> None:
        assert await get_lead_by_phone("") is None

    @pytest.mark.asyncio
    async def test_missing_credentials_returns_none(self) -> None:
        assert await get_lead_by_phone("+34612345678") is None

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(CS_LEADS_URL).mock(return_value=httpx.Response(200, json=[]))
            assert await get_lead_by_phone("+34612345678") is None

    @pytest.mark.asyncio
    async def test_error_returns_none(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(CS_LEADS_URL).mock(return_value=httpx.Response(500))
            assert await get_lead_by_phone("+34612345678") is None

    @pytest.mark.asyncio
    async def test_happy_path_returns_lead(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(CS_LEADS_URL).mock(
                return_value=httpx.Response(200, json=[_row()])
            )
            lead = await get_lead_by_phone("+34612345678")
        assert lead is not None
        assert isinstance(lead, Lead)
        assert lead.id == "lead-1"
        assert lead.name == "Ana"
        assert lead.whatsapp == "+34612345678"
        assert lead.chat_summary == "kitchen reform 15k"
        assert lead.created_at is not None
        # audience preserved as Literal value (dataclass accepts string)
        assert lead.audience == "homeowner"


# ============================== helpers =======================================


class TestRowToLead:
    def test_missing_fields_become_empty_strings(self) -> None:
        lead = _row_to_lead({})
        assert lead.id == ""
        assert lead.name == ""
        assert lead.whatsapp == ""
        assert lead.location == ""
        assert lead.source == ""
        assert lead.chat_summary == ""
        assert lead.chat_history is None
        assert lead.created_at is None


class TestParseTs:
    def test_none_returns_none(self) -> None:
        assert _parse_ts(None) is None

    def test_empty_returns_none(self) -> None:
        assert _parse_ts("") is None

    def test_z_suffix_parsed(self) -> None:
        dt = _parse_ts("2026-04-20T12:00:00Z")
        assert dt is not None
        assert dt.year == 2026

    def test_offset_parsed(self) -> None:
        dt = _parse_ts("2026-04-20T12:00:00+00:00")
        assert dt is not None

    def test_invalid_returns_none(self) -> None:
        assert _parse_ts("not a date") is None

    def test_datetime_instance_passed_through(self) -> None:
        from datetime import datetime, timezone

        src = datetime(2026, 4, 20, tzinfo=timezone.utc)
        assert _parse_ts(src) is src
