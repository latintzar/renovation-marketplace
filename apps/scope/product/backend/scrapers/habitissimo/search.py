"""Habitissimo directory search.

Wave-9 scope: scaffolded stubs with the canonical signatures so
:func:`scraping.search` can import-dispatch against a stable API.
Full implementation (Playwright navigation → company-card parsing →
phone reveal loop) lands in Phase 5 once the upstream DOM is
fingerprinted.
"""
from __future__ import annotations

from typing import Optional

from ..directories import ContractorLead

__all__ = ["search", "list_companies"]


async def list_companies(
    trade: str,
    city: str,
    *,
    pages: int = 1,
    limit: int = 20,
) -> list[ContractorLead]:
    """List companies on Habitissimo's directory for ``trade × city``.

    :param pages: Number of directory pages to paginate through.
        Audit §1.7 S3 noted the pre-migration scraper only fetched
        page 1; Phase 5 adds pagination here.

    .. note::
       **Wave-9 scope**: stub returning ``[]``. See
       ``internal/refactor/packages/scraping/design.md`` §D7.
    """

    return []


async def search(
    trade: str,
    city: str,
    *,
    limit: int = 50,
    reveal_phones: bool = True,
    session: Optional[dict] = None,
) -> list[ContractorLead]:
    """Search Habitissimo directory and optionally reveal phones.

    Returns a list of :class:`ContractorLead` with ``platform="habitissimo"``.
    Deduplication happens at the caller (:func:`scraping.search`).

    .. note::
       **Wave-9 scope**: stub returning ``[]``. Full implementation
       wraps :func:`list_companies` → :func:`.phones.reveal_phone`
       under a :class:`core.RateLimiter`.
    """

    return []
