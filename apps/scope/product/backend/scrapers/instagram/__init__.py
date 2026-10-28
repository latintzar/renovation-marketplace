"""scrapers.instagram — IG directory + profile adapter (scope scrapers).

robots-policy: ignore. IG blocks scraping at ToS level regardless
of robots.txt; robots consultation would be ceremonial.

Discovery uses Google SERP (``site:instagram.com "trade" "city"``)
because IG's own search is rate-limited aggressively. Profile HTML
is fetched with a mobile UA (audit §1.10 I3: the mobile response
is simpler, static-friendly HTML).

Session semantics: **none**. Bright Data's Unlocker zone handles
proxy + fingerprinting server-side.

Wave-9 scope: public surface declared, implementations scaffolded.
"""
from __future__ import annotations

from .profile import extract_profile_fields, fetch_profile
from .search import IG_USERNAME_SKIP, google_search
from .scraper import search  # last: overrides the `search` submodule attribute

__all__ = [
    "search",
    "google_search",
    "fetch_profile",
    "extract_profile_fields",
    "IG_USERNAME_SKIP",
]
