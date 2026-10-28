"""URL fetch: static (httpx) + browser (CDP-first) + auto-routed (D1).

Three public entry points:

* :func:`fetch_static` — pure httpx; raises on HTTP errors; the 90%
  path for walkers, RSS-type flows, JSON endpoints.
* :func:`fetch_browser` — CDP-first Playwright; returns ``""`` on
  total failure (preserves the pre-migration ``tools.web_fetch``
  contract consumed by ``workflows.contractor_discovery``).
* :func:`fetch` — auto-routes via :data:`JS_HOSTS` substring match
  (D3). Callers that always want one path call the specific
  function; callers that want "do the right thing" call ``fetch()``.

:data:`JS_HOSTS` is a mutable :class:`set` — extended at startup via
:func:`extend_js_hosts` (idempotent, safe from multiple init sites).

:func:`fetch_many` fan-outs with a semaphore-capped concurrency, the
canonical replacement for the pre-migration per-caller ``asyncio.gather``
+ semaphore patterns.

CDP path implementation lives in the private :mod:`scraping._cdp` module
(lazy-imported so hosts without Playwright/scrapling can still call
:func:`fetch_static`). See D6 for rationale.
"""
from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Awaitable, Callable, Iterable, Optional

from .errors import FetchError, RobotsDisallowed
from .text import html_to_text
from .user_agents import pick_user_agent

logger = logging.getLogger(__name__)

__all__ = [
    "FetchStrategy",
    "JS_HOSTS",
    "extend_js_hosts",
    "fetch",
    "fetch_static",
    "fetch_browser",
    "fetch_many",
    "extract_text",
]


class FetchStrategy(str, Enum):
    """How should :func:`fetch` dispatch?"""

    AUTO = "auto"
    """Consult :data:`JS_HOSTS`; use browser for matches, static otherwise."""
    STATIC = "static"
    """Force :func:`fetch_static` (httpx)."""
    BROWSER = "browser"
    """Force :func:`fetch_browser` (CDP-first Playwright)."""


JS_HOSTS: set[str] = {
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "tiktok.com",
}
"""Substrings that route :func:`fetch` auto-mode through the browser.

Match is naive substring-in-URL (preserved audit §1.2 I1 behaviour
so we don't silently break callers). Extend at startup via
:func:`extend_js_hosts`."""


def extend_js_hosts(hosts: Iterable[str]) -> None:
    """Add substrings to :data:`JS_HOSTS`. Idempotent."""

    for h in hosts:
        if h:
            JS_HOSTS.add(h)


def _is_js_host(url: str) -> bool:
    """True if any :data:`JS_HOSTS` entry is a substring of ``url``."""

    return any(h in url for h in JS_HOSTS)


async def fetch_static(
    url: str,
    *,
    timeout: float = 15.0,
    headers: Optional[dict[str, str]] = None,
    user_agent: Optional[str] = None,
    follow_redirects: bool = True,
) -> str:
    """Static httpx fetch. Raises :class:`FetchError` on upstream failure.

    ``user_agent`` defaults to a random pick from :data:`USER_AGENTS`;
    callers pin a specific one (e.g. mobile for IG profiles) by passing
    ``user_agent=pick_mobile()``.
    """

    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - httpx is required
        raise FetchError(f"httpx unavailable: {exc}") from exc

    ua = user_agent or pick_user_agent()
    merged = {"User-Agent": ua}
    if headers:
        merged.update(headers)

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=min(timeout, 10.0)),
            follow_redirects=follow_redirects,
        ) as client:
            resp = await client.get(url, headers=merged)
            resp.raise_for_status()
            return resp.text
    except httpx.HTTPStatusError as e:
        raise FetchError(f"HTTP {e.response.status_code} for {url}") from e
    except httpx.RequestError as e:
        raise FetchError(f"request failed for {url}: {e}") from e


async def fetch_browser(
    url: str,
    *,
    timeout_ms: int = 20000,
    cdp_url: Optional[str] = None,
    page_action: Optional[Callable[..., Awaitable[None]]] = None,
    raw_html: bool = False,
    max_chars: Optional[int] = None,
) -> str:
    """CDP-first Playwright fetch. Returns ``""`` on total failure.

    Delegates to the private :mod:`scraping._cdp` module (lazy-imported
    so hosts without Playwright can still use :func:`fetch_static`).
    The returned string is the rendered HTML if ``raw_html=True`` or a
    readability text extraction otherwise.

    ``page_action`` is an optional async hook ``(page) -> None`` for
    per-site post-load work (click "more comments", wait for a specific
    selector, etc.). Used by Facebook comment expansion.

    Empty-string fallback is preserved from the pre-migration
    ``tools.web_fetch.fetch_url`` contract — callers like
    ``workflows.contractor_discovery`` do ``if not content: skip`` and
    must not receive exceptions on routine outages.
    """

    try:
        from ._cdp import fetch_via_cdp
    except ImportError:
        logger.warning("scraping._cdp unavailable; browser fetch disabled for %s", url)
        return ""

    try:
        return await fetch_via_cdp(
            url,
            timeout_ms=timeout_ms,
            cdp_url=cdp_url,
            page_action=page_action,
            raw_html=raw_html,
            max_chars=max_chars,
        )
    except Exception as e:  # noqa: BLE001 — contract: never raise
        logger.warning("scraping.fetch_browser failed for %s: %s", url, e)
        return ""


async def fetch(
    url: str,
    *,
    strategy: FetchStrategy = FetchStrategy.AUTO,
    respect_robots: bool = True,
    timeout: float = 15.0,
    **kwargs,
) -> str:
    """Auto-dispatched fetch. Raises :class:`RobotsDisallowed` on robots
    denial (when ``respect_robots=True``), otherwise delegates.

    :param strategy: See :class:`FetchStrategy`.
    :param respect_robots: When ``True`` (default), fetch halts on robots
        disallow. Adapters with explicit exceptions pass ``False``.
    :param timeout: Passed to the underlying fetcher.
    :param kwargs: Forwarded to :func:`fetch_static` or
        :func:`fetch_browser` depending on resolved strategy.

    The browser path silently swallows errors (empty-string fallback);
    the static path raises :class:`FetchError`. This asymmetry is
    intentional and documented in D1.
    """

    if respect_robots:
        from .robots import is_allowed

        ua = kwargs.get("user_agent") or pick_user_agent()
        if not await is_allowed(url, user_agent=ua):
            raise RobotsDisallowed(url, user_agent=ua)

    resolved = strategy
    if resolved is FetchStrategy.AUTO:
        resolved = FetchStrategy.BROWSER if _is_js_host(url) else FetchStrategy.STATIC

    if resolved is FetchStrategy.BROWSER:
        browser_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k
            in {"timeout_ms", "cdp_url", "page_action", "raw_html", "max_chars"}
        }
        return await fetch_browser(url, **browser_kwargs)

    static_kwargs = {
        k: v
        for k, v in kwargs.items()
        if k in {"headers", "user_agent", "follow_redirects"}
    }
    return await fetch_static(url, timeout=timeout, **static_kwargs)


async def fetch_many(
    urls: Iterable[str],
    *,
    strategy: FetchStrategy = FetchStrategy.AUTO,
    concurrency: int = 8,
    respect_robots: bool = True,
    timeout: float = 15.0,
) -> dict[str, str]:
    """Fan-out fetch with a semaphore-capped concurrency.

    Returns ``{url: content}`` with ``content == ""`` for any URL that
    failed (preserving fetch_browser's empty-string semantics). Failed
    static fetches also return ``""`` in the map — the convenience
    wrapper smooths the two error contracts so callers get one shape.
    """

    sem = asyncio.Semaphore(concurrency)
    results: dict[str, str] = {}

    async def _one(url: str) -> None:
        async with sem:
            try:
                results[url] = await fetch(
                    url,
                    strategy=strategy,
                    respect_robots=respect_robots,
                    timeout=timeout,
                )
            except Exception as e:  # noqa: BLE001 — rollup for batch
                logger.info("scraping.fetch_many | %s failed: %s", url, e)
                results[url] = ""

    await asyncio.gather(*(_one(u) for u in urls))
    return results


async def extract_text(
    url: str,
    *,
    timeout: float = 15.0,
    strategy: FetchStrategy = FetchStrategy.AUTO,
    respect_robots: bool = True,
) -> str:
    """Fetch + :func:`html_to_text` in one call (D9).

    Batteries-included path: same auto-routing as :func:`fetch`, text
    extraction via :func:`html_to_text`. For custom headers or
    post-processing, compose ``html = await fetch(...); text = html_to_text(html)``
    yourself.
    """

    html = await fetch(
        url, strategy=strategy, respect_robots=respect_robots, timeout=timeout
    )
    return html_to_text(html)
