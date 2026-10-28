"""Scope agent test fixtures.

Moved here from ``packages/messaging/tests/conftest.py`` in Wave 6:
the Leo agent pool is scope-local (``agent.leo._agent_pool``), so
the reset fixture belongs alongside the tests that exercise it.
"""

from __future__ import annotations

from typing import Iterator

import pytest


@pytest.fixture(autouse=True)
def _reset_agent_pool() -> Iterator[None]:
    """Flush the LeoAgent pool before and after each test."""
    try:
        from agent import leo as _la  # type: ignore
    except Exception:
        yield
        return

    if hasattr(_la, "_agent_pool"):
        _la._agent_pool.clear()
    yield
    if hasattr(_la, "_agent_pool"):
        _la._agent_pool.clear()
