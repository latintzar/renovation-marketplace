"""Tests for :mod:`storage.proposals` — ``agent_skill_proposals`` workflow.

Covers:

- :func:`store_proposal` — new-row insert with ``pattern_count`` bumped
  based on sibling pending/draft proposals (auto-cluster by
  ``(skill_name, action)``).
- :func:`get_similar_proposals` — fetch pending + draft siblings,
  newest first.
- :func:`resolve_proposal` — status transitions + ``resolved_at``
  handling (``None`` on draft, now-ISO elsewhere).
- :func:`fetch_pending_proposals` / :func:`fetch_proposal_by_id` —
  list + single-row lookups.
- :func:`resolve_proposal_for_founder` — short-ref resolution, latest
  fallback when no ref given.
- :func:`parse_founder_skill_reply` — pure NL parser, exhaustive on
  approve/reject/defer/unknown classes.
- :func:`proposal_short_id` — 8-hex short ref derivation.

External I/O is mocked with :mod:`respx`; no network ever leaves the
process.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

import httpx
import pytest
import respx

from records.proposals import (
    _row_to_proposal,
    fetch_pending_proposals,
    fetch_proposal_by_id,
    get_similar_proposals,
    parse_founder_skill_reply,
    proposal_short_id,
    resolve_proposal,
    resolve_proposal_for_founder,
    store_proposal,
)
from records.types import Proposal, ProposalResult, SkillReplyIntent


SB_BASE = "http://127.0.0.1:54321"
PROPOSALS_URL = f"{SB_BASE}/rest/v1/agent_skill_proposals"


def _row(**overrides: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "skill_name": "estimate",
        "action": "create",
        "reason": "reason",
        "content": "hello",
        "skill_payload": {"x": 1},
        "status": "pending",
        "pattern_count": 1,
        "similar_proposals": [],
        "conversation_id": None,
        "created_at": "2026-04-20T12:00:00+00:00",
        "resolved_at": None,
    }
    base.update(overrides)
    return base


# ============================== store_proposal ================================


class TestStoreProposal:
    @pytest.mark.asyncio
    async def test_returns_db_not_configured_when_env_missing(self) -> None:
        result = await store_proposal("estimate", "create", "reason")
        assert isinstance(result, ProposalResult)
        assert result.ok is False
        assert result.error == "db_not_configured"

    @pytest.mark.asyncio
    async def test_happy_path_inserts_row(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(return_value=httpx.Response(200, json=[]))
            rx.post(PROPOSALS_URL).mock(
                return_value=httpx.Response(
                    201,
                    json=[_row(id="p-1", pattern_count=1)],
                )
            )
            result = await store_proposal(
                "estimate",
                "create",
                "reason",
                content="hello",
            )
        assert result.ok is True
        assert result.id == "p-1"
        assert result.pattern_count == 1

    @pytest.mark.asyncio
    async def test_clusters_with_siblings_bumps_pattern_count(
        self, supabase_env: None
    ) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(201, json=[_row(id="p-3", pattern_count=3)])

        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(
                return_value=httpx.Response(
                    200,
                    json=[
                        _row(id="p-a", pattern_count=2),
                        _row(id="p-b", pattern_count=1),
                    ],
                )
            )
            rx.post(PROPOSALS_URL).mock(side_effect=_capture)
            result = await store_proposal("estimate", "create", "reason")
        assert result.ok is True
        # pattern_count = max(existing pattern_counts) + 1 = 3
        assert captured["pattern_count"] == 3
        assert set(captured["similar_proposals"]) == {"p-a", "p-b"}

    @pytest.mark.asyncio
    async def test_truncates_content_to_10000(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(201, json=[_row()])

        content = "x" * 20000
        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(return_value=httpx.Response(200, json=[]))
            rx.post(PROPOSALS_URL).mock(side_effect=_capture)
            await store_proposal(
                "estimate",
                "create",
                "reason",
                content=content,
            )
        assert len(captured["content"]) == 10000

    @pytest.mark.asyncio
    async def test_status_is_always_pending_on_insert(
        self, supabase_env: None
    ) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(201, json=[_row()])

        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(return_value=httpx.Response(200, json=[]))
            rx.post(PROPOSALS_URL).mock(side_effect=_capture)
            await store_proposal("estimate", "create", "reason")
        assert captured["status"] == "pending"

    @pytest.mark.asyncio
    async def test_insert_5xx_returns_error(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(return_value=httpx.Response(200, json=[]))
            rx.post(PROPOSALS_URL).mock(return_value=httpx.Response(500, text="boom"))
            result = await store_proposal("estimate", "create", "reason")
        assert result.ok is False
        assert result.error == "insert_failed_500"

    @pytest.mark.asyncio
    async def test_network_error_swallowed(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(return_value=httpx.Response(200, json=[]))
            rx.post(PROPOSALS_URL).mock(side_effect=httpx.ConnectError("down"))
            result = await store_proposal("estimate", "create", "reason")
        assert result.ok is False
        assert "down" in (result.error or "")


# ========================= get_similar_proposals ==============================


class TestGetSimilarProposals:
    @pytest.mark.asyncio
    async def test_missing_env_returns_empty(self) -> None:
        assert await get_similar_proposals("skill", "create") == []

    @pytest.mark.asyncio
    async def test_happy_path_returns_parsed_rows(
        self, supabase_env: None
    ) -> None:
        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(
                return_value=httpx.Response(
                    200,
                    json=[_row(id="x"), _row(id="y", pattern_count=2)],
                )
            )
            rows = await get_similar_proposals("estimate", "create")
        assert len(rows) == 2
        assert all(isinstance(p, Proposal) for p in rows)
        assert rows[0].id == "x"
        assert rows[1].pattern_count == 2

    @pytest.mark.asyncio
    async def test_5xx_returns_empty_list(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(return_value=httpx.Response(500))
            assert await get_similar_proposals("estimate", "create") == []

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(side_effect=httpx.ConnectError("nope"))
            assert await get_similar_proposals("estimate", "create") == []


# ============================= resolve_proposal ===============================


class TestResolveProposal:
    @pytest.mark.asyncio
    async def test_empty_id_returns_false(self, supabase_env: None) -> None:
        assert await resolve_proposal("", "approved") is False

    @pytest.mark.asyncio
    async def test_missing_env_returns_false(self) -> None:
        assert await resolve_proposal("id-1", "approved") is False

    @pytest.mark.asyncio
    async def test_approved_sets_resolved_at(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(204)

        async with respx.mock() as rx:
            rx.patch(PROPOSALS_URL).mock(side_effect=_capture)
            ok = await resolve_proposal("id-1", "approved")
        assert ok is True
        assert captured["status"] == "approved"
        assert isinstance(captured["resolved_at"], str)
        # parseable as ISO-8601
        datetime.fromisoformat(captured["resolved_at"])

    @pytest.mark.asyncio
    async def test_draft_clears_resolved_at(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(204)

        async with respx.mock() as rx:
            rx.patch(PROPOSALS_URL).mock(side_effect=_capture)
            ok = await resolve_proposal("id-1", "draft")
        assert ok is True
        assert captured["status"] == "draft"
        assert captured["resolved_at"] is None

    @pytest.mark.asyncio
    async def test_non_2xx_returns_false(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.patch(PROPOSALS_URL).mock(return_value=httpx.Response(500))
            assert await resolve_proposal("id-1", "approved") is False


# ========================== fetch_pending_proposals ===========================


class TestFetchPending:
    @pytest.mark.asyncio
    async def test_missing_env_returns_empty(self) -> None:
        assert await fetch_pending_proposals() == []

    @pytest.mark.asyncio
    async def test_happy_path_returns_proposals(
        self, supabase_env: None
    ) -> None:
        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(
                return_value=httpx.Response(
                    200,
                    json=[_row(id="p-new"), _row(id="p-old")],
                )
            )
            rows = await fetch_pending_proposals(limit=40)
        assert [r.id for r in rows] == ["p-new", "p-old"]

    @pytest.mark.asyncio
    async def test_5xx_returns_empty(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(return_value=httpx.Response(500))
            assert await fetch_pending_proposals() == []


# ========================== fetch_proposal_by_id ==============================


class TestFetchById:
    @pytest.mark.asyncio
    async def test_empty_id_returns_none(self, supabase_env: None) -> None:
        assert await fetch_proposal_by_id("") is None

    @pytest.mark.asyncio
    async def test_missing_env_returns_none(self) -> None:
        assert await fetch_proposal_by_id("id-1") is None

    @pytest.mark.asyncio
    async def test_found_returns_proposal(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(
                return_value=httpx.Response(200, json=[_row(id="found")])
            )
            result = await fetch_proposal_by_id("found")
        assert result is not None
        assert result.id == "found"

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(return_value=httpx.Response(200, json=[]))
            assert await fetch_proposal_by_id("missing") is None


# ====================== resolve_proposal_for_founder ==========================


class TestResolveForFounder:
    @pytest.mark.asyncio
    async def test_no_pending_returns_none(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(return_value=httpx.Response(200, json=[]))
            assert await resolve_proposal_for_founder(None) is None

    @pytest.mark.asyncio
    async def test_no_short_opt_returns_latest(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(
                return_value=httpx.Response(
                    200,
                    json=[
                        _row(id="aaaabbbb-0000-0000-0000-000000000001"),
                        _row(id="ccccdddd-0000-0000-0000-000000000002"),
                    ],
                )
            )
            result = await resolve_proposal_for_founder(None)
        assert result is not None
        # latest = first row (newest first)
        assert proposal_short_id(result.id) == "aaaabbbb"

    @pytest.mark.asyncio
    async def test_matching_short_ref_returns_that_row(
        self, supabase_env: None
    ) -> None:
        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(
                return_value=httpx.Response(
                    200,
                    json=[
                        _row(id="aaaabbbb-0000-0000-0000-000000000001"),
                        _row(id="ccccdddd-0000-0000-0000-000000000002"),
                    ],
                )
            )
            result = await resolve_proposal_for_founder("ccccdddd")
        assert result is not None
        assert proposal_short_id(result.id) == "ccccdddd"

    @pytest.mark.asyncio
    async def test_unmatched_short_ref_returns_none(
        self, supabase_env: None
    ) -> None:
        async with respx.mock() as rx:
            rx.get(PROPOSALS_URL).mock(
                return_value=httpx.Response(
                    200,
                    json=[_row(id="aaaabbbb-0000-0000-0000-000000000001")],
                )
            )
            assert await resolve_proposal_for_founder("99999999") is None


# ========================= parse_founder_skill_reply ==========================


class TestParseFounderSkillReply:
    @pytest.mark.parametrize("word", ["yes", "approve", "ok", "yep", "apply"])
    def test_approve_variants(self, word: str) -> None:
        intent = parse_founder_skill_reply(f"{word} abc12345")
        assert intent.action == "approve"
        assert intent.short_ref == "abc12345"

    @pytest.mark.parametrize("word", ["no", "reject", "nope", "deny"])
    def test_reject_variants(self, word: str) -> None:
        intent = parse_founder_skill_reply(f"{word} abc12345")
        assert intent.action == "reject"
        assert intent.short_ref == "abc12345"

    @pytest.mark.parametrize("word", ["wait", "draft", "hold", "later", "pause"])
    def test_defer_variants(self, word: str) -> None:
        intent = parse_founder_skill_reply(f"{word} abc12345")
        assert intent.action == "defer"
        assert intent.short_ref == "abc12345"

    def test_not_yet_is_defer(self) -> None:
        intent = parse_founder_skill_reply("not yet abc12345")
        assert intent.action == "defer"
        assert intent.short_ref == "abc12345"

    def test_bare_not_yet_defers_without_ref(self) -> None:
        intent = parse_founder_skill_reply("not yet")
        assert intent.action == "defer"
        assert intent.short_ref is None

    def test_short_ref_rejects_non_hex(self) -> None:
        intent = parse_founder_skill_reply("yes hello")
        assert intent.action == "approve"
        assert intent.short_ref is None

    def test_short_ref_rejects_over_8(self) -> None:
        intent = parse_founder_skill_reply("yes abcdef123456789")
        assert intent.action == "approve"
        assert intent.short_ref is None

    def test_smart_quotes_stripped(self) -> None:
        intent = parse_founder_skill_reply("\u201cyes\u201d abc12345")
        assert intent.action == "approve"
        assert intent.short_ref == "abc12345"

    def test_stars_stripped(self) -> None:
        intent = parse_founder_skill_reply("*yes* abc12345")
        assert intent.action == "approve"

    def test_empty_returns_unknown(self) -> None:
        intent = parse_founder_skill_reply("")
        assert intent.action == "unknown"

    def test_whitespace_returns_unknown(self) -> None:
        assert parse_founder_skill_reply("    ").action == "unknown"

    def test_over_120_chars_returns_unknown_with_raw(self) -> None:
        raw = "yes " + ("x" * 200)
        intent = parse_founder_skill_reply(raw)
        assert intent.action == "unknown"
        assert intent.raw == raw

    def test_unknown_keyword_returns_unknown(self) -> None:
        intent = parse_founder_skill_reply("magical")
        assert intent.action == "unknown"

    def test_raw_preserved_verbatim(self) -> None:
        intent = parse_founder_skill_reply("   Yes abc12345  ")
        assert intent.raw == "   Yes abc12345  "
        assert isinstance(intent, SkillReplyIntent)


# ============================ proposal_short_id ==============================


class TestProposalShortId:
    def test_basic_8_hex(self) -> None:
        assert (
            proposal_short_id("aaaabbbb-0000-0000-0000-000000000000")
            == "aaaabbbb"
        )

    def test_lowercases(self) -> None:
        assert (
            proposal_short_id("AAAABBBB-0000-0000-0000-000000000000")
            == "aaaabbbb"
        )

    def test_no_dashes(self) -> None:
        assert proposal_short_id("aaaabbbb00000000") == "aaaabbbb"

    def test_empty_returns_empty(self) -> None:
        assert proposal_short_id("") == ""


# ============================== _row_to_proposal ==============================


class TestRowToProposal:
    def test_action_falls_back_to_create_on_unknown(self) -> None:
        row = _row(action="not-a-valid-action")
        proposal = _row_to_proposal(row)
        assert proposal.action == "create"

    def test_status_falls_back_to_pending(self) -> None:
        proposal = _row_to_proposal(_row(status="hobbit"))
        assert proposal.status == "pending"

    def test_similar_proposals_coerces_nonlist(self) -> None:
        proposal = _row_to_proposal(_row(similar_proposals="not-a-list"))
        assert proposal.similar_proposals == []

    def test_similar_proposals_stringifies(self) -> None:
        proposal = _row_to_proposal(_row(similar_proposals=[1, 2, "x"]))
        assert proposal.similar_proposals == ["1", "2", "x"]

    def test_pattern_count_coerces(self) -> None:
        proposal = _row_to_proposal(_row(pattern_count="7"))
        assert proposal.pattern_count == 7

    def test_skill_payload_non_dict_becomes_empty_dict(self) -> None:
        proposal = _row_to_proposal(_row(skill_payload="string"))
        assert proposal.skill_payload == {}

    def test_missing_fields_safe_defaults(self) -> None:
        proposal = _row_to_proposal({})
        assert proposal.id == ""
        assert proposal.skill_name == ""
        assert proposal.reason == ""
        assert proposal.content is None
        assert proposal.status == "pending"
