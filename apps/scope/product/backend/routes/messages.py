"""
Messages — In-job messaging thread between homeowner and contractor
===================================================================

Lightweight post-payment message thread. Both parties can message after
a scope is paid. Frontend uses Supabase Realtime Broadcast for live updates.

Endpoints:
  POST /api/messages/send     — Send a message
  GET  /api/messages/:token   — Load message history
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from core import sb_url, sb_headers, CurrentUser, require_auth
from project_access import project_party
from payments import SandboxContext, resolve_sandbox
from core import http_client
from core import api_error
from fastapi import Depends

logger = logging.getLogger(__name__)
router = APIRouter()




class SendMessageRequest(BaseModel):
    quote_token: str
    sender_role: str  # 'homeowner' | 'contractor'
    sender_id: str
    body: str


@router.post("/messages/send")
async def send_message(req: SendMessageRequest, ctx: SandboxContext = Depends(resolve_sandbox), caller: CurrentUser = Depends(require_auth)):
    """Insert a message to job_messages. Supabase Realtime handles delivery.

    WhatsApp fallback is suppressed when X-Sandbox: true.
    """
    sandbox = ctx.is_sandbox
    suppress_wa = ctx.suppress_whatsapp
    if req.sender_role not in ("homeowner", "contractor"):
        raise api_error(400, "sender_role must be homeowner or contractor")
    if not req.body.strip():
        raise api_error(400, "Message body cannot be empty")


    # Verify scope exists and is paid
    async with http_client(timeout=10) as client:
        quote_resp = await client.get(
            f"{sb_url()}/quotes",
            params={"token": f"eq.{req.quote_token}", "select": "payment_status,contractor_id,homeowner_auth_id,homeowner_phone", "limit": "1"},
            headers=sb_headers(),
        )
    if quote_resp.status_code != 200 or not quote_resp.json():
        raise api_error(404, "Quote not found")

    quote = quote_resp.json()[0]
    sender_role, sender_id = project_party(caller, quote)
    if quote.get("payment_status") != "paid":
        raise api_error(400, "Messaging only available for paid quotes")

    # Insert message — note: job_messages table uses scope_token (legacy column name)
    # Prefer: return=representation ensures Supabase returns the inserted row so the
    # frontend can replace its optimistic entry with the real ID.
    insert_headers = {**sb_headers(), "Prefer": "return=representation"}
    async with http_client(timeout=10) as client:
        ins_resp = await client.post(
            f"{sb_url()}/job_messages",
            json={
                "scope_token": req.quote_token,
                "sender_role": sender_role,
                "sender_id": sender_id,
                "body": req.body,
            },
            headers=insert_headers,
        )
    if ins_resp.status_code not in (200, 201):
        logger.error("Failed to insert message: %s", ins_resp.text)
        raise api_error(500, "Failed to send message")

    rows = ins_resp.json()
    message_row = rows[0] if isinstance(rows, list) and rows else {}

    # WhatsApp fallback — send to the other party
    try:
        app_base = os.getenv("APP_BASE_URL", "http://127.0.0.1:18260")
        chat_url = f"{app_base}/app/job-chat/{req.quote_token}"

        from routes.milestone import _send_whatsapp, _get_contractor
        if sender_role == "contractor":
            contractor = await _get_contractor(quote["contractor_id"])
            sender_name = contractor.get("business_name") or contractor.get("name") or "Tu contratista"
            recipient_phone = quote.get("homeowner_phone", "")
            if recipient_phone:
                await _send_whatsapp(recipient_phone, f"{sender_name} te ha enviado un mensaje. {chat_url}", suppress=suppress_wa)
        else:
            contractor = await _get_contractor(quote["contractor_id"])
            contractor_phone = contractor.get("phone", "")
            if contractor_phone:
                await _send_whatsapp(contractor_phone, f"El propietario te ha enviado un mensaje. {chat_url}", suppress=suppress_wa)
    except Exception as exc:
        logger.warning("WhatsApp fallback failed: %s", exc)

    return {"ok": True, "message": message_row}


@router.get("/messages/{quote_token}")
async def get_messages(quote_token: str, limit: int = 100, caller: CurrentUser = Depends(require_auth)):
    """Return this authenticated project party’s message history."""
    from routes.projects import get_quote
    quote = await get_quote(quote_token)
    project_party(caller, quote)
    limit = max(1, min(limit, 200))
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/job_messages",
            params={
                "scope_token": f"eq.{quote_token}",  # legacy column name in job_messages table
                "select": "*",
                "order": "created_at.asc",
                "limit": str(limit),
            },
            headers=sb_headers(),
        )
    if resp.status_code != 200:
        logger.error("Failed to fetch messages for quote %s: %s", quote_token[:8], resp.text)
        return []
    return resp.json()
