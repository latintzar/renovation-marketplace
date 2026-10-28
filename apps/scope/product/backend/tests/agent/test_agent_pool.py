"""Agent pool TTL eviction + conversation key derivation.

Post-Wave-6: the Leo agent runtime lives in ``apps/scope/product/backend/agent/``
(``agent.leo``), not in the shared ``packages/messaging``. This test
exercises scope-local policy.
"""

from __future__ import annotations

import time

import pytest

from agent import evict_stale_agents


def test_evict_empty_pool_returns_zero() -> None:
    assert evict_stale_agents() == 0


def test_evict_removes_stale_entries(monkeypatch) -> None:
    from agent import leo as la

    la._agent_pool["fake-stale"] = ("agent", time.time() - 7200)
    la._agent_pool["fake-fresh"] = ("agent", time.time())

    evicted = evict_stale_agents()
    assert evicted == 1
    assert "fake-stale" not in la._agent_pool
    assert "fake-fresh" in la._agent_pool


def test_phone_key_normalises_phone() -> None:
    from agent.leo import _phone_key

    assert _phone_key("+34 600 000 000") == _phone_key("34600000000")
    assert _phone_key("whatsapp:+34600000000") == _phone_key("34600000000")
