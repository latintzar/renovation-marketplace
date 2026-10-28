"""Habitissimo RFQ blast helpers (scaffolded).

Wave-9 scope: signatures only. ``AD_TEMPLATES`` / ``TRADES`` / ``CITIES``
data migrate to ``blast_data.json`` in Phase 5 (audit §1.9 S2).
"""
from __future__ import annotations

from typing import Any, Optional

__all__ = ["submit_rfq", "build_submissions"]


async def submit_rfq(
    trade: str,
    city: str,
    *,
    message: str,
    session: Optional[dict] = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Submit one RFQ to Habitissimo's ``/v1/serviceRequest`` endpoint.

    Returns ``{"status": "ok", "request_id": ...}`` on success or
    ``{"status": "error", "reason": ...}`` on failure. 429 responses
    surface as ``{"status": "throttled", ...}`` so the caller can
    back off.

    .. note::
       **Wave-9 scope**: stub raising :class:`NotImplementedError`.
    """

    raise NotImplementedError(
        "scrapers.habitissimo.blast.submit_rfq is scaffolded "
        "for Wave 9; full implementation in Phase 5."
    )


def build_submissions(
    trades: list[str], cities: list[str], templates: list[str]
) -> list[dict[str, Any]]:
    """Cartesian product of trades × cities × templates.

    Pure function — deterministic. Returns a list of dicts ready for
    :func:`submit_rfq` calls:

    .. code-block:: python

        [{"trade": "fontaneros", "city": "madrid", "message": "..."}, ...]
    """

    if not trades or not cities or not templates:
        return []
    out: list[dict[str, Any]] = []
    template_cycle = iter(templates)
    for trade in trades:
        for city in cities:
            try:
                message = next(template_cycle)
            except StopIteration:
                template_cycle = iter(templates)
                message = next(template_cycle)
            out.append({"trade": trade, "city": city, "message": message})
    return out
