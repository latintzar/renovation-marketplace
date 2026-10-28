"""IG discovery via Google SERP (scaffolded).

Audit §1.10: IG's own search is aggressively rate-limited; discovery
pivots off Google's ``site:instagram.com`` results. Three extraction
strategies run in order — Google's HTML varies by experiment/region.

:data:`IG_USERNAME_SKIP` is the canonical non-user-account allowlist
(``explore``, ``directory``, ``p``, etc.) so those aren't mistaken
for contractor profiles when scraping URLs out of SERP HTML.
"""
from __future__ import annotations

from typing import Any

__all__ = ["IG_USERNAME_SKIP", "google_search"]


IG_USERNAME_SKIP: frozenset[str] = frozenset(
    {
        "explore",
        "accounts",
        "directory",
        "p",
        "reel",
        "reels",
        "stories",
        "tags",
        "tv",
        "web",
        "about",
        "legal",
        "privacy",
        "terms",
        "help",
        "press",
        "api",
        "developer",
        "developers",
    }
)
"""URL-path segments that are **not** user accounts. Used when
extracting IG usernames from SERP URLs so we don't register
``instagram.com/explore`` as a contractor profile."""


async def google_search(
    query: str, *, limit: int = 20
) -> list[dict[str, Any]]:
    """Execute a Google SERP query and return list of IG-profile hits.

    Each hit: ``{"username", "url", "title", "snippet"}``.

    .. note::
       **Wave-9 scope**: stub returning ``[]``. Full implementation
       uses Bright Data Unlocker for the SERP fetch then runs three
       HTML-extraction strategies (audit §1.10 R4-R6) to tolerate
       Google's layout variance.
    """

    return []
