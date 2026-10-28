"""
Notifications — In-app bell + WhatsApp delivery
================================================

GET  /v1/notifications          — Fetch notifications for the authenticated user (JWT)
POST /v1/notifications/mark-read — Mark notification IDs as read

The legacy GET /api/notifications?user_id=… endpoint is preserved in
milestone.py for backward compat until the frontend migrates.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import CurrentUser, require_auth
from core import sb_headers, sb_url
from core import http_client

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Shared notification helpers — imported by projects/milestones/variations
# ---------------------------------------------------------------------------

async def _insert_notification(
    user_id: str,
    quote_token: str,
    notif_type: str,
    milestone_index: Optional[int] = None,
) -> None:
    """Insert a notification row (in-app bell). Table uses scope_token column."""
    payload: dict = {"user_id": user_id, "scope_token": quote_token, "type": notif_type}
    if milestone_index is not None:
        payload["milestone_index"] = milestone_index
    async with http_client(timeout=10) as client:
        resp = await client.post(
            f"{sb_url()}/notifications",
            json=payload,
            headers=sb_headers(),
        )
    if resp.status_code not in (200, 201):
        logger.warning(
            "Failed to insert notification type=%s user=%s: %s",
            notif_type, user_id[:8], resp.text,
        )


async def send_whatsapp(phone: str, message: str, suppress: bool = False) -> None:
    """Send a WhatsApp message via the unified send_wa stack.

    When suppress=True the message is logged but not sent (sandbox mode).
    """
    if not phone:
        return
    if suppress:
        logger.info(
            "[SANDBOX] WhatsApp SUPPRESSED → %s*** | msg=%s",
            phone[:6], message[:80],
        )
        return
    try:
        from messaging import send_wa_message_sync
        send_wa_message_sync(
            phone, message,
            purpose="milestone",
            do_store=False,
            skip_window_check=True,
        )
    except Exception as exc:
        logger.warning("WhatsApp send failed for %s: %s", phone[:6] + "***", exc)


async def send_notification(
    user_id: str,
    quote_token: str,
    notif_type: str,
    milestone_index: Optional[int] = None,
    phone: Optional[str] = None,
    whatsapp_message: Optional[str] = None,
    suppress_wa: bool = False,
) -> None:
    """Insert in-app notification and optionally deliver via WhatsApp."""
    await _insert_notification(user_id, quote_token, notif_type, milestone_index)
    if phone and whatsapp_message:
        await send_whatsapp(phone, whatsapp_message, suppress=suppress_wa)


# ---------------------------------------------------------------------------
# GET /notifications — auth-gated, user_id from JWT
# ---------------------------------------------------------------------------

@router.get("/notifications")
async def get_notifications(
    caller: CurrentUser = Depends(require_auth),
    limit: int = 30,
):
    """Return notifications for the authenticated user, newest first."""
    # Use auth user id for lookup; fall back to email for homeowners stored by email
    user_id = caller.contractor_id if caller.contractor_id else caller.id
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/notifications",
            params={
                "user_id": f"eq.{user_id}",
                "select": "*",
                "order": "created_at.desc",
                "limit": str(limit),
            },
            headers=sb_headers(),
        )
    return resp.json() if resp.status_code == 200 else []


# ---------------------------------------------------------------------------
# POST /notifications/mark-read
# ---------------------------------------------------------------------------

class MarkReadRequest(BaseModel):
    ids: List[str]


@router.post("/notifications/mark-read")
async def mark_notifications_read(
    req: MarkReadRequest,
    caller: CurrentUser = Depends(require_auth),
):
    """Mark notification IDs as read. Caller must be authenticated."""
    user_id = caller.contractor_id if caller.contractor_id else caller.id
    for notif_id in req.ids:
        async with http_client(timeout=5) as client:
            await client.patch(
                f"{sb_url()}/notifications",
                params={"id": f"eq.{notif_id}", "user_id": f"eq.{user_id}"},
                json={"read": True},
                headers=sb_headers(),
            )
    return {"ok": True}
