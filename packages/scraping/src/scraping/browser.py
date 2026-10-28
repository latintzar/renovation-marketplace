"""Playwright session helpers — browser_page / browser_context (D4).

This module is the single home for Chromium automation across the
monorepo. Four public context-managers (async + sync, page + context)
share the same knobs: cookies, user-agent, viewport, storage_state,
anti-detection launch args.

CDP-first convention (D4, Decision C): the default still cold-starts
a new Chromium; the CDP path (attach to a pre-existing Chrome on
:9222) is exposed via an explicit ``persistent_browser`` helper so
adapters that need the fast path know they're taking it. A future
``prefer_cdp`` flag on ``browser_page`` is design-only pending a
benchmark.

GDPR dismissal is deliberately click-first-visible (audit §1.2 S2 —
Spain-biased; 3 of 7 selectors are Spanish-language). That
preservation is the whole point: the real world is ES-heavy, and
English/French selectors remain at the top of the list for dual-market
future-work. The helper is best-effort: one visible match wins,
everything else is silently swallowed.

Lazy Playwright imports: every entry point imports
``playwright.{async,sync}_api`` at call-time, not module scope, so
``import scraping`` doesn't drag in Playwright on hosts that don't
need it (CI runners, Vercel edge, etc.).
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncIterator, Iterator, List, Optional

from .user_agents import pick_user_agent

logger = logging.getLogger(__name__)

__all__ = [
    "GDPR_SELECTORS",
    "DEFAULT_VIEWPORT",
    "browser_page",
    "browser_context",
    "browser_page_sync",
    "browser_context_sync",
    "dismiss_gdpr",
    "dismiss_gdpr_async",
    "persistent_browser",
    "CDP_DEFAULT_PORT",
]


GDPR_SELECTORS: tuple[str, ...] = (
    "button#didomi-notice-agree-button",
    'button:has-text("Aceptar")',
    'button:has-text("Accept all")',
    'button:has-text("Aceptar todo")',
    'button:has-text("Aceptar y continuar")',
    '[data-testid="cookie-accept"]',
    ".cookie-consent-accept",
)
"""Click-first-visible GDPR pool (Smell D consolidation).

Ordered roughly by prevalence on Spain-served pages (Didomi is the
most common banner vendor), but the loop body is best-effort so
ordering only matters at the margin.
"""


DEFAULT_VIEWPORT: dict = {"width": 1280, "height": 900}
"""Canonical Leo viewport. Large enough for most desktop layouts,
small enough for GitHub Actions' standard runners."""


CDP_DEFAULT_PORT = 9222
"""Default Chrome DevTools Protocol port (`puedo-vnc-browser` service)."""


@asynccontextmanager
async def browser_context(
    cookies: Optional[List[dict]] = None,
    user_agent: Optional[str] = None,
    viewport: Optional[dict] = None,
    headless: bool = True,
    storage_state: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
) -> AsyncIterator[Any]:
    """Async Playwright ``BrowserContext`` for multi-page sessions.

    Use this when one "session" spans many pages (a crawler opening
    30 profile URLs under one cookie jar). For a single page, call
    :func:`browser_page` instead.

    ``cookies`` and ``storage_state`` are mutually exclusive at the
    intent level — when both are passed, ``storage_state`` wins and
    ``cookies`` is silently dropped (audit §1.1 I2). That behaviour
    is preserved; tests assert it.
    """

    from playwright.async_api import async_playwright

    ua = user_agent or pick_user_agent()
    vp = viewport or DEFAULT_VIEWPORT
    launch_args = extra_args or []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=launch_args)
        ctx_kwargs: dict = {"user_agent": ua, "viewport": vp}
        if storage_state:
            ctx_kwargs["storage_state"] = storage_state
        ctx = await browser.new_context(**ctx_kwargs)

        if cookies and not storage_state:
            await ctx.add_cookies(cookies)

        try:
            yield ctx
        finally:
            await browser.close()


@asynccontextmanager
async def browser_page(
    cookies: Optional[List[dict]] = None,
    user_agent: Optional[str] = None,
    viewport: Optional[dict] = None,
    headless: bool = True,
    auto_dismiss_gdpr: bool = True,
    storage_state: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
) -> AsyncIterator[Any]:
    """Async Playwright ``Page`` with sensible defaults.

    ``auto_dismiss_gdpr`` is purely advisory here — the GDPR banner is
    page-content, and you must navigate *before* calling
    :func:`dismiss_gdpr_async`. Callers that want automatic dismissal
    should run it themselves inside their navigation block:

    .. code-block:: python

        async with browser_page() as page:
            await page.goto(url)
            await dismiss_gdpr_async(page)

    The kwarg is retained for API parity with a future middleware
    that could wrap ``page.goto``.
    """

    from playwright.async_api import async_playwright

    ua = user_agent or pick_user_agent()
    vp = viewport or DEFAULT_VIEWPORT
    launch_args = extra_args or []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=launch_args)
        ctx_kwargs: dict = {"user_agent": ua, "viewport": vp}
        if storage_state:
            ctx_kwargs["storage_state"] = storage_state
        ctx = await browser.new_context(**ctx_kwargs)

        if cookies and not storage_state:
            await ctx.add_cookies(cookies)

        page = await ctx.new_page()

        try:
            yield page
        finally:
            await browser.close()


@contextmanager
def browser_page_sync(
    cookies: Optional[List[dict]] = None,
    user_agent: Optional[str] = None,
    viewport: Optional[dict] = None,
    headless: bool = True,
    storage_state: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
) -> Iterator[Any]:
    """Sync Playwright ``Page`` — used by login flows and session refresh
    scripts that don't live inside an asyncio loop."""

    from playwright.sync_api import sync_playwright

    ua = user_agent or pick_user_agent()
    vp = viewport or DEFAULT_VIEWPORT
    launch_args = extra_args or []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=launch_args)
        ctx_kwargs: dict = {"user_agent": ua, "viewport": vp}
        if storage_state:
            ctx_kwargs["storage_state"] = storage_state
        ctx = browser.new_context(**ctx_kwargs)

        if cookies and not storage_state:
            ctx.add_cookies(cookies)

        page = ctx.new_page()

        try:
            yield page
        finally:
            browser.close()


@contextmanager
def browser_context_sync(
    cookies: Optional[List[dict]] = None,
    user_agent: Optional[str] = None,
    viewport: Optional[dict] = None,
    headless: bool = True,
    locale: Optional[str] = None,
    storage_state: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
) -> Iterator[Any]:
    """Sync Playwright ``BrowserContext`` for multi-page crawlers."""

    from playwright.sync_api import sync_playwright

    ua = user_agent or pick_user_agent()
    vp = viewport or DEFAULT_VIEWPORT
    launch_args = extra_args or []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=launch_args)
        ctx_kwargs: dict = {"user_agent": ua, "viewport": vp}
        if locale:
            ctx_kwargs["locale"] = locale
        if storage_state:
            ctx_kwargs["storage_state"] = storage_state
        ctx = browser.new_context(**ctx_kwargs)

        if cookies and not storage_state:
            ctx.add_cookies(cookies)

        try:
            yield ctx
        finally:
            browser.close()


async def dismiss_gdpr_async(page: Any, timeout_ms: int = 3000) -> bool:
    """Click the first visible GDPR/cookie consent button in
    :data:`GDPR_SELECTORS`. Returns ``True`` if one was dismissed.

    Per-selector exceptions are swallowed (audit §1.1 errors row) —
    a hidden/removed element should never bubble a Playwright error
    up to the caller.
    """

    for sel in GDPR_SELECTORS:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                await el.click(timeout=timeout_ms)
                await page.wait_for_timeout(500)
                logger.debug("GDPR dismissed via: %s", sel)
                return True
        except Exception:
            continue
    return False


def dismiss_gdpr(page: Any, timeout_ms: int = 3000) -> bool:
    """Sync analogue of :func:`dismiss_gdpr_async`."""

    for sel in GDPR_SELECTORS:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click(timeout=timeout_ms)
                time.sleep(0.5)
                logger.debug("GDPR dismissed via: %s", sel)
                return True
        except Exception:
            continue
    return False


@asynccontextmanager
async def persistent_browser(
    *, cdp_port: int = CDP_DEFAULT_PORT, timeout_ms: int = 5000
) -> AsyncIterator[Any]:
    """Attach to an already-running Chrome via CDP — skips the 3-5s
    cold-start cost of every ``browser.chromium.launch()``.

    The service-managed Chrome (``puedo-vnc-browser.service``, port
    9222) survives across agent restarts and holds persistent cookies
    useful for authenticated sites (Facebook, Habitissimo).

    Yields a fresh ``Page``; on exit the page is closed but the
    Chrome process keeps running — the browser is not ours to terminate.
    """

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
        try:
            ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await ctx.new_page()
            page.set_default_timeout(timeout_ms)
            try:
                yield page
            finally:
                await page.close()
        finally:
            await browser.close()
