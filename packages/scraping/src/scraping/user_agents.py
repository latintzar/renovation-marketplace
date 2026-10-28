"""Single source of truth for user-agent rotation (D12).

Merges five pre-migration UA lists (``shared.browser``, ``blast.py``,
``instagram_scraper``, ``tools/web_fetch``, ``routes/profile_import``)
into one canonical pool split by form factor. Every outbound request —
``fetch_static``, ``fetch_browser``, Playwright contexts, adapter
POSTs — picks from here.

Public API (exposed via ``scraping.__all__``):

* :data:`USER_AGENTS` — the full pool, desktop + mobile.
* :data:`DESKTOP_USER_AGENTS` / :data:`MOBILE_USER_AGENTS` — form-factor
  slices. Disjoint with the full pool because callers pin to one
  class of device (audit §1.10 I3: IG profile fetches need mobile UA
  to get the simpler HTML response).
* :func:`pick_user_agent`, :func:`pick_desktop`, :func:`pick_mobile` —
  random-choice pickers; never raise.
"""
from __future__ import annotations

import random

__all__ = [
    "USER_AGENTS",
    "DESKTOP_USER_AGENTS",
    "MOBILE_USER_AGENTS",
    "pick_user_agent",
    "pick_desktop",
    "pick_mobile",
]

DESKTOP_USER_AGENTS: tuple[str, ...] = (
    # Chrome — macOS / Windows / Linux
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.3; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
)

MOBILE_USER_AGENTS: tuple[str, ...] = (
    # iPhone — used by IG profile scraping (mobile = simpler non-React HTML)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    # Android
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
)

USER_AGENTS: tuple[str, ...] = DESKTOP_USER_AGENTS + MOBILE_USER_AGENTS


def pick_user_agent() -> str:
    """Return a random UA from the full pool."""

    return random.choice(USER_AGENTS)


def pick_desktop() -> str:
    """Return a random desktop UA."""

    return random.choice(DESKTOP_USER_AGENTS)


def pick_mobile() -> str:
    """Return a random mobile UA (use for IG profile HTML, etc.)."""

    return random.choice(MOBILE_USER_AGENTS)
