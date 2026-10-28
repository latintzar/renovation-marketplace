"""Houzz search — query construction + directory fetch.

:func:`build_query` is a pure helper exposed for unit tests —
Houzz's expanded search URL shape is idiosyncratic enough that
getting it right once (and asserting via tests) is worth a public
helper.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import quote_plus

from ..directories import ContractorLead

__all__ = ["build_query", "search"]


HOUZZ_SEARCH_BASE = "https://www.houzz.com/professionals/search"


def build_query(trade: str, city: str, *, country: str = "es") -> str:
    """Construct a Houzz directory search URL.

    Pure function — deterministic. Used by both :func:`search` and
    any migrated call-site of the pre-migration
    ``workflows.contractor_discovery._search_houzz_expanded``.

    >>> build_query("fontaneros", "madrid")
    'https://www.houzz.com/professionals/search/query/fontaneros--madrid/geo/es'
    """

    trade_slug = quote_plus((trade or "").lower().replace(" ", "-"))
    city_slug = quote_plus((city or "").lower().replace(" ", "-"))
    return (
        f"{HOUZZ_SEARCH_BASE}/query/{trade_slug}--{city_slug}/geo/{country}"
    )


async def search(
    trade: str,
    city: str,
    *,
    limit: int = 50,
    country: str = "es",
    respect_robots: bool = True,
) -> list[ContractorLead]:
    """Houzz contractor directory search.

    Wraps :func:`scraping.fetch` with ``respect_robots=True``. On
    :class:`~scraping.errors.RobotsDisallowed` returns an empty list
    (graceful degradation — never breaks the outer
    :func:`scraping.search` batch).

    .. note::
       **Wave-9 scope**: stub returning ``[]``. Full implementation
       uses ``curl_cffi`` for JA3 impersonation (Houzz blocks stdlib
       httpx aggressively) — audit §3.1.
    """

    return []
