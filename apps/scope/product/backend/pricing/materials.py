"""Live-scraped materials pricing (stub in Phase 3.5b).

The full flow — fetch a Leroy Merlin / manufacturer page via the
``packages/scraping`` adapters and extract the current price — is out
of scope for the pricing migration wave. The public signature lives
here so downstream callers don't refactor when it flips to live.

When wired:

- Decorated with ``core.resilience.timed_cache(ttl=timedelta(hours=24))``
  to avoid hammering vendors.
- Delegates to per-site adapters under ``packages/scraping/adapters/``
  (Leroy Merlin, Roca, VitrA).
- Returns a :class:`LivePrice` or raises ``VendorUnavailableError`` on
  anti-bot block.
"""

from __future__ import annotations

from .types import LivePrice

__all__ = ["lookup_live_price"]


def lookup_live_price(sku: str) -> LivePrice:
    """STUB — raises ``NotImplementedError`` until ``scraping`` lands
    vendor-aware helpers.

    Public signature defined now so callers can import/type-check
    against the eventual live implementation.
    """

    raise NotImplementedError(
        "lookup_live_price is not wired in Phase 3.5b. "
        "Will be enabled once packages/scraping ships vendor-aware helpers "
        "(see design.md §D12 and Phase 4 roadmap)."
    )
