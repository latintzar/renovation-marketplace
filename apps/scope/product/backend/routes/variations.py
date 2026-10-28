"""
Variations — Change orders between contractor and homeowner
===========================================================

POST /v1/projects/:token/variations          — Contractor proposes a change order
POST /v1/projects/:token/variations/:id/approve — Homeowner approves (creates Stripe Checkout)
POST /v1/projects/:token/variations/:id/decline — Homeowner declines
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import CurrentUser, require_auth
from core import sb_headers, sb_url
from payments import (
    SandboxContext,
    StripeNotConfigured,
    get_stripe_client,
    resolve_sandbox,
)
from core import http_client
from core import api_error
from routes.projects import get_quote, get_contractor, app_base_url, tracking_url
from routes.notifications import send_notification

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# POST /projects/:token/variations
# ---------------------------------------------------------------------------

class CreateVariationBody(BaseModel):
    title: str
    description: Optional[str] = None
    photos: List[str] = []
    amount_cents: int
    reason: Optional[str] = None


@router.post("/projects/{token}/variations")
async def create_variation(
    token: str,
    body: CreateVariationBody,
    caller: CurrentUser = Depends(require_auth),
    ctx: SandboxContext = Depends(resolve_sandbox),
):
    """Contractor proposes a change order / variation."""
    if caller.role != "contractor":
        raise api_error(403, "Only a contractor can propose variations")

    suppress_wa = ctx.suppress_whatsapp
    quote = await get_quote(token)

    if quote.get("contractor_id") != caller.contractor_id:
        raise api_error(403, "You are not assigned to this project")

    async with http_client(timeout=15) as client:
        ins_resp = await client.post(
            f"{sb_url()}/variation_orders",
            json={
                "scope_token": token,
                "title": body.title,
                "description": body.description,
                "photos": body.photos,
                "amount_cents": body.amount_cents,
                "reason": body.reason,
                "status": "pending",
            },
            headers=sb_headers(),
        )
    if ins_resp.status_code not in (200, 201):
        raise api_error(500, "Failed to create variation order")

    homeowner_id = quote.get("homeowner_auth_id") or quote.get("homeowner_email") or ""
    homeowner_phone = quote.get("homeowner_phone", "")
    ho_email = quote.get("homeowner_email") or ""
    contractor = await get_contractor(quote["contractor_id"])
    contractor_name = contractor.get("name", "Tu contratista")
    project_url = tracking_url(token, ho_email)
    amount_eur = f"€{body.amount_cents / 100:.0f}"

    if homeowner_id:
        await send_notification(
            user_id=homeowner_id,
            quote_token=token,
            notif_type="variation_created",
            phone=homeowner_phone,
            whatsapp_message=(
                f"{contractor_name} propone un cambio de obra por {amount_eur}: {body.title}. "
                f"Revísalo: {project_url}"
            ),
            suppress_wa=suppress_wa,
        )

    return {"ok": True, "message": "Variation order sent to homeowner"}


# ---------------------------------------------------------------------------
# POST /projects/:token/variations/:id/approve
# ---------------------------------------------------------------------------

@router.post("/projects/{token}/variations/{variation_id}/approve")
async def approve_variation(
    token: str,
    variation_id: str,
    caller: CurrentUser = Depends(require_auth),
    ctx: SandboxContext = Depends(resolve_sandbox),
):
    """Homeowner approves a variation — creates a new Stripe Checkout for the extra amount."""
    if caller.role != "homeowner":
        raise api_error(403, "Only the homeowner can approve variations")

    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/variation_orders",
            params={"id": f"eq.{variation_id}", "select": "*", "limit": "1"},
            headers=sb_headers(),
        )
    if resp.status_code != 200 or not resp.json():
        raise api_error(404, "Variation not found")

    variation = resp.json()[0]
    if variation.get("status") != "pending":
        raise api_error(409, "Variation already actioned")

    quote_tok = variation.get("scope_token") or variation.get("quote_token", "")
    if quote_tok != token:
        raise api_error(400, "Variation does not belong to this project")

    quote = await get_quote(quote_tok)

    # Identity check
    if caller.id != quote.get("homeowner_auth_id") and caller.email != quote.get("homeowner_email"):
        raise api_error(403, "Only the project homeowner can approve variations")

    contractor = await get_contractor(quote["contractor_id"])
    try:
        stripe_client = get_stripe_client(ctx)
    except StripeNotConfigured:
        raise api_error(500, "Stripe not configured")
    base = app_base_url()

    session = stripe_client.checkout.sessions.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "eur",
                "unit_amount": variation["amount_cents"],
                "product_data": {
                    "name": f"Cambio de obra: {variation['title']}",
                    "description": variation.get("description") or variation["title"],
                },
            },
            "quantity": 1,
        }],
        payment_intent_data={
            "metadata": {
                "variation_id": variation_id,
                "quote_token": quote_tok,
                "contractor_stripe_account": contractor.get("stripe_account_id", ""),
            }
        },
        customer_email=caller.email,
        success_url=f"{base}/app/project/{quote_tok}?variation_paid=true",
        cancel_url=f"{base}/app/project/{quote_tok}",
        locale="es",
        metadata={"variation_id": variation_id, "quote_token": quote_tok},
    )

    async with http_client(timeout=10) as client:
        await client.patch(
            f"{sb_url()}/variation_orders",
            params={"id": f"eq.{variation_id}"},
            json={"status": "approved", "checkout_session_id": session.id},
            headers=sb_headers(),
        )

    return {"ok": True, "checkout_url": session.url}


# ---------------------------------------------------------------------------
# POST /projects/:token/variations/:id/decline
# ---------------------------------------------------------------------------

@router.post("/projects/{token}/variations/{variation_id}/decline")
async def decline_variation(
    token: str,
    variation_id: str,
    caller: CurrentUser = Depends(require_auth),
    ctx: SandboxContext = Depends(resolve_sandbox),
):
    """Homeowner declines a variation."""
    if caller.role != "homeowner":
        raise api_error(403, "Only the homeowner can decline variations")

    suppress_wa = ctx.suppress_whatsapp

    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/variation_orders",
            params={"id": f"eq.{variation_id}", "select": "scope_token,status", "limit": "1"},
            headers=sb_headers(),
        )
    if resp.status_code != 200 or not resp.json():
        raise api_error(404, "Variation not found")

    variation = resp.json()[0]
    if variation.get("status") != "pending":
        raise api_error(409, "Variation already actioned")

    quote_tok = variation.get("scope_token") or variation.get("quote_token", "")
    if quote_tok != token:
        raise api_error(400, "Variation does not belong to this project")

    quote = await get_quote(quote_tok)

    # Identity check
    if caller.id != quote.get("homeowner_auth_id") and caller.email != quote.get("homeowner_email"):
        raise api_error(403, "Only the project homeowner can decline variations")

    async with http_client(timeout=10) as client:
        await client.patch(
            f"{sb_url()}/variation_orders",
            params={"id": f"eq.{variation_id}"},
            json={"status": "declined"},
            headers=sb_headers(),
        )

    contractor_id = quote.get("contractor_id", "")
    contractor = await get_contractor(contractor_id)
    contractor_phone = contractor.get("phone", "")

    await send_notification(
        user_id=contractor_id,
        quote_token=quote_tok,
        notif_type="variation_declined",
        phone=contractor_phone,
        whatsapp_message=(
            f"La propuesta de cambio fue rechazada por el propietario. "
            f"Ver detalles: {app_base_url()}/app/project/{quote_tok}"
        ),
        suppress_wa=suppress_wa,
    )

    return {"ok": True, "message": "Variation declined"}
