"""Resend API — the single email dispatcher.

Collapses two pre-migration paths onto one function:

* ``leo_agent/persistence.py::send_email_resend`` — contractor onboarding /
  cold outreach email.
* ``shared/comms.py::_send_email`` — the inline ``httpx.AsyncClient`` POST
  called from :func:`messaging.comms.notify`.

:func:`send_email` is the canonical new name; :func:`send_email_resend`
is preserved as a thin alias so existing call sites keep working during
the caller-flip phase.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from core import http_client

logger = logging.getLogger(__name__)

_RESEND_URL = "https://api.resend.com/emails"


def _resolve_api_key() -> str:
    """Pull the Resend API key from env.

    Pre-migration the legacy persistence helper also fell back to reading
    ``/root/leo/.env.local`` directly; that was a dev-convenience hack. We
    drop it here — the canonical path is env-only. Callers running under
    systemd already have ``/etc/scope-backend.env`` loaded; dev scripts
    that want the fallback should source the env file themselves.
    """
    return os.getenv("RESEND_API_KEY", "")


async def send_email(
    to: str,
    subject: str,
    body_html: str = "",
    body_text: str = "",
    *,
    from_label: str = "Leo",
    from_address: str = "project-agent@projects.leo.casa",
    reply_to: Optional[str] = None,
    tags: Optional[list[dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Send an email via Resend.

    Returns ``{"ok": True, "id": ...}`` on success, or
    ``{"ok": False, "error": ..., "detail": ...}`` on any failure. Never
    raises — Resend hiccups should not cascade into upstream agent turns.
    """
    api_key = _resolve_api_key()
    if not api_key:
        logger.error("send_email: RESEND_API_KEY not found")
        return {"ok": False, "error": "resend_api_key_missing"}

    payload: Dict[str, Any] = {
        "from": f"{from_label} <{from_address}>",
        "to": to,
        "subject": subject,
    }
    if body_html:
        payload["html"] = body_html
    if body_text:
        payload["text"] = body_text
    if reply_to:
        payload["reply_to"] = reply_to
    if tags:
        payload["tags"] = tags

    try:
        async with http_client(timeout=20) as client:
            resp = await client.post(
                _RESEND_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                logger.info(
                    "send_email ok | to=%s subject=%s id=%s",
                    to, subject[:40], data.get("id"),
                )
                return {"ok": True, "id": data.get("id")}
            logger.warning(
                "send_email resend error | status=%s body=%s",
                resp.status_code, resp.text[:300],
            )
            return {
                "ok": False,
                "error": f"resend_{resp.status_code}",
                "detail": resp.text[:300],
            }
    except Exception as exc:  # noqa: BLE001
        logger.error("send_email exception | %s", exc, exc_info=True)
        return {"ok": False, "error": str(exc)}


async def send_email_resend(
    to: str,
    subject: str,
    body_html: str,
    body_text: str = "",
    from_label: str = "Leo",
    from_address: str = "project-agent@projects.leo.casa",
) -> Dict[str, Any]:
    """Legacy alias for :func:`send_email`.

    Preserves the exact 6-positional-arg signature used pre-migration so
    the codemod can replace call sites without touching argument order.
    Delete after all callers have migrated to :func:`send_email`.
    """
    return await send_email(
        to=to,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        from_label=from_label,
        from_address=from_address,
    )
