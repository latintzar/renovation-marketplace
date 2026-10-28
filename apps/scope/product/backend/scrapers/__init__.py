"""``scrapers`` — scope-app site-specific scrapers and contractor discovery.

Lives at ``apps/scope/product/backend/scrapers/`` (moved from
``packages/scraping/src/scraping/adapters/`` in Phase 5 Wave 5 — per-site
scraping logic is scope-policy, while the underlying browser/fetch/parse
primitives stay in ``packages/scraping/``).

What's here:

* :class:`ContractorLead` + :func:`search` — cross-platform contractor
  orchestrator with phone-based dedup. The canonical shape consumed by
  the scope app's contractor-discovery flow.
* :func:`fb_expand_comments` — Facebook comment expander (scope's
  prospect-discovery extension).
* Site adapters live in submodules: :mod:`scrapers.habitissimo`,
  :mod:`scrapers.instagram`, :mod:`scrapers.houzz`,
  :mod:`scrapers.facebook`.
* Legacy one-offs: :mod:`scrapers.instagram_scraper` (pre-adapter IG
  scraper, still used by profile-import route),
  :mod:`scrapers.whatsapp_checker` (phone validity pinger).

Imports ``packages/scraping`` for primitives (``parse_html``,
``fetch_browser``, ``browser_page``, ``USER_AGENTS``, etc.) via the
public API: ``from scraping import ...``.
"""
from __future__ import annotations

from .directories import ContractorLead, search
from .facebook import expand_comments as fb_expand_comments

__all__ = [
    "ContractorLead",
    "search",
    "fb_expand_comments",
]
