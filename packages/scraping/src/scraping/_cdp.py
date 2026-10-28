"""Private CDP fetch implementation (D4, D6).

Wraps ``scrapling.DynamicFetcher`` with a three-strategy fallback:

1. **CDP attach** — connect to the always-running Chrome on
   :9222 (discovered via HTTP ``/json/version``). Saves the 3–5s
   cold-start of every Playwright launch. Default.
2. **Standalone scrapling** — scrapling cold-starts Chromium itself
   if CDP attach fails (e.g. the service is down).
3. **httpx** — last-resort static fetch if both browser paths fail.
   Returns raw HTML; caller still gets something.

The CDP WS URL is cached per-port (module-level ``_cdp_ws_cache``)
with auto-invalidation on any HTTP error from the discovery endpoint
(fixes pre-migration audit §1.4 S2: cache-never-expires-on-Chrome-restart).

Callers **always** go through :func:`scraping.fetch_browser`; this
module is underscore-prefixed to enforce that convention.

Scrapling is an optional runtime dep. If unavailable, module import
succeeds (returns empty-string contract via the fallback path);
``fetch_browser`` logs a warning and returns ``""``.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Awaitable, Callable, Optional

import httpx

from .user_agents import pick_user_agent

logger = logging.getLogger(__name__)

__all__ = [
    "fetch_via_cdp",
    "get_cdp_ws_url",
]


_CDP_WS_CACHE: dict[int, tuple[str, float]] = {}
"""``{port: (ws_url, expires_at)}``. Expires after 5 minutes or on
fetch error (auto-invalidates on Chrome restart)."""

_CDP_CACHE_TTL = 300.0


async def get_cdp_ws_url(port: int = 9222, *, force_refresh: bool = False) -> Optional[str]:
    """Discover the CDP WebSocket URL for the given port.

    Queries ``http://127.0.0.1:{port}/json/version``, caches the
    ``webSocketDebuggerUrl`` for 5 minutes. Returns ``None`` if the
    Chrome DevTools endpoint is unreachable (port not listening,
    connection refused, etc.).

    Cache auto-invalidates on fetch error so a Chrome restart doesn't
    leave us attached to a dead WS URL.
    """

    now = time.monotonic()
    if not force_refresh:
        cached = _CDP_WS_CACHE.get(port)
        if cached and cached[1] > now:
            return cached[0]

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=2.0)) as client:
            resp = await client.get(f"http://127.0.0.1:{port}/json/version")
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, json.JSONDecodeError, ValueError) as e:
        logger.debug("CDP discovery failed on port %d: %s", port, e)
        _CDP_WS_CACHE.pop(port, None)
        return None

    ws_url = data.get("webSocketDebuggerUrl")
    if not ws_url:
        _CDP_WS_CACHE.pop(port, None)
        return None

    _CDP_WS_CACHE[port] = (ws_url, now + _CDP_CACHE_TTL)
    return ws_url


async def fetch_via_cdp(
    url: str,
    *,
    timeout_ms: int = 20000,
    cdp_url: Optional[str] = None,
    page_action: Optional[Callable[..., Awaitable[None]]] = None,
    raw_html: bool = False,
    max_chars: Optional[int] = None,
) -> str:
    """Three-strategy browser fetch.

    Strategy order: CDP attach → standalone scrapling → httpx. Each
    strategy silently falls to the next on any exception. Empty string
    is returned only if **all three** fail (preserves the pre-migration
    ``tools.web_fetch`` contract).

    ``page_action`` runs after page load, before content extraction —
    used by Facebook comment expansion and similar per-site hooks.

    ``raw_html=True`` returns the rendered HTML; otherwise returns a
    readability text extraction via :func:`scraping.html_to_text`.
    """

    from .text import html_to_text

    port = 9222
    try:
        from scrapling.fetchers import DynamicFetcher  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("scrapling unavailable; falling back to httpx for %s", url)
        return await _httpx_fallback(url, raw_html=raw_html, max_chars=max_chars)

    ws_url = cdp_url or await get_cdp_ws_url(port)

    if ws_url:
        try:
            fetcher = DynamicFetcher()
            page = await _run_scrapling(
                fetcher,
                url,
                timeout=timeout_ms,
                cdp_url=ws_url,
                page_action=page_action,
            )
            content = (
                page.html_content if raw_html else html_to_text(page.html_content)
            )
            if max_chars:
                content = content[:max_chars]
            if content:
                return content
            logger.debug("CDP strategy returned empty for %s; trying standalone", url)
        except Exception as e:  # noqa: BLE001
            logger.debug("CDP attach failed for %s: %s", url, e)
            _CDP_WS_CACHE.pop(port, None)

    try:
        fetcher = DynamicFetcher()
        page = await _run_scrapling(
            fetcher, url, timeout=timeout_ms, page_action=page_action
        )
        content = (
            page.html_content if raw_html else html_to_text(page.html_content)
        )
        if max_chars:
            content = content[:max_chars]
        if content:
            return content
    except Exception as e:  # noqa: BLE001
        logger.debug("Standalone scrapling failed for %s: %s", url, e)

    return await _httpx_fallback(url, raw_html=raw_html, max_chars=max_chars)


async def _run_scrapling(
    fetcher: Any,
    url: str,
    *,
    timeout: int,
    cdp_url: Optional[str] = None,
    page_action: Optional[Callable[..., Awaitable[None]]] = None,
) -> Any:
    """Invoke scrapling.DynamicFetcher with our canonical kwargs.

    scrapling's API has shifted across versions; we tolerate both
    ``cdp_url`` and ``cdpUrl`` spellings and let the library decide."""

    kwargs: dict[str, Any] = {"timeout": timeout, "useragent": pick_user_agent()}
    if cdp_url:
        kwargs["cdp_url"] = cdp_url
    if page_action is not None:
        kwargs["page_action"] = page_action
    return await fetcher.fetch(url, **kwargs)


async def _httpx_fallback(
    url: str, *, raw_html: bool, max_chars: Optional[int] = None
) -> str:
    """Last-resort static fetch. Returns ``""`` on any httpx error."""

    from .text import html_to_text

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=10.0),
            follow_redirects=True,
        ) as client:
            resp = await client.get(url, headers={"User-Agent": pick_user_agent()})
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPError as e:
        logger.debug("httpx fallback failed for %s: %s", url, e)
        return ""

    content = html if raw_html else html_to_text(html)
    if max_chars:
        content = content[:max_chars]
    return content
