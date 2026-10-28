"""24-hour conversation window check.

Meta's WhatsApp Business policy lets us send free-form text for 24 hours
after an inbound user message; beyond that we must use pre-approved
templates. :func:`check_24h_window` performs the Supabase lookup that
tells :func:`messaging.whatsapp.send.send_wa_message` which branch to
take.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from core import http_client, sb_key, sb_url

logger = logging.getLogger(__name__)


def _sb_auth_headers() -> dict[str, str]:
    """Minimal read-auth headers for a Supabase REST GET."""
    key = sb_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }


async def check_24h_window(phone: str) -> bool:
    """Return True if we have an inbound WA message from ``phone`` within 24h.

    Never raises: Supabase errors, network failures, or empty tables all
    degrade to ``False`` (treat the window as closed, force template
    routing). That matches the pre-migration contract in
    ``leo_agent/send_wa.py``.
    """
    base = sb_url()
    key = sb_key()
    if not base or not key:
        return False
    clean = phone.lstrip("+")
    phone_variants = [f"+{clean}", clean]
    try:
        async with http_client(timeout=8) as client:
            or_clause = ",".join(f"phone_number.eq.{v}" for v in phone_variants)
            resp = await client.get(
                f"{base}/whatsapp_messages",
                params={
                    "select": "created_at",
                    "or": f"({or_clause})",
                    "role": "eq.user",
                    "order": "created_at.desc",
                    "limit": "1",
                },
                headers=_sb_auth_headers(),
            )
            if resp.status_code != 200:
                logger.debug("24h window check failed | status=%s", resp.status_code)
                return False
            rows = resp.json()
            if not rows:
                return False
            last_ts = rows[0].get("created_at", "")
            if not last_ts:
                return False
            from dateutil.parser import isoparse
            last_dt = isoparse(last_ts)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            age_secs = (datetime.now(timezone.utc) - last_dt).total_seconds()
            return age_secs < 86400
    except Exception as exc:  # noqa: BLE001
        logger.debug("24h window check error (assuming closed) | %s", exc)
        return False


__all__ = ["check_24h_window"]
