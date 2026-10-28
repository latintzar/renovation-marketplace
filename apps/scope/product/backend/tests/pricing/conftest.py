"""Test fixtures for the scope ``pricing`` module.

Moved from ``packages/pricing/tests/`` in Phase 5 Wave 4 alongside the
pricing code itself (``apps/scope/product/backend/pricing/``).
"""
from __future__ import annotations

import pytest

from pricing import config as pricing_config


@pytest.fixture(autouse=True)
def _reset_pricing_config() -> None:
    """Reset process-wide pricing config before and after each test."""

    pricing_config._reset_for_tests()
    yield
    pricing_config._reset_for_tests()
