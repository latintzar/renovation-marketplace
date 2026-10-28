"""Unit tests for :mod:`scrapers.facebook`."""
from __future__ import annotations

import pytest

from scrapers.facebook import (
    FB_MORE_SELECTORS,
    capture_graphql,
    expand_comments,
)


def test_fb_more_selectors_includes_spanish_copy() -> None:
    joined = " ".join(FB_MORE_SELECTORS).lower()
    assert "ver" in joined  # Spanish variants


def test_fb_more_selectors_non_empty_tuple() -> None:
    assert isinstance(FB_MORE_SELECTORS, tuple)
    assert len(FB_MORE_SELECTORS) >= 4


@pytest.mark.asyncio
async def test_expand_comments_stub_returns_zero() -> None:
    assert await expand_comments(object()) == 0


@pytest.mark.asyncio
async def test_capture_graphql_stub_returns_empty_list() -> None:
    assert await capture_graphql(object()) == []
