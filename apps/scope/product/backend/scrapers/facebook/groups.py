"""Facebook group GraphQL response capture (scaffolded).

Audit §3.2: the pre-migration ``scripts/fb_monitor.py`` intercepted
FB group feed GraphQL responses to extract post metadata. The capture
logic moves here so the library is reusable; the cron orchestration
stays in ``scripts/fb_monitor.py``.

Wave-9 scope: signature declared; Phase 5 ports the ``page.on("response", ...)``
handler + JSON deserialisation.
"""
from __future__ import annotations

from typing import Any

__all__ = ["capture_graphql"]


async def capture_graphql(
    page: Any, *, timeout_ms: int = 10000, op_name: str = "GroupsCometFeedRegularStoriesPaginationQuery"
) -> list[dict[str, Any]]:
    """Capture FB GraphQL responses matching ``op_name`` over
    ``timeout_ms`` milliseconds.

    Returns the list of decoded JSON payloads (one per matching
    response).

    .. note::
       **Wave-9 scope**: stub returning ``[]``. See
       ``internal/refactor/packages/scraping/design.md`` §D7.
    """

    return []
