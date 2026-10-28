"""docuSeal webhook verification + event parsing.

Delegates HMAC verification to :func:`core.auth.verify_webhook_signature`
so the Stripe / Meta / Resend webhook patterns share one impl.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

from core.auth import verify_webhook_signature

from .types import DocusealWebhookEvent

__all__ = ["verify_docuseal_webhook", "parse_webhook_event"]


def verify_docuseal_webhook(
    body: bytes,
    signature: str,
    secret: str,
) -> bool:
    """HMAC-SHA256 verify the ``X-DocuSeal-Signature`` header.

    Returns ``True`` on a valid signature, ``False`` on any mismatch or
    malformed input. Never raises.
    """

    if not signature or not secret:
        return False
    try:
        return verify_webhook_signature(
            payload=body, signature=signature, secret=secret, algo="sha256"
        )
    except Exception:
        return False


def parse_webhook_event(body: bytes) -> DocusealWebhookEvent:
    """Parse a docuSeal webhook body into :class:`DocusealWebhookEvent`.

    Unknown event types pass through (the DTO tolerates vendor
    additions via ``extra="allow"``).
    """

    payload: Dict[str, Any] = json.loads(body)
    data = payload.get("data") or {}
    occurred_raw = payload.get("occurred_at") or payload.get("created_at")
    occurred_at = _parse_iso(occurred_raw) if occurred_raw else datetime.now(timezone.utc)
    return DocusealWebhookEvent(
        event_type=str(payload.get("event_type") or payload.get("event") or ""),
        submission_id=str(payload.get("submission_id") or data.get("submission_id") or ""),
        external_id=str(payload.get("external_id") or data.get("external_id") or ""),
        status=str(payload.get("status") or data.get("status") or ""),
        occurred_at=occurred_at,
        data=data,
    )


def _parse_iso(value: str) -> datetime:
    normalised = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalised)
