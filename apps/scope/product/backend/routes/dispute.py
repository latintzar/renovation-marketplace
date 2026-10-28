"""
Dispute / Get Help — Homeowner opens a support conversation
=============================================================

When a homeowner has an issue with a milestone (quality concerns, disagreement
with the contractor), they tap "Get Help" which opens a Chatwoot conversation
tagged with the quote and milestone context. An aparejador (building surveyor)
reviews the evidence and mediates.

Endpoints:
  POST /dispute/open    — Homeowner opens a dispute on a milestone
  POST /dispute/reply   — Send a message into an existing dispute conversation
  GET  /dispute/{token} — Get dispute status and message history
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core import sb_url, sb_headers
from payments import SandboxContext, resolve_sandbox
from core import http_client
from core import api_error
from routes.chatwoot import (
    CHATWOOT_API_TOKEN,
    get_or_create_contact,
    get_or_create_conversation,
    _cw,
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_quote(token: str) -> dict:
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/quotes",
            params={"token": f"eq.{token}", "select": "*", "limit": "1"},
            headers=sb_headers(),
        )
        if resp.status_code == 200 and resp.json():
            return resp.json()[0]
    raise api_error(404, "Quote not found")


async def _get_contractor(contractor_id: str) -> dict:
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/contractors",
            params={"id": f"eq.{contractor_id}", "select": "*", "limit": "1"},
            headers=sb_headers(),
        )
        if resp.status_code == 200 and resp.json():
            return resp.json()[0]
    return {}


# ── POST /dispute/open ──────────────────────────────────────────────

class OpenDisputeRequest(BaseModel):
    quote_token: str
    milestone_index: int
    homeowner_name: str
    homeowner_phone: str
    reason: str
    photos: list[str] = []


@router.post("/dispute/open")
async def open_dispute(req: OpenDisputeRequest, ctx: SandboxContext = Depends(resolve_sandbox)):
    """Open a dispute on a milestone. Creates a Chatwoot conversation with full context.

    The conversation is pre-populated with:
    - Quote details (contractor, amount, milestones)
    - The specific milestone being disputed
    - Homeowner's reason and any photos
    - Instructions for the aparejador reviewer
    """
    quote = await _get_quote(req.quote_token)

    if quote.get("payment_status") != "paid":
        raise api_error(400, "Cannot dispute an unpaid scope")

    milestones = quote.get("milestones") or []
    if req.milestone_index >= len(milestones):
        raise api_error(400, "Invalid milestone index")

    milestone = milestones[req.milestone_index]
    if milestone.get("status") not in ("proof_submitted", "released"):
        raise HTTPException(
            status_code=400,
            detail=f"Milestone must have proof submitted to dispute (current: {milestone.get('status')})",
        )

    contractor = await _get_contractor(quote.get("contractor_id", ""))
    contractor_name = contractor.get("name", "Unknown contractor")

    milestone_title = milestone.get("title", f"Milestone {req.milestone_index + 1}")
    amount_eur = (milestone.get("amount_cents", 0) or 0) / 100

    # Build context message for the aparejador
    context_lines = [
        f"🔴 DISPUTE OPENED — {milestone_title} (€{amount_eur:.2f})",
        f"",
        f"Homeowner: {req.homeowner_name} ({req.homeowner_phone})",
        f"Contractor: {contractor_name}",
        f"Quote: {req.quote_token[:12]}...",
        f"Milestone: #{req.milestone_index + 1} — {milestone_title}",
        f"Milestone status: {milestone.get('status')}",
        f"",
        f"Reason: {req.reason}",
    ]
    if req.photos:
        context_lines.append(f"")
        context_lines.append(f"Photos attached: {len(req.photos)}")
        for i, url in enumerate(req.photos, 1):
            context_lines.append(f"  [{i}] {url}")

    context_lines.extend([
        "",
        "— Action required: review proof photos vs scope, mediate between parties.",
        f"— Scope URL: /app/project/{req.quote_token}",
    ])
    context_message = "\n".join(context_lines)

    # In sandbox mode without Chatwoot configured, simulate the conversation
    if ctx.is_sandbox and not CHATWOOT_API_TOKEN:
        import uuid
        fake_conv_id = abs(hash(req.quote_token + str(req.milestone_index))) % 100000
        logger.info(
            "Sandbox dispute opened (no Chatwoot) | quote=%s milestone=%d conv=%d",
            req.quote_token[:8], req.milestone_index, fake_conv_id,
        )

        # Store dispute in Supabase for tracking
        await _store_dispute(
            req.quote_token, req.milestone_index, fake_conv_id,
            req.reason, req.homeowner_phone, ctx.is_sandbox,
        )

        return {
            "ok": True,
            "conversation_id": fake_conv_id,
            "sandbox": True,
            "message": "Dispute opened (sandbox — Chatwoot not configured)",
        }

    # Create Chatwoot conversation
    contact_id = await get_or_create_contact(req.homeowner_phone, req.homeowner_name)
    if not contact_id:
        raise api_error(500, "Failed to create support contact")

    conv_id = await get_or_create_conversation(contact_id)
    if not conv_id:
        raise api_error(500, "Failed to create support conversation")

    # Post the context message as an internal note
    await _cw("post", f"/conversations/{conv_id}/messages", json={
        "content": context_message,
        "message_type": "outgoing",
        "private": True,  # internal note — only agents see this
    })

    # Post the homeowner's reason as an incoming message
    await _cw("post", f"/conversations/{conv_id}/messages", json={
        "content": f"I need help with {milestone_title}: {req.reason}",
        "message_type": "incoming",
        "private": False,
    })

    # Tag the conversation with dispute metadata
    await _cw("post", f"/conversations/{conv_id}/labels", json={
        "labels": ["dispute", f"quote-{req.quote_token[:8]}"],
    })

    # Update milestone status to disputed
    milestones[req.milestone_index]["status"] = "disputed"
    async with http_client(timeout=10) as client:
        await client.patch(
            f"{sb_url()}/quotes",
            params={"token": f"eq.{req.quote_token}"},
            json={"milestones": milestones},
            headers=sb_headers(),
        )

    # Store dispute record
    await _store_dispute(
        req.quote_token, req.milestone_index, conv_id,
        req.reason, req.homeowner_phone, ctx.is_sandbox,
    )

    logger.info(
        "Dispute opened | quote=%s milestone=%d conv=%d sandbox=%s",
        req.quote_token[:8], req.milestone_index, conv_id, ctx.is_sandbox,
    )

    return {
        "ok": True,
        "conversation_id": conv_id,
        "sandbox": ctx.is_sandbox,
        "message": "Dispute opened — an aparejador will review shortly",
    }


async def _store_dispute(
    quote_token: str,
    milestone_index: int,
    conversation_id: int,
    reason: str,
    homeowner_phone: str,
    is_sandbox: bool,
) -> None:
    """Store dispute record in Supabase for tracking."""
    async with http_client(timeout=10) as client:
        resp = await client.post(
            f"{sb_url()}/disputes",
            json={
                "quote_token": quote_token,
                "milestone_index": milestone_index,
                "chatwoot_conversation_id": conversation_id,
                "reason": reason,
                "homeowner_phone": homeowner_phone,
                "status": "open",
                "is_sandbox": is_sandbox,
            },
            headers=sb_headers(),
        )
        if resp.status_code not in (200, 201):
            logger.warning("Failed to store dispute record: %s", resp.text[:200])


# ── POST /dispute/reply ─────────────────────────────────────────────

class DisputeReplyRequest(BaseModel):
    quote_token: str
    conversation_id: int
    sender_role: str  # 'homeowner' | 'aparejador' | 'contractor'
    sender_name: str
    body: str


@router.post("/dispute/reply")
async def reply_to_dispute(req: DisputeReplyRequest, ctx: SandboxContext = Depends(resolve_sandbox)):
    """Send a message in a dispute conversation.

    Aparejador messages are outgoing (agent); homeowner/contractor are incoming (customer).
    """
    if not req.body.strip():
        raise api_error(400, "Message body cannot be empty")

    if req.sender_role not in ("homeowner", "aparejador", "contractor"):
        raise api_error(400, "sender_role must be homeowner, aparejador, or contractor")

    # In sandbox without Chatwoot, just log and store
    if ctx.is_sandbox and not CHATWOOT_API_TOKEN:
        logger.info(
            "Sandbox dispute reply | conv=%d role=%s body=%s",
            req.conversation_id, req.sender_role, req.body[:80],
        )
        return {"ok": True, "sandbox": True}

    # Aparejador messages are "outgoing" (from agent); others are "incoming" (from customer)
    message_type = "outgoing" if req.sender_role == "aparejador" else "incoming"
    prefix = f"[{req.sender_name}] " if req.sender_role != "aparejador" else ""

    result = await _cw("post", f"/conversations/{req.conversation_id}/messages", json={
        "content": f"{prefix}{req.body}",
        "message_type": message_type,
        "private": False,
    })

    if not result:
        raise api_error(500, "Failed to send message")

    return {"ok": True, "message_id": result.get("id")}


# ── GET /dispute/{token} ────────────────────────────────────────────

@router.get("/dispute/{quote_token}")
async def get_disputes(quote_token: str):
    """Get all disputes for a quote."""
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/disputes",
            params={
                "quote_token": f"eq.{quote_token}",
                "select": "*",
                "order": "created_at.desc",
            },
            headers=sb_headers(),
        )
        if resp.status_code == 200:
            return {"ok": True, "disputes": resp.json()}
    return {"ok": True, "disputes": []}
