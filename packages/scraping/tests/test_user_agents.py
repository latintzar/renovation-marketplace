"""Unit tests for :mod:`scraping.user_agents`."""
from __future__ import annotations

import pytest

from scraping import (
    DESKTOP_USER_AGENTS,
    MOBILE_USER_AGENTS,
    USER_AGENTS,
    pick_desktop,
    pick_mobile,
    pick_user_agent,
)


def test_desktop_mobile_disjoint() -> None:
    """Mobile UAs must not appear in desktop pool (D12)."""

    assert not (set(DESKTOP_USER_AGENTS) & set(MOBILE_USER_AGENTS))


def test_full_pool_is_concat() -> None:
    assert len(USER_AGENTS) == len(DESKTOP_USER_AGENTS) + len(MOBILE_USER_AGENTS)
    for ua in DESKTOP_USER_AGENTS:
        assert ua in USER_AGENTS
    for ua in MOBILE_USER_AGENTS:
        assert ua in USER_AGENTS


def test_non_empty_pools() -> None:
    assert len(USER_AGENTS) > 0
    assert len(DESKTOP_USER_AGENTS) > 0
    assert len(MOBILE_USER_AGENTS) > 0


def test_pick_user_agent_returns_pool_member() -> None:
    for _ in range(20):
        assert pick_user_agent() in USER_AGENTS


def test_pick_desktop_returns_desktop() -> None:
    for _ in range(20):
        assert pick_desktop() in DESKTOP_USER_AGENTS


def test_pick_mobile_returns_mobile() -> None:
    for _ in range(20):
        assert pick_mobile() in MOBILE_USER_AGENTS


@pytest.mark.parametrize("pool", [USER_AGENTS, DESKTOP_USER_AGENTS, MOBILE_USER_AGENTS])
def test_pool_entries_look_like_uas(pool) -> None:
    """Every UA starts with ``Mozilla/5.0`` — the canonical shape."""

    assert all(ua.startswith("Mozilla/5.0") for ua in pool)
