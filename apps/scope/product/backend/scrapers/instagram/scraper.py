"""IG orchestrator — compose :mod:`.search` + :mod:`.profile` into
:class:`~scrapers.directories.ContractorLead` records.

Wave-9 scope: stub returning ``[]``; full implementation walks
Google SERP → profile HTML → phone extraction in Phase 5.
"""
from __future__ import annotations

from ..directories import ContractorLead

__all__ = ["search"]


async def search(
    trade: str, city: str, *, limit: int = 50
) -> list[ContractorLead]:
    """IG contractor search (Google SERP → profile parse → leads)."""

    return []
