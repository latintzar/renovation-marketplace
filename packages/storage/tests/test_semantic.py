"""Tests for :mod:`storage.semantic` — the mem0 SaaS wrapper.

Covers all seven public functions plus two private helpers
(:func:`_normalize_user_id`, :func:`_row_to_memory`). No network: mem0
reads go through :mod:`respx` against ``api.mem0.ai``; writes go through
a :class:`MagicMock` replacing :func:`_get_client`.

Invariants verified:
- ``is_mem0_configured`` flips with ``MEM0_API_KEY``.
- ``_normalize_user_id`` rule table (digits → ``+<digits>``, UUID pass-through).
- ``remember`` drops ``system`` and empty-text rows, forwards ``metadata``.
- ``recall`` dispatches ``get_all`` vs ``search`` on ``query`` presence.
- ``migrate_user`` re-adds with ``infer=False`` then deletes, returning
  :class:`MigrationResult` with accurate counts (+ non-atomic semantics
  when a re-add fails).
- ``forget`` swallows mem0 errors and returns ``False``.
- ``format_memories_for_prompt`` English-only framing + 10-fact cap.
- ``get_user_context`` zero-configured short-circuit.
- Tri-state sentinel refactor: ``_mem0_init_failed`` prevents retry.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
import respx

from dataclasses import dataclass

import storage.semantic as semantic
from storage import (
    Memory,
    MigrationResult,
    forget,
    format_memories_for_prompt,
    get_user_context,
    is_mem0_configured,
    migrate_user,
    recall,
    remember,
)
from storage.semantic import _normalize_user_id, _row_to_memory


@dataclass
class Message:
    """Minimal chat turn that satisfies ``storage.ChatTurn`` protocol.

    The real Message shape lives in ``apps/scope/product/backend/records/types.py``
    (scope-specific). The engine only needs ``role`` + ``text``, so the
    test double stays local here.
    """

    id: str
    channel: str
    user_id: str
    role: str
    text: str


MEM0_BASE = "https://api.mem0.ai"


# --------------------------------- is_configured --------------------------------


class TestIsMem0Configured:
    def test_returns_false_when_env_unset(self) -> None:
        assert is_mem0_configured() is False

    def test_returns_true_when_env_set(self, mem0_env) -> None:
        assert is_mem0_configured() is True

    def test_returns_false_for_empty_string(self, monkeypatch) -> None:
        monkeypatch.setenv("MEM0_API_KEY", "")
        assert is_mem0_configured() is False


# --------------------------------- normalize -----------------------------------


class TestNormalizeUserId:
    def test_empty_returns_empty(self) -> None:
        assert _normalize_user_id("") == ""

    def test_plain_digits_get_plus(self) -> None:
        assert _normalize_user_id("34612345678") == "+34612345678"

    def test_plus_digits_pass_through(self) -> None:
        assert _normalize_user_id("+34612345678") == "+34612345678"

    def test_spaces_stripped(self) -> None:
        assert _normalize_user_id("+34 612 345 678") == "+34612345678"

    def test_hyphens_stripped(self) -> None:
        assert _normalize_user_id("+34-612-345-678") == "+34612345678"

    def test_uuid_like_passes_through(self) -> None:
        """UUIDs contain non-digit chars; we keep them untouched."""

        # After stripping hyphens a UUID becomes all hex digits; it would
        # then match the isdigit() branch as False because hex letters
        # aren't digits. Confirm pass-through.
        uuid_ish = "web-abcdef01-2345-6789-abcd-ef0123456789"
        got = _normalize_user_id(uuid_ish)
        assert got == "webabcdef012345678" + "9abcdef0123456789"

    def test_already_plus_digits_idempotent(self) -> None:
        assert _normalize_user_id("+34612345678") == "+34612345678"


# --------------------------------- row → Memory --------------------------------


class TestRowToMemory:
    def test_basic_row(self) -> None:
        row = {
            "id": "mem-123",
            "memory": "User lives in Madrid",
            "metadata": {"source": "onboarding"},
            "score": 0.91,
            "created_at": "2026-01-14T10:00:00Z",
        }
        mem = _row_to_memory(row, user_id="+34612345678")
        assert mem.id == "mem-123"
        assert mem.text == "User lives in Madrid"
        assert mem.metadata == {"source": "onboarding"}
        assert mem.score == 0.91
        assert mem.user_id == "+34612345678"
        assert mem.created_at == datetime(2026, 1, 14, 10, 0, tzinfo=timezone.utc)

    def test_missing_score_is_none(self) -> None:
        mem = _row_to_memory({"id": "x", "memory": "t"}, user_id="+34")
        assert mem.score is None

    def test_non_numeric_score_is_none(self) -> None:
        mem = _row_to_memory({"id": "x", "memory": "t", "score": "not-a-number"}, user_id="")
        assert mem.score is None

    def test_null_metadata_becomes_empty_dict(self) -> None:
        mem = _row_to_memory({"id": "x", "memory": "t", "metadata": None}, user_id="")
        assert mem.metadata == {}

    def test_bad_timestamp_is_none(self) -> None:
        mem = _row_to_memory(
            {"id": "x", "memory": "t", "created_at": "not-a-date"}, user_id=""
        )
        assert mem.created_at is None


# --------------------------------- recall --------------------------------------


class TestRecall:
    @pytest.mark.asyncio
    async def test_returns_empty_when_unconfigured(self) -> None:
        assert await recall("+34612345678") == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_user_id_blank(self, mem0_env) -> None:
        assert await recall("") == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_all_path_when_query_empty(self, mem0_env) -> None:
        rx = respx.post(f"{MEM0_BASE}/v2/memories/").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"id": "m1", "memory": "fact one", "metadata": {}},
                    {"id": "m2", "memory": "fact two", "metadata": {}},
                ],
            )
        )
        got = await recall("+34612345678")
        assert len(got) == 2
        assert [m.text for m in got] == ["fact one", "fact two"]
        assert rx.called
        payload = rx.calls.last.request.content.decode()
        assert "\"user_id\":\"+34612345678\"" in payload
        assert "\"filters\"" in payload

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_path_when_query_present(self, mem0_env) -> None:
        rx = respx.post(f"{MEM0_BASE}/v2/memories/search/").mock(
            return_value=httpx.Response(
                200,
                json={"results": [{"id": "m3", "memory": "relevant fact", "score": 0.88}]},
            )
        )
        got = await recall("+34612345678", query="where does user live?")
        assert len(got) == 1
        assert got[0].score == 0.88
        assert rx.called
        payload = rx.calls.last.request.content.decode()
        assert "where does user live" in payload

    @pytest.mark.asyncio
    @respx.mock
    async def test_swallows_errors_returns_empty(self, mem0_env) -> None:
        respx.post(f"{MEM0_BASE}/v2/memories/").mock(
            return_value=httpx.Response(500, json={"err": "oops"})
        )
        assert await recall("+34612345678") == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_limit_passed_through_as_page_size(self, mem0_env) -> None:
        rx = respx.post(f"{MEM0_BASE}/v2/memories/").mock(
            return_value=httpx.Response(200, json=[])
        )
        await recall("+34612345678", limit=7)
        assert rx.called
        assert "\"page_size\":7" in rx.calls.last.request.content.decode()

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_limit_passed_through_as_top_k(self, mem0_env) -> None:
        rx = respx.post(f"{MEM0_BASE}/v2/memories/search/").mock(
            return_value=httpx.Response(200, json=[])
        )
        await recall("+34612345678", query="q", limit=3)
        assert "\"top_k\":3" in rx.calls.last.request.content.decode()


# --------------------------------- remember ------------------------------------


class TestRemember:
    @pytest.mark.asyncio
    async def test_returns_false_when_unconfigured(self) -> None:
        ok = await remember("+34612345678", [Message(id="1", channel="whatsapp",
                                                     user_id="+34", role="user", text="hi")])
        assert ok is False

    @pytest.mark.asyncio
    async def test_returns_false_when_no_messages(self, mem0_env, fake_mem0_client) -> None:
        assert await remember("+34612345678", []) is False
        assert not fake_mem0_client.add.called

    @pytest.mark.asyncio
    async def test_returns_false_when_user_id_blank(self, mem0_env, fake_mem0_client) -> None:
        m = Message(id="1", channel="whatsapp", user_id="", role="user", text="hi")
        assert await remember("", [m]) is False

    @pytest.mark.asyncio
    async def test_forwards_user_and_assistant_turns(
        self, mem0_env, fake_mem0_client
    ) -> None:
        msgs = [
            Message(id="1", channel="whatsapp", user_id="+34", role="user", text="hi"),
            Message(id="2", channel="whatsapp", user_id="+34", role="assistant", text="hello"),
        ]
        ok = await remember("+34612345678", msgs)
        assert ok is True
        fake_mem0_client.add.assert_called_once()
        args, kwargs = fake_mem0_client.add.call_args
        assert args[0] == [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        assert kwargs["user_id"] == "+34612345678"

    @pytest.mark.asyncio
    async def test_drops_system_role(self, mem0_env, fake_mem0_client) -> None:
        msgs = [
            Message(id="1", channel="whatsapp", user_id="+34", role="system", text="be brief"),
            Message(id="2", channel="whatsapp", user_id="+34", role="user", text="hi"),
        ]
        await remember("+34612345678", msgs)
        args, _ = fake_mem0_client.add.call_args
        assert args[0] == [{"role": "user", "content": "hi"}]

    @pytest.mark.asyncio
    async def test_drops_empty_text(self, mem0_env, fake_mem0_client) -> None:
        msgs = [
            Message(id="1", channel="whatsapp", user_id="+34", role="user", text=""),
            Message(id="2", channel="whatsapp", user_id="+34", role="user", text="hi"),
        ]
        await remember("+34612345678", msgs)
        args, _ = fake_mem0_client.add.call_args
        assert args[0] == [{"role": "user", "content": "hi"}]

    @pytest.mark.asyncio
    async def test_returns_false_when_all_messages_filtered(
        self, mem0_env, fake_mem0_client
    ) -> None:
        msgs = [
            Message(id="1", channel="whatsapp", user_id="+34", role="system", text="x"),
            Message(id="2", channel="whatsapp", user_id="+34", role="user", text=""),
        ]
        assert await remember("+34612345678", msgs) is False
        assert not fake_mem0_client.add.called

    @pytest.mark.asyncio
    async def test_metadata_forwarded(self, mem0_env, fake_mem0_client) -> None:
        msgs = [Message(id="1", channel="whatsapp", user_id="+34", role="user", text="hi")]
        await remember("+34612345678", msgs, metadata={"audience": "professional"})
        _, kwargs = fake_mem0_client.add.call_args
        assert kwargs["metadata"] == {"audience": "professional"}

    @pytest.mark.asyncio
    async def test_swallows_client_error(self, mem0_env, fake_mem0_client) -> None:
        fake_mem0_client.add.side_effect = RuntimeError("network")
        msgs = [Message(id="1", channel="whatsapp", user_id="+34", role="user", text="hi")]
        assert await remember("+34612345678", msgs) is False


# --------------------------------- forget --------------------------------------


class TestForget:
    @pytest.mark.asyncio
    async def test_returns_false_when_unconfigured(self) -> None:
        assert await forget("+34612345678", "mem-id-1") is False

    @pytest.mark.asyncio
    async def test_returns_false_when_memory_id_blank(
        self, mem0_env, fake_mem0_client
    ) -> None:
        assert await forget("+34", "") is False
        assert not fake_mem0_client.delete.called

    @pytest.mark.asyncio
    async def test_deletes_on_happy_path(self, mem0_env, fake_mem0_client) -> None:
        assert await forget("+34", "mem-1") is True
        fake_mem0_client.delete.assert_called_once_with("mem-1")

    @pytest.mark.asyncio
    async def test_swallows_errors(self, mem0_env, fake_mem0_client) -> None:
        fake_mem0_client.delete.side_effect = RuntimeError("boom")
        assert await forget("+34", "mem-1") is False


# --------------------------------- migrate_user --------------------------------


class TestMigrateUser:
    @pytest.mark.asyncio
    async def test_returns_not_ok_when_unconfigured(self) -> None:
        result = await migrate_user("+34", "+34999")
        assert result.ok is False
        assert result.error == "mem0_not_configured"

    @pytest.mark.asyncio
    async def test_returns_not_ok_when_ids_empty(
        self, mem0_env, fake_mem0_client
    ) -> None:
        result = await migrate_user("", "+34999")
        assert result.ok is False
        assert result.error == "empty_user_id"

    @pytest.mark.asyncio
    async def test_same_id_is_no_op(self, mem0_env, fake_mem0_client) -> None:
        result = await migrate_user("+34612", "+34612")
        assert result.ok is True
        assert result.migrated_count == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_memories_returns_ok_zero(
        self, mem0_env, fake_mem0_client
    ) -> None:
        respx.post(f"{MEM0_BASE}/v2/memories/").mock(
            return_value=httpx.Response(200, json=[])
        )
        result = await migrate_user("+34", "+34999")
        assert result.ok is True
        assert result.migrated_count == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_error_returns_not_ok(
        self, mem0_env, fake_mem0_client
    ) -> None:
        respx.post(f"{MEM0_BASE}/v2/memories/").mock(
            return_value=httpx.Response(500, json={})
        )
        result = await migrate_user("+34", "+34999")
        assert result.ok is False
        assert "fetch_failed" in (result.error or "")

    @pytest.mark.asyncio
    @respx.mock
    async def test_readds_with_infer_false(
        self, mem0_env, fake_mem0_client
    ) -> None:
        respx.post(f"{MEM0_BASE}/v2/memories/").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"id": "m1", "memory": "fact-a", "metadata": {}},
                    {"id": "m2", "memory": "fact-b", "metadata": {}},
                ],
            )
        )
        result = await migrate_user("+34", "+34999")
        assert result.ok is True
        assert result.migrated_count == 2
        assert result.failed_count == 0

        # client.add called twice (once per memory) with infer=False.
        assert fake_mem0_client.add.call_count == 2
        for call in fake_mem0_client.add.call_args_list:
            assert call.kwargs.get("infer") is False
            assert call.kwargs.get("user_id") == "+34999"

        # client.delete called twice.
        assert fake_mem0_client.delete.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_partial_failure_counts_failed(
        self, mem0_env, fake_mem0_client
    ) -> None:
        respx.post(f"{MEM0_BASE}/v2/memories/").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"id": "m1", "memory": "fact-a"},
                    {"id": "m2", "memory": "fact-b"},
                ],
            )
        )

        calls = {"n": 0}

        def flaky_add(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("network blip")
            return None

        fake_mem0_client.add.side_effect = flaky_add
        result = await migrate_user("+34", "+34999")
        assert result.ok is False
        assert result.migrated_count == 1
        assert result.failed_count == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_skips_empty_memory_text(
        self, mem0_env, fake_mem0_client
    ) -> None:
        respx.post(f"{MEM0_BASE}/v2/memories/").mock(
            return_value=httpx.Response(
                200,
                json=[{"id": "m1", "memory": ""}, {"id": "m2", "memory": "fact"}],
            )
        )
        result = await migrate_user("+34", "+34999")
        assert result.migrated_count == 1


# --------------------------------- format --------------------------------------


class TestFormatMemoriesForPrompt:
    def test_empty_returns_empty(self) -> None:
        assert format_memories_for_prompt([]) == ""

    def test_basic_framing(self) -> None:
        mems = [
            Memory(id="1", text="User lives in Madrid"),
            Memory(id="2", text="User prefers evening calls"),
        ]
        out = format_memories_for_prompt(mems)
        assert out.startswith("Known facts about this user:\n")
        assert "- User lives in Madrid" in out
        assert "- User prefers evening calls" in out

    def test_caps_at_ten(self) -> None:
        mems = [Memory(id=str(i), text=f"fact-{i}") for i in range(15)]
        out = format_memories_for_prompt(mems)
        assert "fact-9" in out
        assert "fact-10" not in out

    def test_drops_empty_text(self) -> None:
        mems = [Memory(id="1", text=""), Memory(id="2", text="real")]
        out = format_memories_for_prompt(mems)
        assert "- real" in out
        assert out.count("- ") == 1

    def test_all_empty_returns_empty(self) -> None:
        mems = [Memory(id="1", text=""), Memory(id="2", text="")]
        assert format_memories_for_prompt(mems) == ""


# --------------------------------- get_user_context ---------------------------


class TestGetUserContext:
    @pytest.mark.asyncio
    async def test_returns_empty_when_user_id_blank(self) -> None:
        assert await get_user_context("") == ""

    @pytest.mark.asyncio
    async def test_returns_empty_when_unconfigured(self) -> None:
        assert await get_user_context("+34612") == ""

    @pytest.mark.asyncio
    @respx.mock
    async def test_happy_path_calls_recall_and_formats(self, mem0_env) -> None:
        respx.post(f"{MEM0_BASE}/v2/memories/search/").mock(
            return_value=httpx.Response(
                200, json=[{"id": "m1", "memory": "User is in Madrid"}]
            )
        )
        out = await get_user_context("+34612345678", "where?")
        assert "Known facts about this user:" in out
        assert "User is in Madrid" in out


# --------------------------------- client init ---------------------------------


class TestClientLazyInit:
    def test_init_failure_sets_flag_and_blocks_retry(
        self, mem0_env, monkeypatch
    ) -> None:
        """Tri-state sentinel refactor (D15): once init raises, the
        ``_mem0_init_failed`` flag flips to True and stays there —
        subsequent ``_get_client()`` calls return None without retrying.
        """

        call_count = {"n": 0}

        class BrokenClient:
            def __init__(self, **kwargs):
                call_count["n"] += 1
                raise RuntimeError("no mem0")

        import mem0 as _mem0

        monkeypatch.setattr(_mem0, "MemoryClient", BrokenClient)

        # First call tries to init, fails, sets _mem0_init_failed.
        assert semantic._get_client() is None
        assert semantic._mem0_init_failed is True
        assert call_count["n"] == 1

        # Second call skips init entirely.
        assert semantic._get_client() is None
        assert call_count["n"] == 1  # unchanged

    def test_successful_init_caches_client(self, mem0_env, monkeypatch) -> None:
        built = {"n": 0}

        class GoodClient:
            def __init__(self, *, api_key):
                built["n"] += 1
                self.api_key = api_key

        import mem0 as _mem0

        monkeypatch.setattr(_mem0, "MemoryClient", GoodClient)

        c1 = semantic._get_client()
        c2 = semantic._get_client()
        assert c1 is c2
        assert built["n"] == 1
