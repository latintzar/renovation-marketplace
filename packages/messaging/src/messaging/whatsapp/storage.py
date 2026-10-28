"""Persist outbound WhatsApp messages + the :class:`SendResult` contract.

Splitting storage from send keeps :func:`store_message` independently
testable — tests can mock Supabase without spinning up the full Meta API
dispatcher.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core import http_client, sb_headers, sb_url

logger = logging.getLogger(__name__)


@dataclass
class SendResult:
    """Structured return value for :func:`messaging.whatsapp.send.send_wa_message`.

    ``method`` is one of ``"text"``, ``"template"``, or
    ``"template_door_opener"`` (template sent on a cold number for a
    general-purpose message — the recipient must reply before a full
    message can be delivered).
    """

    ok: bool
    method: str = ""
    window_was_open: bool = False
    wa_message_id: str = ""
    note: str = ""
    error: str = ""


async def store_message(
    phone_number: str,
    role: str,
    text: str,
    message_type: str = "text",
    media_urls: Optional[List[str]] = None,
    media_types: Optional[List[str]] = None,
    wa_message_id: Optional[str] = None,
    reply_to_wa_id: Optional[str] = None,
    reply_to_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert one row into ``whatsapp_messages`` via Supabase REST.

    Raises :class:`RuntimeError` on non-2xx Supabase responses; callers
    that want fire-and-forget should wrap in a try/except — the main
    :func:`send_wa_message` path already does.
    """
    base_url = sb_url()
    headers = sb_headers()
    row: Dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "phone_number": phone_number,
        "role": role,
        "message_text": text,
        "message_type": message_type,
        "media_urls": media_urls or [],
        "media_types": media_types or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if wa_message_id:
        row["wa_message_id"] = wa_message_id
    if reply_to_wa_id:
        row["reply_to_wa_id"] = reply_to_wa_id
    if reply_to_text:
        row["reply_to_text"] = reply_to_text
    async with http_client(timeout=10) as client:
        resp = await client.post(
            f"{base_url}/whatsapp_messages",
            json=row,
            headers={**headers, "Prefer": "return=representation"},
        )
    if resp.status_code not in (200, 201):
        logger.error(
            "Failed to store message | status=%s body=%s",
            resp.status_code, resp.text[:300],
        )
        raise RuntimeError(f"Supabase insert failed: {resp.status_code}")
    stored = resp.json()
    return stored[0] if isinstance(stored, list) and stored else stored


__all__ = ["SendResult", "store_message"]
