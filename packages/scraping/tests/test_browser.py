"""Unit tests for :mod:`scraping.browser` — GDPR selectors, sync helpers.

Playwright itself is not exercised here (that's L2 territory); we only
verify the deterministic pure-logic surface: constants, GDPR dismissal
order, and the presence of the async/sync entry points.
"""
from __future__ import annotations

import asyncio
from typing import Any, List

import pytest

from scraping import (
    DEFAULT_VIEWPORT,
    GDPR_SELECTORS,
    CDP_DEFAULT_PORT,
    browser_context,
    browser_context_sync,
    browser_page,
    browser_page_sync,
    dismiss_gdpr,
    dismiss_gdpr_async,
    persistent_browser,
)


def test_gdpr_selectors_is_tuple_and_non_empty() -> None:
    assert isinstance(GDPR_SELECTORS, tuple)
    assert len(GDPR_SELECTORS) >= 5


def test_gdpr_selectors_contains_spanish_copy() -> None:
    """Spain-biased ordering preserved (audit §1.2 S2)."""

    joined = " ".join(GDPR_SELECTORS).lower()
    assert "aceptar" in joined


def test_default_viewport_shape() -> None:
    assert isinstance(DEFAULT_VIEWPORT, dict)
    assert DEFAULT_VIEWPORT["width"] > 0
    assert DEFAULT_VIEWPORT["height"] > 0


def test_cdp_default_port() -> None:
    assert CDP_DEFAULT_PORT == 9222


def test_entry_points_exist() -> None:
    assert callable(browser_page)
    assert callable(browser_context)
    assert callable(browser_page_sync)
    assert callable(browser_context_sync)
    assert callable(persistent_browser)


class _FakeElement:
    def __init__(self, *, visible: bool, clicked: List[str], selector: str) -> None:
        self._visible = visible
        self._clicked = clicked
        self._selector = selector

    async def is_visible(self) -> bool:
        return self._visible

    async def click(self, timeout: int = 0) -> None:
        self._clicked.append(self._selector)


class _FakePage:
    def __init__(self, visible_selectors: set[str]) -> None:
        self._visible = visible_selectors
        self.clicked: List[str] = []

    async def query_selector(self, selector: str) -> Any:
        present = selector in self._visible
        return _FakeElement(visible=present, clicked=self.clicked, selector=selector)

    async def wait_for_timeout(self, ms: int) -> None:
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_dismiss_gdpr_async_clicks_first_visible() -> None:
    """Order matters: the first visible selector in :data:`GDPR_SELECTORS`
    is the one clicked."""

    page = _FakePage(visible_selectors={GDPR_SELECTORS[1]})
    ok = await dismiss_gdpr_async(page)
    assert ok is True
    assert page.clicked == [GDPR_SELECTORS[1]]


@pytest.mark.asyncio
async def test_dismiss_gdpr_async_returns_false_when_no_banner() -> None:
    page = _FakePage(visible_selectors=set())
    assert await dismiss_gdpr_async(page) is False


class _FakeSyncElement:
    def __init__(self, *, visible: bool, clicked: List[str], selector: str) -> None:
        self._visible = visible
        self._clicked = clicked
        self._selector = selector

    def is_visible(self) -> bool:
        return self._visible

    def click(self, timeout: int = 0) -> None:
        self._clicked.append(self._selector)


class _FakeSyncPage:
    def __init__(self, visible_selectors: set[str]) -> None:
        self._visible = visible_selectors
        self.clicked: List[str] = []

    def query_selector(self, selector: str) -> Any:
        present = selector in self._visible
        return _FakeSyncElement(visible=present, clicked=self.clicked, selector=selector)


def test_dismiss_gdpr_sync_clicks_first_visible() -> None:
    page = _FakeSyncPage(visible_selectors={GDPR_SELECTORS[0]})
    ok = dismiss_gdpr(page)
    assert ok is True
    assert page.clicked == [GDPR_SELECTORS[0]]


def test_dismiss_gdpr_sync_returns_false_when_no_banner() -> None:
    page = _FakeSyncPage(visible_selectors=set())
    assert dismiss_gdpr(page) is False
