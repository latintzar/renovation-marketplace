"""
Stripe Connect — Contractor onboarding and account management
=============================================================

Manages Stripe Express accounts for contractors so they can receive
payments (escrow releases) through the Leo platform.

Flow:
  1. POST /api/stripe/create-account  — create Express account, save stripe_account_id
  2. POST /api/stripe/account-link    — generate onboarding URL (redirect to Stripe)
  3. GET  /api/stripe/account-status  — check if onboarding is complete
  4. POST /api/stripe/webhook         — handle account.updated events

For security, all contractor identity (KYC) is collected by Stripe's
hosted onboarding form — we never touch DNI, IBAN, or other sensitive data.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from core import sb_url, sb_headers
from payments import (
    SandboxContext,
    StripeNotConfigured,
    build_stripe_client_from_key,
    get_stripe_client,
    resolve_sandbox,
)
from core import http_client
from core import api_error

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_stripe_key() -> str:
    try:
        from config import settings
        return getattr(settings, "STRIPE_SECRET_KEY", "") or os.getenv("STRIPE_SECRET_KEY", "")
    except Exception:
        return os.getenv("STRIPE_SECRET_KEY", "")


def _get_webhook_secret() -> str:
    try:
        from config import settings
        return getattr(settings, "STRIPE_WEBHOOK_SECRET", "") or os.getenv("STRIPE_WEBHOOK_SECRET", "")
    except Exception:
        return os.getenv("STRIPE_WEBHOOK_SECRET", "")


def _get_webhook_secret_test() -> str:
    try:
        from config import settings
        return getattr(settings, "STRIPE_WEBHOOK_SECRET_TEST", "") or os.getenv("STRIPE_WEBHOOK_SECRET_TEST", "")
    except Exception:
        return os.getenv("STRIPE_WEBHOOK_SECRET_TEST", "")




async def _get_contractor(contractor_id: str) -> Optional[Dict[str, Any]]:
    if not sb_url:
        return None
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/contractors",
            params={"id": f"eq.{contractor_id}", "select": "*", "limit": "1"},
            headers=sb_headers(),
        )
        if resp.status_code == 200:
            rows = resp.json()
            return rows[0] if rows else None
    return None


async def _patch_contractor(contractor_id: str, updates: dict) -> None:
    if not sb_url:
        return
    async with http_client(timeout=10) as client:
        await client.patch(
            f"{sb_url()}/contractors",
            params={"id": f"eq.{contractor_id}"},
            json=updates,
            headers=sb_headers(),
        )


# ── POST /api/stripe/create-account ──────────────────────────────────

class CreateAccountRequest(BaseModel):
    contractor_id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@router.post("/stripe/create-account")
async def api_create_stripe_account(
    req: CreateAccountRequest,
    ctx: SandboxContext = Depends(resolve_sandbox),
):
    """Create a Stripe Connect Express account for a contractor.

    Prefills whatever we know from the profile to reduce onboarding friction.
    Saves the stripe_account_id to the contractors table.

    Sandbox mode (X-Sandbox: true):
    - Uses test Stripe key
    - Immediately marks stripe_onboarding_complete = true (KYC bypassed)
    - No Stripe account link generation required
    """
    sandbox = ctx.is_sandbox
    try:
        stripe_client = get_stripe_client(ctx)
    except StripeNotConfigured:
        raise api_error(500, "Stripe not configured")

    contractor = await _get_contractor(req.contractor_id)
    if not contractor:
        raise api_error(404, "Contractor not found")

    existing_stripe_id = contractor.get("stripe_account_id", "")
    if existing_stripe_id:
        logger.info("Returning existing Stripe account | contractor=%s acct=%s", req.contractor_id[:12], existing_stripe_id[:12])
        return {"ok": True, "stripe_account_id": existing_stripe_id, "existing": True}

    # Build prefill from profile canvas
    canvas = contractor.get("canvas") or {}
    business_name = canvas.get("business_name", "")
    email = req.email or contractor.get("phone", "")  # fallback — Stripe accepts email

    # Parse name from profile if not provided
    first_name = req.first_name
    last_name = req.last_name
    if not first_name and business_name:
        parts = business_name.split()
        first_name = parts[0] if parts else ""
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    account_params: Dict[str, Any] = {
        "type": "express",
        "country": "ES",
        "business_type": "individual",
        "capabilities": {
            "transfers": {"requested": True},
        },
        "settings": {
            "payouts": {
                "schedule": {"interval": "manual"},  # Leo controls when funds are released
            }
        },
    }

    # Prefill with known data (reduces what Stripe asks)
    individual: Dict[str, Any] = {}
    if first_name:
        individual["first_name"] = first_name
    if last_name:
        individual["last_name"] = last_name
    if email and "@" in email:
        account_params["email"] = email
        individual["email"] = email
    if individual:
        account_params["individual"] = individual

    try:
        account = stripe_client.accounts.create(**account_params)
        stripe_account_id = account.id
        logger.info("Stripe Express account created | contractor=%s acct=%s", req.contractor_id[:12], stripe_account_id[:12])
    except stripe.StripeError as e:
        logger.error("Stripe account creation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    # Persist to Supabase
    patch_data: Dict[str, Any] = {"stripe_account_id": stripe_account_id}

    # Sandbox KYC bypass — immediately mark onboarding complete
    if sandbox:
        patch_data["stripe_onboarding_complete"] = True
        logger.info("Sandbox KYC bypassed | contractor=%s acct=%s", req.contractor_id[:12], stripe_account_id[:12])

    await _patch_contractor(req.contractor_id, patch_data)

    return {"ok": True, "stripe_account_id": stripe_account_id, "existing": False, "kyc_bypassed": sandbox}


# ── POST /api/stripe/account-link ────────────────────────────────────

class AccountLinkRequest(BaseModel):
    contractor_id: str
    return_url: Optional[str] = None
    refresh_url: Optional[str] = None


@router.post("/stripe/account-link")
async def api_create_account_link(req: AccountLinkRequest):
    """Generate a Stripe Connect onboarding URL for a contractor.

    The contractor is redirected to Stripe's hosted form (in Spanish),
    which collects DNI, NIF, IBAN, and other required details.
    After completing, they land back on return_url.
    """
    try:
        stripe_client = build_stripe_client_from_key(_get_stripe_key())
    except StripeNotConfigured:
        raise api_error(500, "Stripe not configured")

    contractor = await _get_contractor(req.contractor_id)
    if not contractor:
        raise api_error(404, "Contractor not found")

    stripe_account_id = contractor.get("stripe_account_id", "")
    if not stripe_account_id:
        raise api_error(400, "No Stripe account found — create one first")

    # Determine base URL for return/refresh
    base_url = os.getenv("APP_BASE_URL", "http://127.0.0.1:18260")
    return_url = req.return_url or f"{base_url}/app/stripe/complete?contractor={req.contractor_id}"
    refresh_url = req.refresh_url or f"{base_url}/app/stripe/refresh?contractor={req.contractor_id}"

    try:
        account_link = stripe_client.account_links.create(
            account=stripe_account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
            collection_options={
                "fields": "eventually_due",  # Collect everything upfront to avoid future interruptions
            },
        )
        logger.info("Stripe account link generated | contractor=%s acct=%s", req.contractor_id[:12], stripe_account_id[:12])
    except stripe.StripeError as e:
        logger.error("Stripe account link creation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    return {"ok": True, "url": account_link.url, "expires_at": account_link.expires_at}


# ── GET /api/stripe/account-status ───────────────────────────────────

@router.get("/stripe/account-status")
async def api_get_account_status(contractor_id: str):
    """Check the Stripe Connect onboarding status for a contractor.

    Returns charges_enabled, payouts_enabled, and details_submitted.
    Also updates stripe_onboarding_complete in Supabase when fully verified.
    """
    try:
        stripe_client = build_stripe_client_from_key(_get_stripe_key())
    except StripeNotConfigured:
        raise api_error(500, "Stripe not configured")

    contractor = await _get_contractor(contractor_id)
    if not contractor:
        raise api_error(404, "Contractor not found")

    stripe_account_id = contractor.get("stripe_account_id", "")
    if not stripe_account_id:
        return {
            "ok": True,
            "has_account": False,
            "charges_enabled": False,
            "payouts_enabled": False,
            "details_submitted": False,
            "onboarding_complete": False,
        }

    try:
        account = stripe_client.accounts.retrieve(stripe_account_id)
    except stripe.StripeError as e:
        logger.error("Stripe account retrieve failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    charges_enabled = bool(account.charges_enabled)
    payouts_enabled = bool(account.payouts_enabled)
    details_submitted = bool(account.details_submitted)
    onboarding_complete = charges_enabled and payouts_enabled

    # Update Supabase if newly complete
    if onboarding_complete and not contractor.get("stripe_onboarding_complete"):
        await _patch_contractor(contractor_id, {"stripe_onboarding_complete": True})
        logger.info("Stripe onboarding complete | contractor=%s", contractor_id[:12])

    return {
        "ok": True,
        "has_account": True,
        "stripe_account_id": stripe_account_id,
        "charges_enabled": charges_enabled,
        "payouts_enabled": payouts_enabled,
        "details_submitted": details_submitted,
        "onboarding_complete": onboarding_complete,
        "requirements": {
            "currently_due": list(account.requirements.currently_due or []),
            "eventually_due": list(account.requirements.eventually_due or []),
            "pending_verification": list(account.requirements.pending_verification or []),
        },
    }


# ── POST /api/stripe/webhook ──────────────────────────────────────────

@router.post("/stripe/webhook")
async def api_stripe_webhook(request: Request):
    """Handle Stripe Connect webhook events (live + test/sandbox mode).

    Key events:
      - account.updated: contractor's verification status changed
      - checkout.session.completed: homeowner paid

    Verification strategy:
      1. Try live webhook secret. If it passes → live event.
      2. If it fails, try test webhook secret. If it passes → sandbox event.
      3. If both fail → reject with 400.
    """
    live_secret = _get_webhook_secret()
    test_secret = _get_webhook_secret_test()

    live_api_key = _get_stripe_key()
    if not live_api_key:
        raise api_error(500, "Stripe not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not sig_header:
        logger.warning("Stripe webhook received without stripe-signature header — rejecting")
        raise api_error(400, "Missing stripe-signature header")

    event = None
    is_sandbox_event = False

    if live_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, live_secret)
        except stripe.SignatureVerificationError:
            pass
        except ValueError as e:
            logger.warning("Stripe webhook payload parse error: %s", e)
            raise api_error(400, "Invalid webhook payload")

    if event is None and test_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, test_secret)
            is_sandbox_event = True
            logger.info("Stripe webhook verified with TEST secret (sandbox event)")
        except stripe.SignatureVerificationError:
            pass
        except ValueError as e:
            logger.warning("Stripe webhook payload parse error (test): %s", e)
            raise api_error(400, "Invalid webhook payload")

    if event is None:
        if not live_secret and not test_secret:
            logger.error("No STRIPE_WEBHOOK_SECRET configured — rejecting all webhook calls")
            raise api_error(500, "Webhook secret not configured")
        logger.warning("Stripe webhook signature verification failed (live + test)")
        raise api_error(400, "Invalid webhook signature")

    event_type = event.type
    logger.info("Stripe webhook received | type=%s sandbox=%s", event_type, is_sandbox_event)

    if event_type == "account.updated":
        account = event.data.object
        stripe_account_id = account.id
        charges_enabled = bool(account.charges_enabled)
        payouts_enabled = bool(account.payouts_enabled)
        onboarding_complete = charges_enabled and payouts_enabled

        if onboarding_complete:
            # Find contractor by stripe_account_id and mark as complete
            if True:
                async with http_client(timeout=10) as client:
                    resp = await client.get(
                        f"{sb_url()}/contractors",
                        params={"stripe_account_id": f"eq.{stripe_account_id}", "select": "id", "limit": "1"},
                        headers=sb_headers(),
                    )
                    if resp.status_code == 200:
                        rows = resp.json()
                        if rows:
                            contractor_id = rows[0]["id"]
                            await _patch_contractor(
                                contractor_id,
                                {"stripe_onboarding_complete": True},
                            )
                            logger.info(
                                "Stripe onboarding complete via webhook | contractor=%s acct=%s",
                                contractor_id[:12], stripe_account_id[:12],
                            )

    elif event_type == "checkout.session.completed":
        session = event.data.object
        quote_token = (session.metadata or {}).get("quote_token", "")
        payment_intent_id = session.payment_intent or ""
        homeowner_email = (session.customer_details or {}).get("email", "")
        amount_total = session.amount_total  # in cents (homeowner-paid amount)

        if quote_token:
            if True:
                # Use homeowner email as auth_id for notification routing when no Supabase user yet
                homeowner_auth_id = homeowner_email or None

                async with http_client(timeout=10) as client:
                    resp = await client.patch(
                        f"{sb_url()}/quotes",
                        params={"token": f"eq.{quote_token}"},
                        json={
                            "payment_status": "paid",
                            "status": "paid",
                            "payment_intent_id": payment_intent_id,
                            "homeowner_email": homeowner_email or None,
                            "homeowner_auth_id": homeowner_auth_id,
                            "amount_total_cents": amount_total,
                        },
                        headers={**sb_headers(), "Prefer": "return=minimal"},
                    )
                    if resp.status_code in (200, 201, 204):
                        logger.info(
                            "Quote marked paid via webhook | quote=%s intent=%s amount=%s homeowner=%s",
                            quote_token[:8], str(payment_intent_id)[:16], amount_total,
                            (homeowner_email or "")[:20],
                        )
                    else:
                        logger.error(
                            "Quote payment status update failed | quote=%s status=%d body=%s",
                            quote_token[:8], resp.status_code, resp.text[:200],
                        )

                # Update the consent record with payment_intent_id if one exists
                if payment_intent_id:
                    async with http_client(timeout=10) as client:
                        await client.patch(
                            f"{sb_url()}/consents",
                            params={"quote_token": f"eq.{quote_token}"},
                            json={"payment_intent_id": payment_intent_id},
                            headers={**sb_headers(), "Prefer": "return=minimal"},
                        )
        else:
            logger.warning("checkout.session.completed missing quote_token in metadata | session=%s", session.id)

    elif event_type == "payment_intent.payment_failed":
        intent = event.data.object
        quote_token = (intent.metadata or {}).get("quote_token", "")
        if quote_token:
            if True:
                async with http_client(timeout=10) as client:
                    await client.patch(
                        f"{sb_url()}/quotes",
                        params={"token": f"eq.{quote_token}"},
                        json={"payment_status": "failed"},
                        headers={**sb_headers(), "Prefer": "return=minimal"},
                    )
            logger.info("Quote payment failed | quote=%s", quote_token[:8])

    return {"ok": True, "received": event_type}
