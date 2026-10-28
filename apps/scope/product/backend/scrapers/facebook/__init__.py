"""scrapers.facebook — Facebook group monitoring + comment expansion (scope scrapers).

robots-policy: ignore. FB's terms forbid scraping; robots.txt
adds nothing.

Session semantics: Playwright ``storage_state`` blob, file-cached
at ``/tmp/fb_state.json``. TTL: unlimited until invalidated by FB
(sessions last months under normal use).

Wave-9 scope: ``expand_comments`` is a scaffolded wrapper around
:func:`scraping.fetch_browser` with ``page_action=``. ``capture_graphql``
(``groups.py``) is scaffolded — full GraphQL response interception
moves from ``scripts/fb_monitor.py`` in Phase 5.
"""
from __future__ import annotations

from .expand import FB_MORE_SELECTORS, expand_comments
from .groups import capture_graphql

__all__ = ["expand_comments", "FB_MORE_SELECTORS", "capture_graphql"]
