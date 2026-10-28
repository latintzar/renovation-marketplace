"""
Payment — Stripe Checkout Sessions for homeowner scope payments
===============================================================

Homeowner payment flow using Stripe Checkout (hosted page).
No Stripe JS on the frontend — just a redirect URL.

ESCROW MODEL:
  - Homeowner pays the full amount into Leo's platform Stripe account.
  - Funds are NOT immediately transferred to the contractor.
  - Leo releases funds to the contractor's Express account per milestone,
    via stripe.Transfer() when each milestone is marked complete.
  - Materials upfront is released first (before work starts).

AMOUNT CALCULATION (mirrors ScopeCanvas.tsx exactly):
  milestones_subtotal = sum(line_items[].amount)
  materials_upfront   = scope_data.materials_upfront (if any)
  work_total          = milestones_subtotal + materials_upfront
  leo_fee             = milestones_subtotal × service_fee_percent%
  iva                 = work_total × iva_rate% (if iva_rate is set)
  homeowner_pays      = work_total + leo_fee + iva

  NOTE: amount_total_cents is computed at finalize time and stored on the scopes row.
  We read it from there — no re-derivation here.

Endpoints:
  POST /api/payment/create-checkout  — Create a Stripe Checkout session for a scope
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import sb_url, sb_headers
from payments import (
    SandboxContext,
    StripeNotConfigured,
    get_stripe_client,
    resolve_sandbox,
)
from payments.finance import compute_quote_financials
from core import http_client
from core import api_error

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateCheckoutRequest(BaseModel):
    quote_token: str
    homeowner_email: Optional[str] = None
    consent_id: Optional[str] = None


@router.post("/payment/create-checkout")
async def api_create_checkout(
    req: CreateCheckoutRequest,
    ctx: SandboxContext = Depends(resolve_sandbox),
):
    """Create a Stripe Checkout Session for a scope payment.

    Input: { quote_token, homeowner_email }
    Header: X-Sandbox: true → use test Stripe keys and skip KYC check.
    Returns: { ok: true, checkout_url: "https://checkout.stripe.com/..." }

    The frontend redirects to checkout_url. Stripe handles everything:
    card, Apple Pay, Google Pay, Klarna, Link, promo codes, 3DS, PCI compliance.

    On success: Stripe → /app/canvas/:token?paid=true
    On cancel:  Stripe → /app/canvas/:token
    """
    sandbox = ctx.is_sandbox
    try:
        stripe_client = get_stripe_client(ctx)
    except StripeNotConfigured:
        raise api_error(500, "Stripe not configured")

    # 1. Load scope from Supabase
    async with http_client(timeout=15) as client:
        quote_resp = await client.get(
            f"{sb_url()}/quotes",
            params={"token": f"eq.{req.quote_token}", "select": "*", "limit": "1"},
            headers=sb_headers(),
        )
    if quote_resp.status_code != 200 or not quote_resp.json():
        raise api_error(404, "Quote not found")

    quote_row = quote_resp.json()[0]
    quote_data = quote_row.get("quote_data") or {}
    contractor_id = quote_row.get("contractor_id", "")

    # Idempotency guard: never create a second checkout if already paid or pending
    existing_status = quote_row.get("payment_status", "unpaid")
    if existing_status == "paid":
        raise api_error(409, "Scope is already paid")
    existing_session_id = quote_row.get("checkout_session_id", "")
    if existing_status == "pending" and existing_session_id:
        # Re-use the existing session instead of creating a new one
        try:
            existing_session = stripe_client.checkout.sessions.retrieve(existing_session_id)
            if existing_session.status == "open":
                logger.info("Reusing existing checkout session | quote=%s session=%s", req.quote_token[:8], existing_session_id[:16])
                return {"ok": True, "checkout_url": existing_session.url}
        except stripe.error.StripeError:
            pass  # Session expired or invalid — fall through to create a new one

    # 2. Load contractor to get stripe_account_id
    async with http_client(timeout=15) as client:
        contractor_resp = await client.get(
            f"{sb_url()}/contractors",
            params={
                "id": f"eq.{contractor_id}",
                "select": "stripe_account_id,stripe_onboarding_complete",
                "limit": "1",
            },
            headers=sb_headers(),
        )
    if contractor_resp.status_code != 200 or not contractor_resp.json():
        raise api_error(404, "Contractor not found")

    contractor = contractor_resp.json()[0]
    stripe_account_id = contractor.get("stripe_account_id", "")
    onboarding_complete = contractor.get("stripe_onboarding_complete", False)

    if not sandbox and not stripe_account_id:
        raise HTTPException(
            status_code=400,
            detail="Contractor has not connected their bank account",
        )
    if not sandbox and not onboarding_complete:
        raise HTTPException(
            status_code=400,
            detail="Contractor KYC not complete — cannot accept payments yet",
        )
    if sandbox:
        logger.info(
            "Sandbox checkout: KYC/bank checks skipped | quote=%s contractor=%s",
            req.quote_token[:8], contractor_id[:12],
        )

    # 3. Get pre-computed total from the scopes row (set at finalize time).
    #    Falls back to re-computing from scope_data if missing (legacy scopes).
    amount_total_cents = quote_row.get("amount_total_cents")
    leo_fee_cents = quote_row.get("stripe_fee_cents")

    if not amount_total_cents:
        fin = compute_quote_financials(quote_data)
        amount_total_cents = fin.amount_total_cents
        leo_fee_cents = fin.fee_cents
        logger.warning(
            "Scope missing pre-computed totals — re-derived from scope_data | quote=%s total_eur=%.2f",
            req.quote_token[:8], amount_total_cents / 100,
        )

    if not amount_total_cents or amount_total_cents <= 0:
        raise api_error(400, "Scope has no payable amount")

    scope_title = quote_data.get("title") or "Leo Scope"
    line_items = quote_data.get("line_items") or []
    num_phases = len(line_items)
    app_base_url = os.getenv("APP_BASE_URL", "http://127.0.0.1:18260")

    # 4. Create Stripe Checkout Session.
    #
    # ESCROW: funds land in Leo's platform account. We do NOT use transfer_data.destination
    # here — that would give money to the contractor immediately, bypassing escrow.
    # Per-milestone releases are done later via stripe.Transfer() when each phase completes.
    # The contractor's stripe_account_id is stored so we can route transfers per milestone.
    try:
        session = stripe_client.checkout.sessions.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "unit_amount": int(amount_total_cents),
                    "product_data": {
                        "name": scope_title,
                        "description": (
                            f"{num_phases} fase{'s' if num_phases != 1 else ''} · "
                            f"Pagos protegidos por custodia Leo"
                        ),
                    },
                },
                "quantity": 1,
            }],
            payment_intent_data={
                # Funds held by Leo. Transfer to contractor happens per milestone.
                "metadata": {
                    "quote_token": req.quote_token,
                    "contractor_id": contractor_id,
                    "contractor_stripe_account": stripe_account_id,
                    "leo_fee_cents": str(leo_fee_cents or 0),
                },
            },
            allow_promotion_codes=False,  # Scope payments are exact — no promo codes
            customer_email=req.homeowner_email or None,
            success_url=f"{app_base_url}/app/canvas/{req.quote_token}?paid=true",
            cancel_url=f"{app_base_url}/app/canvas/{req.quote_token}",
            locale="es",  # Our primary market is Spain
            metadata={"quote_token": req.quote_token},
        )
    except stripe.error.StripeError as e:
        logger.error("Stripe checkout session creation failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Payment setup failed: {getattr(e, 'user_message', None) or str(e)}",
        )

    # 5. Record checkout session; don't overwrite amount_total_cents (already set at finalize)
    quote_patch: dict = {
        "checkout_session_id": session.id,
        "homeowner_email": req.homeowner_email or None,
        "payment_status": "pending",
    }
    if req.consent_id:
        quote_patch["consent_id"] = req.consent_id
    if sandbox:
        quote_patch["is_sandbox"] = True

    async with http_client(timeout=15) as client:
        await client.patch(
            f"{sb_url()}/quotes",
            params={"token": f"eq.{req.quote_token}"},
            json=quote_patch,
            headers=sb_headers(),
        )

    logger.info(
        "Checkout session created | quote=%s contractor=%s total_eur=%.2f phases=%d",
        req.quote_token[:8], contractor_id[:12],
        amount_total_cents / 100, num_phases,
    )
    return {"ok": True, "checkout_url": session.url}
