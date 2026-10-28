"""Typed scraping errors.

All I/O-borne failures raise :class:`ScrapingError` or a subclass.
Callers branch on type for graceful degradation:

* :class:`RobotsDisallowed` — ``/robots.txt`` forbids the path. Caller
  chooses to skip (directory discovery) or bypass with
  ``respect_robots=False`` (authenticated adapter).
* :class:`FetchError` — generic upstream failure. Wraps
  :class:`httpx.HTTPStatusError` / :class:`httpx.RequestError` /
  CDP timeouts. Caller retries at a higher layer if appropriate.
* :class:`BrowserUnavailable` — Playwright cold-start failed AND
  CDP fallback failed. Caller falls back to static fetch or gives up.

Pure FTS / pure parse paths never raise:

* :func:`parse_html` / :func:`parse_soup` catch at the lxml/bs4
  boundary — ``recover=True`` on the parser + silent fallback in
  :func:`html_to_text`.

Design note: this module carries the typed error surface without
adding any dependencies. The concrete fetchers import
``httpx.HTTPStatusError`` at call-time and wrap into ``FetchError``
at their boundaries.
"""
from __future__ import annotations

__all__ = [
    "ScrapingError",
    "FetchError",
    "BrowserUnavailable",
    "RobotsDisallowed",
]


class ScrapingError(Exception):
    """Base class for all scraping-related errors."""


class FetchError(ScrapingError):
    """Upstream failure during URL fetch (HTTP error, timeout, TLS, DNS)."""


class BrowserUnavailable(ScrapingError):
    """Browser/CDP unavailable — both cold-start and CDP paths failed."""


class RobotsDisallowed(ScrapingError):
    """robots.txt explicitly disallows the requested path for this UA."""

    def __init__(self, url: str, user_agent: str = "*") -> None:
        self.url = url
        self.user_agent = user_agent
        super().__init__(f"robots.txt disallows {url!r} for UA {user_agent!r}")
