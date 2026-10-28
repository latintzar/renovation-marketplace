"""Contractor directory discovery — :class:`ContractorLead`, :func:`search`.

Lives at ``apps/scope/product/backend/scrapers/directories.py`` (moved from
``packages/scraping/src/scraping/directories.py`` in Phase 5 Wave 5
alongside the four site adapters: the contractor-lead shape and the
cross-platform orchestrator are Spanish-contractor-market concerns, not
reusable scraping capability). Reached via
``from scrapers import search, ContractorLead``.

What's preserved:

* :class:`ContractorLead` dataclass — the canonical row shape across
  every site adapter. ``phone_normalized`` + ``is_valid_phone`` delegate
  to :mod:`core.phone` (post-Wave-2 canonical), preserving the dedup-
  key invariant.
* Phone-based dedup. First occurrence wins.
* Per-adapter exception containment: a single adapter raising does not
  break the batch.

Adapter dispatch uses lazy imports so importing :mod:`scrapers` doesn't
drag in every site module (and its optional deps like Playwright).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional, Sequence

from core.phone import is_valid_spanish, normalize

logger = logging.getLogger(__name__)

__all__ = [
    "ContractorLead",
    "search",
]

_PLATFORM_NAMES: tuple[str, ...] = ("habitissimo", "instagram", "houzz")


@dataclass
class ContractorLead:
    """One contractor row, platform-agnostic.

    Normalised-phone is the dedup key; ``raw_data`` is the escape hatch
    for provider-specific payloads (Habitissimo company_id, IG username,
    Houzz profile URL, etc.).
    """

    name: str = ""
    phone: str = ""
    trade: str = ""
    city: str = ""
    platform: str = ""
    rating: Optional[float] = None
    profile_url: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)

    @property
    def phone_normalized(self) -> str:
        """9-digit dedup key from :func:`domain.phone.normalize`, or ``""``."""

        if not self.phone:
            return ""
        try:
            return normalize(self.phone) or ""
        except Exception:  # noqa: BLE001 — defence in depth
            return ""

    @property
    def is_valid_phone(self) -> bool:
        """True if ``phone`` parses as a valid Spanish mobile."""

        if not self.phone:
            return False
        try:
            return is_valid_spanish(self.phone)
        except Exception:  # noqa: BLE001
            return False


AdapterFn = Callable[[str, str, int], Awaitable[list[ContractorLead]]]
"""Per-platform adapter signature: ``(trade, city, limit) -> leads``."""


async def _dispatch(platform: str, trade: str, city: str, limit: int) -> list[ContractorLead]:
    """Lazy-import and invoke a single platform's search.

    Import errors short-circuit to an empty list — a missing adapter
    dependency (e.g. Playwright not installed on a CI node) must never
    crash the batch."""

    try:
        if platform == "habitissimo":
            from scrapers.habitissimo import search as _search
        elif platform == "instagram":
            from scrapers.instagram import search as _search
        elif platform == "houzz":
            from scrapers.houzz import search as _search
        else:
            logger.warning("directories.search: unknown platform %r", platform)
            return []
    except ImportError as e:
        logger.warning("directories.search: adapter %r unavailable: %s", platform, e)
        return []

    return await _search(trade, city, limit=limit)


def _dedup(leads: Sequence[ContractorLead]) -> list[ContractorLead]:
    """Deduplicate by normalised phone. Leads with unparseable phones
    are dropped (audit §1.3 I1: invalid phones can't dedup reliably)."""

    seen: set[str] = set()
    out: list[ContractorLead] = []
    for lead in leads:
        key = lead.phone_normalized
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(lead)
    return out


async def search(
    trade: str,
    city: str,
    *,
    platforms: Optional[Sequence[str]] = None,
    limit: int = 50,
    dedup: bool = True,
) -> list[ContractorLead]:
    """Search for contractors across one or more platforms.

    :param platforms: Which adapters to query. ``None`` uses all three
        canonical platforms.
    :param limit: Per-adapter cap (adapters may return fewer).
    :param dedup: When ``True`` (default), deduplicate by normalised
        phone. Set ``False`` when the caller wants raw platform data
        (e.g. cross-platform attribution analysis).

    Per-adapter exceptions are caught and logged; a single adapter
    failure does not break the batch."""

    targets = tuple(platforms) if platforms else _PLATFORM_NAMES
    results: list[ContractorLead] = []

    for platform in targets:
        try:
            batch = await _dispatch(platform, trade, city, limit)
            results.extend(batch)
            logger.info(
                "directories.search | platform=%s | trade=%s | city=%s | returned=%d",
                platform,
                trade,
                city,
                len(batch),
            )
        except Exception as e:  # noqa: BLE001 — adapter-level isolation
            logger.error("directories.search | platform=%s failed: %s", platform, e)

    return _dedup(results) if dedup else results
