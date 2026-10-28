"""robots.txt consultation — :func:`is_allowed`, :class:`RobotsChecker` (D10).

Permissive default: unreachable robots.txt (network error, 404, 5xx)
resolves to **allowed**. Rationale in D10:

* Scraping Leo's targets is already courtesy-not-requirement space.
* A conservative default ("block if unsure") would break the walker
  and the directory adapters on every transient DNS failure.
* Callers who want strict behaviour pass ``strict=True``.

:class:`RobotsChecker` caches one parsed robots.txt per host for
``cache_ttl`` seconds (default 1 h). Useful when a crawler visits
many pages on the same host — we pay the robots fetch once.

Implementation: stdlib :mod:`urllib.robotparser` does the heavy
lifting. We only add:

* Async fetch via :mod:`httpx` (the parser's built-in sync fetch
  would block an asyncio event loop).
* Per-host cache with expiry.
* Permissive-on-error default (stdlib's behaviour is implementation-
  defined on fetch failure; we pin it).
"""
from __future__ import annotations

import logging
import time
from typing import Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from .user_agents import pick_user_agent

logger = logging.getLogger(__name__)

__all__ = ["is_allowed", "RobotsChecker"]


class RobotsChecker:
    """Cached robots.txt checker.

    One instance per crawler session lets the robots fetch amortise
    across many URL checks on the same host.

    :param cache_ttl: Seconds to cache a parsed robots.txt per host.
        Default 1 h. Set to ``0`` for no caching (testing).
    :param fetch_timeout: Per-robots-fetch HTTP timeout in seconds.
    """

    def __init__(self, *, cache_ttl: float = 3600.0, fetch_timeout: float = 10.0) -> None:
        self._cache_ttl = cache_ttl
        self._timeout = fetch_timeout
        self._cache: dict[str, tuple[Optional[RobotFileParser], float]] = {}

    async def _parser_for(self, host_root: str) -> Optional[RobotFileParser]:
        """Fetch + parse robots.txt for ``host_root`` (``scheme://host``).

        Returns a populated :class:`RobotFileParser`, or ``None`` if the
        robots.txt could not be retrieved (caller treats as permissive).
        """

        now = time.monotonic()
        cached = self._cache.get(host_root)
        if cached and cached[1] > now:
            return cached[0]

        url = host_root.rstrip("/") + "/robots.txt"
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout, connect=min(self._timeout, 5.0)),
                follow_redirects=True,
            ) as client:
                resp = await client.get(url, headers={"User-Agent": pick_user_agent()})
        except httpx.HTTPError as e:
            logger.debug("robots.txt fetch failed for %s: %s", url, e)
            self._cache[host_root] = (None, now + self._cache_ttl)
            return None

        if resp.status_code != 200:
            logger.debug("robots.txt HTTP %d for %s", resp.status_code, url)
            self._cache[host_root] = (None, now + self._cache_ttl)
            return None

        parser = RobotFileParser()
        parser.parse(resp.text.splitlines())
        self._cache[host_root] = (parser, now + self._cache_ttl)
        return parser

    async def is_allowed(
        self, url: str, user_agent: str = "*", *, strict: bool = False
    ) -> bool:
        """Check whether ``url`` is allowed for ``user_agent``.

        :param strict: When ``True``, a fetch failure raises the
            underlying :class:`httpx.HTTPError` instead of returning
            ``True``. Useful when you want to fail loudly on a
            provider that's explicitly opted-in to robots.
        """

        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return True
        host_root = f"{parsed.scheme}://{parsed.netloc}"

        if strict:
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(self._timeout, connect=min(self._timeout, 5.0)),
                    follow_redirects=True,
                ) as client:
                    resp = await client.get(
                        host_root.rstrip("/") + "/robots.txt",
                        headers={"User-Agent": pick_user_agent()},
                    )
                if resp.status_code != 200:
                    raise httpx.HTTPStatusError(
                        f"robots.txt HTTP {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                rp = RobotFileParser()
                rp.parse(resp.text.splitlines())
            except httpx.HTTPError:
                raise
            return rp.can_fetch(user_agent, url)

        parser = await self._parser_for(host_root)
        if parser is None:
            return True
        return parser.can_fetch(user_agent, url)

    async def crawl_delay(
        self, host: str, user_agent: str = "*"
    ) -> Optional[float]:
        """Return the declared crawl-delay for ``host`` (seconds), or
        ``None`` if robots.txt is silent on the matter."""

        parsed = urlparse(host)
        host_root = (
            f"{parsed.scheme}://{parsed.netloc}"
            if parsed.scheme
            else f"https://{host}"
        )
        parser = await self._parser_for(host_root)
        if parser is None:
            return None
        delay = parser.crawl_delay(user_agent)
        return float(delay) if delay else None


_DEFAULT_CHECKER = RobotsChecker()


async def is_allowed(
    url: str, user_agent: str = "*", *, strict: bool = False
) -> bool:
    """Module-level convenience wrapper over a shared :class:`RobotsChecker`.

    Fine for one-off checks. For high-volume crawls use
    :class:`RobotsChecker` with an explicit instance so the cache is
    scoped to the crawler (avoids process-wide cache leak).
    """

    return await _DEFAULT_CHECKER.is_allowed(url, user_agent=user_agent, strict=strict)
