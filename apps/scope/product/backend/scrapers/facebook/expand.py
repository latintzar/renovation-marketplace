"""Facebook "More comments" expansion helper.

Used as a ``page_action`` callback with :func:`scraping.fetch_browser` to
reveal hidden comment threads on Facebook group posts (where contractor
phone numbers and business names usually hide). Facebook lazy-loads the
lower comment layers, so without this step a scrape returns the first 2-3
comments only.

The pre-migration home was :mod:`unmigrated.backend.tools.web_fetch` —
inline site-specific code inside a generic fetcher. We moved it here so
per-site logic stays next to the Facebook adapter.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["FB_MORE_SELECTORS", "expand_comments"]


FB_MORE_SELECTORS: tuple[str, ...] = (
    'span:has-text("View more comments")',
    'span:has-text("Ver más comentarios")',
    'span:has-text("View more answers")',
    'span:has-text("Ver más respuestas")',
    'div[role="button"]:has-text("more comment")',
    'div[role="button"]:has-text("más comentario")',
    '[aria-label*="View more comments"]',
    '[aria-label*="more comments"]',
)
"""Ordered list of FB comment-expansion selectors. Spanish variants
included because Spain is our primary market for contractor scraping."""


async def expand_comments(page: Any, max_clicks: int = 5) -> int:
    """Click every matching "more comments" button up to ``max_clicks`` rounds.

    Facebook lazy-loads comments in batches. Each click reveals ~5-10 more.
    We keep clicking until no more buttons remain or we hit ``max_clicks``
    (safety cap — avoids infinite loops on viral posts with 500+ comments).

    Returns the number of successful clicks (useful for observability).
    """
    clicked = 0
    for _ in range(max_clicks):
        found_any = False
        for selector in FB_MORE_SELECTORS:
            try:
                buttons = await page.query_selector_all(selector)
                for btn in buttons:
                    if not await btn.is_visible():
                        continue
                    await btn.scroll_into_view_if_needed()
                    await btn.click()
                    clicked += 1
                    found_any = True
                    await page.wait_for_timeout(1500)
            except Exception:
                continue
        if not found_any:
            break

    if clicked:
        logger.info("fb_expand_comments | clicked %d 'view more' buttons", clicked)
    return clicked
