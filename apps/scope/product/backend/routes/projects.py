"""
Projects — Project retrieval and cancellation
==============================================

GET  /v1/projects/:token        — Fetch a project (auth-gated: returns role-specific data)
POST /v1/projects/:token/cancel — Cancel a project and issue a full Stripe refund

Replaces the scattered project-level logic previously in milestone.py.
Legacy endpoint /api/job/cancel is preserved as a thin redirect in milestone.py.
"""

from __future__ import annotations

import logging
import os
from typing import Literal, Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import CurrentUser, optional_auth, require_auth
from core import sb_headers, sb_url
from payments import (
    SandboxContext,
    StripeNotConfigured,
    get_stripe_client,
    resolve_sandbox,
)
from state_machine import assert_transition
from core import http_client
from core import api_error

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Shared helpers (also imported by other route modules)
# ---------------------------------------------------------------------------

async def get_quote(quote_token: str) -> dict:
    """Fetch a quote row by token. Raises 404 if not found."""
    async with http_client(timeout=15) as client:
        resp = await client.get(
            f"{sb_url()}/quotes",
            params={"token": f"eq.{quote_token}", "select": "*", "limit": "1"},
            headers=sb_headers(),
        )
    if resp.status_code != 200 or not resp.json():
        raise api_error(404, "Project not found")
    return resp.json()[0]


async def get_contractor(contractor_id: str) -> dict:
    """Fetch a contractor row by id. Raises 404 if not found."""
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/contractors",
            params={"id": f"eq.{contractor_id}", "select": "*", "limit": "1"},
            headers=sb_headers(),
        )
    if resp.status_code != 200 or not resp.json():
        raise api_error(404, "Contractor not found")
    return resp.json()[0]


async def patch_quote(quote_token: str, data: dict) -> None:
    async with http_client(timeout=15) as client:
        await client.patch(
            f"{sb_url()}/quotes",
            params={"token": f"eq.{quote_token}"},
            json=data,
            headers=sb_headers(),
        )


def app_base_url() -> str:
    return os.getenv("APP_BASE_URL", "http://127.0.0.1:18260")


def tracking_url(quote_token: str, homeowner_email: str = "") -> str:
    """Build the homeowner-facing project tracking URL with optional email pre-fill."""
    base = f"{app_base_url()}{os.getenv('SCOPE_WEB_BASE_PATH', '/app')}/project/{quote_token}"
    if homeowner_email:
        from urllib.parse import quote as urlquote
        base += f"?email={urlquote(homeowner_email)}"
    return base


# ---------------------------------------------------------------------------
# GET /projects/:token
# ---------------------------------------------------------------------------

@router.get("/projects/{token}")
async def get_project(
    token: str,
    caller: Optional[CurrentUser] = Depends(optional_auth),
):
    """Return project data. Public read — auth resolves role-specific visibility."""
    quote = await get_quote(token)

    # Basic project data visible to everyone
    result: dict = {
        "token": quote.get("token"),
        "status": quote.get("status"),
        "payment_status": quote.get("payment_status"),
        "quote_data": quote.get("quote_data"),
        "milestones": quote.get("milestones"),
        "contractor_id": quote.get("contractor_id"),
        "is_sandbox": quote.get("is_sandbox", False),
        "created_at": quote.get("created_at"),
        "completed_at": quote.get("completed_at"),
    }

    # Homeowner-only fields (PII)
    if caller and (
        caller.email == quote.get("homeowner_email")
        or caller.id == quote.get("homeowner_auth_id")
    ):
        result["homeowner_email"] = quote.get("homeowner_email")
        result["homeowner_phone"] = quote.get("homeowner_phone")

    # Contractor-only fields
    if caller and caller.contractor_id == quote.get("contractor_id"):
        result["homeowner_email"] = quote.get("homeowner_email")
        result["homeowner_phone"] = quote.get("homeowner_phone")
        result["payment_intent_id"] = quote.get("payment_intent_id")

    return result


# ---------------------------------------------------------------------------
# POST /projects/:token/cancel
# ---------------------------------------------------------------------------

class CancelProjectRequest(BaseModel):
    reason: Optional[str] = None


@router.post("/projects/{token}/cancel")
async def cancel_project(
    token: str,
    req: CancelProjectRequest,
    caller: CurrentUser = Depends(require_auth),
    ctx: SandboxContext = Depends(resolve_sandbox),
):
    """Cancel a project and issue a full Stripe refund.

    Either the homeowner or the assigned contractor may cancel.
    Guard: no milestone must have progressed past 'pending'.
    """
    quote = await get_quote(token)

    # Determine who is cancelling and verify identity
    if caller.role == "homeowner":
        if caller.id != quote.get("homeowner_auth_id") and caller.email != quote.get("homeowner_email"):
            raise api_error(403, "Only the project homeowner can cancel")
        actor_role: Literal["homeowner", "contractor"] = "homeowner"
    else:
        if caller.contractor_id != quote.get("contractor_id"):
            raise api_error(403, "Only the assigned contractor can cancel")
        actor_role = "contractor"

    milestones = quote.get("milestones") or []
    assert_transition(
        "project", quote.get("status"), "cancelled",
        actor_role=actor_role,
        milestones=milestones,
        status_code=400,
    )

    if quote.get("status") in ("cancelled", "complete"):
        raise api_error(409, "Project is already finalised")

    payment_intent_id = quote.get("payment_intent_id")
    if not payment_intent_id:
        raise api_error(400, "No payment found to refund")

    suppress_wa = ctx.suppress_whatsapp
    try:
        stripe_client = get_stripe_client(ctx)
    except StripeNotConfigured:
        raise api_error(500, "Stripe not configured")

    try:
        refund = stripe_client.refunds.create(payment_intent=payment_intent_id)
        refund_id = refund.id
        refund_amount_cents = refund.amount
        logger.info(
            "Refund issued | project=%s refund=%s amount_eur=%.2f",
            token[:8], refund_id[:16], refund_amount_cents / 100,
        )
    except stripe.error.StripeError as e:
        logger.error("Refund failed | project=%s: %s", token[:8], e)
        raise HTTPException(status_code=500, detail=f"Refund failed: {str(e)}")

    # Record cancellation
    async with http_client(timeout=10) as client:
        await client.post(
            f"{sb_url()}/cancellations",
            json={
                "scope_token": token,
                "cancelled_by": actor_role,
                "reason": req.reason,
                "stripe_refund_id": refund_id,
                "refund_amount_cents": refund_amount_cents,
            },
            headers=sb_headers(),
        )

    await patch_quote(token, {"status": "cancelled", "payment_status": "refunded"})

    # Notify both parties
    from routes.notifications import send_notification, send_whatsapp
    contractor = await get_contractor(quote["contractor_id"])
    contractor_phone = contractor.get("phone", "")
    homeowner_phone = quote.get("homeowner_phone", "")
    scope_title = (quote.get("quote_data") or {}).get("title", "el trabajo")
    msg = f"El trabajo '{scope_title}' ha sido cancelado. Reembolso en 5–7 días hábiles."

    homeowner_id = quote.get("homeowner_auth_id") or quote.get("homeowner_email") or ""
    if homeowner_id:
        await send_notification(
            user_id=homeowner_id, quote_token=token, notif_type="job_cancelled",
            phone=homeowner_phone, whatsapp_message=msg, suppress_wa=suppress_wa,
        )
    await send_notification(
        user_id=quote["contractor_id"], quote_token=token, notif_type="job_cancelled",
        phone=contractor_phone, whatsapp_message=msg, suppress_wa=suppress_wa,
    )

    return {"ok": True, "refund_id": refund_id, "message": "Project cancelled and refund issued"}
