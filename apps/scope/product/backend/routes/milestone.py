"""
Milestone — Escrow Engine for Leo Scope
========================================

Handles the full post-payment lifecycle:
  - Contractor submits proof for a milestone
  - Homeowner approves → stripe.Transfer releases funds from escrow
  - Variation orders (change orders) — create, approve, decline
  - Job cancellation + full refund
  - Reviews after job complete
  - Notification read/unread state

All money movement uses idempotency keys to prevent double-release.

State machine:
  Scope:      draft → sent → paid → in_progress → awaiting_final_approval → complete | cancelled | disputed
  Milestone:  pending → in_progress → proof_submitted → approved → released | disputed

Endpoints:
  POST /api/milestone/submit-proof
  POST /api/payment/release-milestone
  POST /api/variation/create
  POST /api/variation/approve
  POST /api/variation/decline
  POST /api/job/cancel
  POST /api/reviews/create
  GET  /api/notifications
  POST /api/notifications/mark-read
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_quote(quote_token: str) -> dict:
    async with http_client(timeout=15) as client:
        resp = await client.get(
            f"{sb_url()}/quotes",
            params={"token": f"eq.{quote_token}", "select": "*", "limit": "1"},
            headers=sb_headers(),
        )
    if resp.status_code != 200 or not resp.json():
        raise api_error(404, "Quote not found")
    return resp.json()[0]


async def _get_contractor(contractor_id: str) -> dict:
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/contractors",
            params={"id": f"eq.{contractor_id}", "select": "*", "limit": "1"},
            headers=sb_headers(),
        )
    if resp.status_code != 200 or not resp.json():
        raise api_error(404, "Contractor not found")
    return resp.json()[0]


async def _patch_quote(quote_token: str, data: dict) -> None:
    async with http_client(timeout=15) as client:
        await client.patch(
            f"{sb_url()}/quotes",
            params={"token": f"eq.{quote_token}"},
            json=data,
            headers=sb_headers(),
        )


async def _insert_notification(user_id: str, quote_token: str, notif_type: str, milestone_index: Optional[int] = None) -> None:
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
        logger.warning("Failed to insert notification type=%s user=%s: %s", notif_type, user_id, resp.text)


async def _send_whatsapp(phone: str, message: str, suppress: bool = False) -> None:
    """Send WhatsApp message via the unified send_wa stack.

    Args:
        suppress: When True the message is logged but NOT sent. Controlled by
                  ctx.suppress_whatsapp which respects X-Allow-WhatsApp header,
                  so sandbox tests CAN send real WhatsApp when explicitly opted in.
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
        send_wa_message_sync(phone, message, purpose="milestone", do_store=False, skip_window_check=True)
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
    """Insert in-app notification and optionally send WhatsApp.

    In-app notification is always inserted. WhatsApp is suppressed when
    suppress_wa=True (sandbox without X-Allow-WhatsApp).
    """
    await _insert_notification(user_id, quote_token, notif_type, milestone_index)
    if phone and whatsapp_message:
        await _send_whatsapp(phone, whatsapp_message, suppress=suppress_wa)


def _app_base_url() -> str:
    return os.getenv("APP_BASE_URL", "http://127.0.0.1:18260")


def _tracking_url(quote_token: str, homeowner_email: str = "") -> str:
    """Build tracking page URL with optional email pre-fill for faster homeowner login."""
    base = f"{_app_base_url()}/app/project/{quote_token}"
    if homeowner_email:
        from urllib.parse import quote as urlquote
        base += f"?email={urlquote(homeowner_email)}"
    return base


# ---------------------------------------------------------------------------
# Section 1: Milestone proof submission
# ---------------------------------------------------------------------------

class SubmitProofRequest(BaseModel):
    quote_token: str
    milestone_index: int
    photos: List[str] = []
    voice_url: Optional[str] = None
    note: Optional[str] = None
    contractor_auth_id: str


@router.post("/milestone/submit-proof")
async def submit_proof(req: SubmitProofRequest, ctx: SandboxContext = Depends(resolve_sandbox)):
    """Contractor submits proof photos + note for a milestone.

    - Inserts milestone_updates row (status=proof_submitted)
    - Patches quotes.milestones[index].status = proof_submitted
    - Notifies homeowner via in-app + WhatsApp (suppressed in sandbox)
    """
    sandbox = ctx.is_sandbox
    suppress_wa = ctx.suppress_whatsapp
    quote = await _get_quote(req.quote_token)

    if quote.get("payment_status") != "paid":
        raise api_error(400, "Scope is not paid — cannot submit proof")

    if quote.get("contractor_id") != req.contractor_auth_id:
        raise api_error(403, "Not the quote contractor")


    milestones = quote.get("milestones") or []
    if req.milestone_index < 0 or req.milestone_index >= len(milestones):
        raise api_error(400, "Invalid milestone index")

    # Insert milestone_updates row (table uses scope_token column)
    async with http_client(timeout=15) as client:
        ins_resp = await client.post(
            f"{sb_url()}/milestone_updates",
            json={
                "scope_token": req.quote_token,
                "milestone_index": req.milestone_index,
                "photos": req.photos,
                "voice_url": req.voice_url,
                "note": req.note,
                "status": "proof_submitted",
            },
            headers=sb_headers(),
        )
    if ins_resp.status_code not in (200, 201):
        logger.error("Failed to insert milestone_update: %s", ins_resp.text)
        raise api_error(500, "Failed to record proof")

    # Patch milestone status in quotes.milestones JSON
    milestones = quote.get("milestones") or []
    if isinstance(milestones, list) and req.milestone_index < len(milestones):
        milestones[req.milestone_index]["status"] = "proof_submitted"
        await _patch_quote(req.quote_token, {"milestones": milestones, "payment_status": "paid"})

    # Update scope status to in_progress if first proof
    if quote.get("status") in ("paid", None):
        await _patch_quote(req.quote_token, {"status": "in_progress"})

    # Notify homeowner
    homeowner_id = quote.get("homeowner_auth_id") or quote.get("homeowner_email") or ""
    homeowner_phone = quote.get("homeowner_phone") or ""
    ho_email = quote.get("homeowner_email") or ""
    contractor = await _get_contractor(quote["contractor_id"])
    contractor_name = contractor.get("name", "Tu contratista")
    project_url = _tracking_url(req.quote_token, ho_email)

    milestone_label = f"fase {req.milestone_index + 1}"
    milestones_list = quote.get("milestones") or []
    if req.milestone_index < len(milestones_list):
        milestone_label = milestones_list[req.milestone_index].get("title", milestone_label)

    if homeowner_id:
        await send_notification(
            user_id=homeowner_id,
            quote_token=req.quote_token,
            notif_type="proof_submitted",
            milestone_index=req.milestone_index,
            phone=homeowner_phone,
            whatsapp_message=(
                f"{contractor_name} ha enviado fotos de la {milestone_label}. "
                f"Revísalas y aprueba el pago. {project_url}"
            ),
            suppress_wa=suppress_wa,
        )

    logger.info(
        "Proof submitted | quote=%s milestone=%d photos=%d sandbox=%s",
        req.quote_token[:8], req.milestone_index, len(req.photos), sandbox,
    )
    return {"ok": True, "message": "Proof submitted — homeowner notified"}


# ---------------------------------------------------------------------------
# Section 2: Milestone release (escrow → contractor)
# ---------------------------------------------------------------------------

class ReleaseMilestoneRequest(BaseModel):
    quote_token: str
    milestone_index: int
    homeowner_auth_id: str


@router.post("/payment/release-milestone")
async def release_milestone(req: ReleaseMilestoneRequest, ctx: SandboxContext = Depends(resolve_sandbox)):
    """Homeowner approves a milestone and releases funds from escrow."""
    quote = await _get_quote(req.quote_token)

    # Identity check: caller must be the project's homeowner
    quote_ho = quote.get("homeowner_auth_id") or ""
    if not quote_ho or req.homeowner_auth_id != quote_ho:
        raise api_error(403, "Only the project homeowner can release milestones")

    if quote.get("payment_status") != "paid":
        raise api_error(400, "Scope is not paid")

    milestones = quote.get("milestones") or []
    if req.milestone_index >= len(milestones):
        raise api_error(400, "Invalid milestone index")

    milestone = milestones[req.milestone_index]
    if milestone.get("status") == "released":
        raise api_error(409, "Milestone already released")

    contractor = await _get_contractor(quote["contractor_id"])
    stripe_account_id = contractor.get("stripe_account_id", "")
    if not stripe_account_id:
        raise api_error(400, "Contractor has no Stripe account")

    # Amount for this milestone (in cents)
    amount_cents = milestone.get("amount_cents", 0)
    if not amount_cents:
        # Derive from amount field (EUR string or float) if amount_cents not stored
        raw_amount = milestone.get("amount", 0)
        try:
            amount_cents = int(float(str(raw_amount).replace("€", "").strip()) * 100)
        except (ValueError, TypeError):
            amount_cents = 0

    if amount_cents <= 0:
        raise api_error(400, "Milestone has no payable amount")

    # If the quote is a sandbox quote, always use test keys (even without X-Sandbox header).
    # This prevents live-key errors when homeowners open sandbox links in a normal browser.
    quote_is_sandbox = quote.get("is_sandbox", False)
    sandbox = ctx.is_sandbox or quote_is_sandbox
    suppress_wa = ctx.suppress_whatsapp
    try:
        if quote_is_sandbox and not ctx.is_sandbox:
            from config import settings as _settings
            sandbox_key = getattr(_settings, "STRIPE_SECRET_KEY_TEST", "") or os.getenv("STRIPE_SECRET_KEY_TEST", "")
            stripe_client = build_stripe_client_from_key(sandbox_key)
            logger.info("Quote is sandbox — overriding to test Stripe key | quote=%s", req.quote_token[:8])
        else:
            stripe_client = get_stripe_client(ctx)
    except StripeNotConfigured:
        raise api_error(500, "Stripe not configured")

    idempotency_key = f"{req.quote_token}-milestone-{req.milestone_index}"
    try:
        transfer = stripe_client.transfers.create(
            amount=amount_cents,
            currency="eur",
            destination=stripe_account_id,
            idempotency_key=idempotency_key,
            metadata={
                "quote_token": req.quote_token,
                "milestone_index": req.milestone_index,
                "milestone_title": milestone.get("title", ""),
            },
        )
        transfer_id = transfer.id
        logger.info(
            "Transfer created | quote=%s milestone=%d amount_eur=%.2f transfer=%s sandbox=%s",
            req.quote_token[:8], req.milestone_index, amount_cents / 100, transfer_id[:16], sandbox,
        )
    except stripe.error.IdempotencyError:
        logger.info("Idempotency hit — milestone already released | quote=%s milestone=%d", req.quote_token[:8], req.milestone_index)
        transfer_id = "idempotent-duplicate"
    except stripe.error.StripeError as e:
        logger.error("Transfer failed | quote=%s: %s", req.quote_token[:8], e)
        raise HTTPException(status_code=500, detail=f"Transfer failed: {getattr(e, 'user_message', None) or str(e)}")


    # Patch milestone_updates row (table uses scope_token column)
    import datetime
    now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    async with http_client(timeout=15) as client:
        await client.patch(
            f"{sb_url()}/milestone_updates",
            params={"scope_token": f"eq.{req.quote_token}", "milestone_index": f"eq.{req.milestone_index}"},
            json={"status": "released", "released_at": now_iso, "stripe_transfer_id": transfer_id},
            headers=sb_headers(),
        )

    # Patch quotes.milestones JSON
    milestones[req.milestone_index]["status"] = "released"
    all_released = all(m.get("status") == "released" for m in milestones)
    quote_patch: dict = {"milestones": milestones}
    if all_released:
        quote_patch["status"] = "complete"
        quote_patch["completed_at"] = now_iso

    await _patch_quote(req.quote_token, quote_patch)

    # Notifications
    contractor_name = contractor.get("name", "Tu contratista")
    contractor_phone = contractor.get("phone", "")
    contractor_user_id = contractor.get("id") or quote["contractor_id"]
    homeowner_id = quote.get("homeowner_auth_id") or quote.get("homeowner_email") or ""
    ho_email = quote.get("homeowner_email") or ""
    project_url = _tracking_url(req.quote_token, ho_email)
    milestone_title = milestone.get("title", f"Fase {req.milestone_index + 1}")
    amount_eur = f"€{amount_cents / 100:.0f}"

    await send_notification(
        user_id=contractor_user_id,
        quote_token=req.quote_token,
        notif_type="milestone_released",
        milestone_index=req.milestone_index,
        phone=contractor_phone,
        whatsapp_message=(
            f"{amount_eur} liberado · {milestone_title} aprobado. "
            f"Ver en app: {project_url}"
        ),
        suppress_wa=suppress_wa,
    )

    if homeowner_id:
        await send_notification(
            user_id=homeowner_id,
            quote_token=req.quote_token,
            notif_type="payment_released",
            milestone_index=req.milestone_index,
            suppress_wa=suppress_wa,
        )

    if all_released:
        # Final completion notifications
        if contractor_phone:
            await _send_whatsapp(
                contractor_phone,
                f"¡Trabajo completado! Todos los pagos han sido transferidos. {project_url}",
                suppress=suppress_wa,
            )
        homeowner_phone = quote.get("homeowner_phone", "")
        if homeowner_phone:
            await _send_whatsapp(
                homeowner_phone,
                f"Tu proyecto está completo. Factura disponible en: {project_url}",
                suppress=suppress_wa,
            )

    return {
        "ok": True,
        "transfer_id": transfer_id,
        "all_released": all_released,
        "message": f"Released {amount_eur} to {contractor_name}",
    }


# ---------------------------------------------------------------------------
# Section 3: Variation orders
# ---------------------------------------------------------------------------

class CreateVariationRequest(BaseModel):
    quote_token: str
    title: str
    description: Optional[str] = None
    photos: List[str] = []
    amount_cents: int
    reason: Optional[str] = None
    contractor_auth_id: str


@router.post("/variation/create")
async def create_variation(req: CreateVariationRequest, ctx: SandboxContext = Depends(resolve_sandbox)):
    """Contractor proposes a change order / variation."""
    sandbox = ctx.is_sandbox
    suppress_wa = ctx.suppress_whatsapp
    quote = await _get_quote(req.quote_token)

    if quote.get("contractor_id") != req.contractor_auth_id:
        raise api_error(403, "Not the quote contractor")

    async with http_client(timeout=15) as client:
        ins_resp = await client.post(
            f"{sb_url()}/variation_orders",
            json={
                "scope_token": req.quote_token,
                "title": req.title,
                "description": req.description,
                "photos": req.photos,
                "amount_cents": req.amount_cents,
                "reason": req.reason,
                "status": "pending",
            },
            headers=sb_headers(),
        )
    if ins_resp.status_code not in (200, 201):
        raise api_error(500, "Failed to create variation order")

    homeowner_id = quote.get("homeowner_auth_id") or quote.get("homeowner_email") or ""
    homeowner_phone = quote.get("homeowner_phone", "")
    ho_email = quote.get("homeowner_email") or ""
    contractor = await _get_contractor(quote["contractor_id"])
    contractor_name = contractor.get("name", "Tu contratista")
    project_url = _tracking_url(req.quote_token, ho_email)
    amount_eur = f"€{req.amount_cents / 100:.0f}"

    if homeowner_id:
        await send_notification(
            user_id=homeowner_id,
            quote_token=req.quote_token,
            notif_type="variation_created",
            phone=homeowner_phone,
            whatsapp_message=(
                f"{contractor_name} propone un cambio de obra por {amount_eur}: {req.title}. "
                f"Revísalo: {project_url}"
            ),
            suppress_wa=suppress_wa,
        )

    return {"ok": True, "message": "Variation order sent to homeowner"}


class ApproveVariationRequest(BaseModel):
    variation_id: str
    homeowner_email: str


@router.post("/variation/approve")
async def approve_variation(req: ApproveVariationRequest, ctx: SandboxContext = Depends(resolve_sandbox)):
    """Homeowner approves a variation — creates new Stripe Checkout for the extra amount."""
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/variation_orders",
            params={"id": f"eq.{req.variation_id}", "select": "*", "limit": "1"},
            headers=sb_headers(),
        )
    if resp.status_code != 200 or not resp.json():
        raise api_error(404, "Variation not found")

    variation = resp.json()[0]
    if variation.get("status") != "pending":
        raise api_error(409, "Variation already actioned")

    quote_tok = variation.get("scope_token") or variation.get("quote_token", "")
    quote = await _get_quote(quote_tok)

    # Identity check: caller email must match the project's homeowner
    quote_ho_email = quote.get("homeowner_email") or ""
    if not quote_ho_email or req.homeowner_email.lower() != quote_ho_email.lower():
        raise api_error(403, "Only the project homeowner can approve variations")

    contractor = await _get_contractor(quote["contractor_id"])

    sandbox = ctx.is_sandbox
    suppress_wa = ctx.suppress_whatsapp
    try:
        stripe_client = get_stripe_client(ctx)
    except StripeNotConfigured:
        raise api_error(500, "Stripe not configured")

    app_base = _app_base_url()
    session = stripe_client.checkout.sessions.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "eur",
                "unit_amount": variation["amount_cents"],
                "product_data": {
                    "name": f"Cambio de obra: {variation['title']}",
                    "description": variation.get("description") or "",
                },
            },
            "quantity": 1,
        }],
        payment_intent_data={
            "metadata": {
                "variation_id": req.variation_id,
                "quote_token": quote_tok,
                "contractor_stripe_account": contractor.get("stripe_account_id", ""),
            }
        },
        customer_email=req.homeowner_email,
        success_url=f"{app_base}/app/project/{quote_tok}?variation_paid=true",
        cancel_url=f"{app_base}/app/project/{quote_tok}",
        locale="es",
        metadata={"variation_id": req.variation_id, "quote_token": quote_tok},
    )

    # Mark variation as approved + store session
    async with http_client(timeout=10) as client:
        await client.patch(
            f"{sb_url()}/variation_orders",
            params={"id": f"eq.{req.variation_id}"},
            json={"status": "approved", "checkout_session_id": session.id},
            headers=sb_headers(),
        )

    return {"ok": True, "checkout_url": session.url}


class DeclineVariationRequest(BaseModel):
    variation_id: str
    homeowner_auth_id: str


@router.post("/variation/decline")
async def decline_variation(req: DeclineVariationRequest, ctx: SandboxContext = Depends(resolve_sandbox)):
    """Homeowner declines a variation."""
    sandbox = ctx.is_sandbox
    suppress_wa = ctx.suppress_whatsapp
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/variation_orders",
            params={"id": f"eq.{req.variation_id}", "select": "scope_token,status", "limit": "1"},
            headers=sb_headers(),
        )
    if resp.status_code != 200 or not resp.json():
        raise api_error(404, "Variation not found")

    variation = resp.json()[0]
    if variation.get("status") != "pending":
        raise api_error(409, "Variation already actioned")

    quote_tok = variation.get("scope_token") or variation.get("quote_token", "")
    quote = await _get_quote(quote_tok)

    # Identity check
    quote_ho = quote.get("homeowner_auth_id") or ""
    if not quote_ho or req.homeowner_auth_id != quote_ho:
        raise api_error(403, "Only the project homeowner can decline variations")

    async with http_client(timeout=10) as client:
        await client.patch(
            f"{sb_url()}/variation_orders",
            params={"id": f"eq.{req.variation_id}"},
            json={"status": "declined"},
            headers=sb_headers(),
        )

    contractor_id = quote.get("contractor_id", "")
    contractor = await _get_contractor(contractor_id)
    contractor_phone = contractor.get("phone", "")

    await send_notification(
        user_id=contractor_id,
        quote_token=quote_tok,
        notif_type="variation_declined",
        phone=contractor_phone,
        whatsapp_message=(
            f"La propuesta de cambio fue rechazada por el propietario. "
            f"Ver detalles: {_app_base_url()}/app/project/{quote_tok}"
        ),
        suppress_wa=suppress_wa,
    )

    return {"ok": True, "message": "Variation declined"}


# ---------------------------------------------------------------------------
# Section 4: Job cancellation
# ---------------------------------------------------------------------------

class CancelJobRequest(BaseModel):
    quote_token: str
    cancelled_by: str  # 'homeowner' | 'contractor'
    reason: Optional[str] = None
    user_auth_id: str


@router.post("/job/cancel")
async def cancel_job(req: CancelJobRequest, ctx: SandboxContext = Depends(resolve_sandbox)):
    """Cancel a job and issue full refund via Stripe."""
    quote = await _get_quote(req.quote_token)

    # Identity check: caller must be the project's homeowner or contractor
    quote_ho = quote.get("homeowner_auth_id") or ""
    quote_contractor = quote.get("contractor_id") or ""
    if req.cancelled_by == "homeowner" and req.user_auth_id != quote_ho:
        raise api_error(403, "Only the project homeowner can cancel")
    elif req.cancelled_by == "contractor" and req.user_auth_id != quote_contractor:
        raise api_error(403, "Only the project contractor can cancel")

    if quote.get("status") in ("cancelled", "complete"):
        raise api_error(409, "Job is already finalised")

    # Guard: no milestone can be past pending
    milestones = quote.get("milestones") or []
    for m in milestones:
        if m.get("status") not in ("pending", None, ""):
            raise HTTPException(
                status_code=400,
                detail="Cannot cancel — work has already started on a milestone",
            )

    payment_intent_id = quote.get("payment_intent_id")
    if not payment_intent_id:
        raise api_error(400, "No payment found to refund")

    sandbox = ctx.is_sandbox
    suppress_wa = ctx.suppress_whatsapp
    try:
        stripe_client = get_stripe_client(ctx)
    except StripeNotConfigured:
        raise api_error(500, "Stripe not configured")

    try:
        refund = stripe_client.refunds.create(payment_intent=payment_intent_id)
        refund_id = refund.id
        refund_amount_cents = refund.amount
        logger.info("Refund issued | quote=%s refund=%s amount_eur=%.2f", req.quote_token[:8], refund_id[:16], refund_amount_cents / 100)
    except stripe.error.StripeError as e:
        logger.error("Refund failed | quote=%s: %s", req.quote_token[:8], e)
        raise HTTPException(status_code=500, detail=f"Refund failed: {str(e)}")


    # Record cancellation (table uses scope_token column)
    async with http_client(timeout=10) as client:
        await client.post(
            f"{sb_url()}/cancellations",
            json={
                "scope_token": req.quote_token,
                "cancelled_by": req.cancelled_by,
                "reason": req.reason,
                "stripe_refund_id": refund_id,
                "refund_amount_cents": refund_amount_cents,
            },
            headers=sb_headers(),
        )

    await _patch_quote(req.quote_token, {"status": "cancelled", "payment_status": "refunded"})

    # Notify both parties
    contractor = await _get_contractor(quote["contractor_id"])
    contractor_phone = contractor.get("phone", "")
    homeowner_phone = quote.get("homeowner_phone", "")
    scope_title = (quote.get("quote_data") or {}).get("title", "el trabajo")

    msg = f"El trabajo '{scope_title}' ha sido cancelado. Reembolso en 5–7 días hábiles."

    homeowner_id = quote.get("homeowner_auth_id") or quote.get("homeowner_email") or ""
    if homeowner_id:
        await send_notification(user_id=homeowner_id, quote_token=req.quote_token, notif_type="job_cancelled",
                                phone=homeowner_phone, whatsapp_message=msg, suppress_wa=suppress_wa)
    await send_notification(user_id=quote["contractor_id"], quote_token=req.quote_token, notif_type="job_cancelled",
                            phone=contractor_phone, whatsapp_message=msg, suppress_wa=suppress_wa)

    return {"ok": True, "refund_id": refund_id, "message": "Job cancelled and refund issued"}


# ---------------------------------------------------------------------------
# Section 5: Reviews
# ---------------------------------------------------------------------------

class CreateReviewRequest(BaseModel):
    quote_token: str
    rating: int
    body: Optional[str] = None
    homeowner_auth_id: str


@router.post("/reviews/create")
async def create_review(req: CreateReviewRequest):
    """Homeowner submits review after job completion."""
    if req.rating < 1 or req.rating > 5:
        raise api_error(400, "Rating must be between 1 and 5")

    quote = await _get_quote(req.quote_token)

    # Identity check
    quote_ho = quote.get("homeowner_auth_id") or ""
    if not quote_ho or req.homeowner_auth_id != quote_ho:
        raise api_error(403, "Only the project homeowner can submit reviews")

    if quote.get("status") != "complete":
        raise api_error(400, "Job is not complete yet")

    contractor_id = quote["contractor_id"]

    # Insert review (UNIQUE constraint prevents duplicates; table uses scope_token column)
    async with http_client(timeout=10) as client:
        ins_resp = await client.post(
            f"{sb_url()}/reviews",
            json={
                "scope_token": req.quote_token,
                "contractor_id": contractor_id,
                "homeowner_auth_id": req.homeowner_auth_id,
                "rating": req.rating,
                "body": req.body,
            },
            headers=sb_headers(),
        )
    if ins_resp.status_code == 409:
        raise api_error(409, "Review already submitted for this job")
    if ins_resp.status_code not in (200, 201):
        raise api_error(500, "Failed to save review")

    # Recompute contractor avg_rating
    async with http_client(timeout=10) as client:
        reviews_resp = await client.get(
            f"{sb_url()}/reviews",
            params={"contractor_id": f"eq.{contractor_id}", "select": "rating"},
            headers=sb_headers(),
        )
    if reviews_resp.status_code == 200 and reviews_resp.json():
        all_ratings = [r["rating"] for r in reviews_resp.json()]
        avg = round(sum(all_ratings) / len(all_ratings), 2)
        count = len(all_ratings)
        async with http_client(timeout=10) as client:
            await client.patch(
                f"{sb_url()}/contractors",
                params={"id": f"eq.{contractor_id}"},
                json={"avg_rating": avg, "review_count": count},
                headers=sb_headers(),
            )

    return {"ok": True, "message": "Review submitted"}


# ---------------------------------------------------------------------------
# Section 6: Notifications
# ---------------------------------------------------------------------------

@router.get("/notifications")
async def get_notifications(user_id: str, limit: int = 30):
    """Returns notifications for a user, newest first."""
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


class MarkReadRequest(BaseModel):
    ids: List[str]


@router.post("/notifications/mark-read")
async def mark_notifications_read(req: MarkReadRequest):
    """Mark notification IDs as read."""
    for notif_id in req.ids:
        async with http_client(timeout=5) as client:
            await client.patch(
                f"{sb_url()}/notifications",
                params={"id": f"eq.{notif_id}"},
                json={"read": True},
                headers=sb_headers(),
            )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Read endpoints for frontend data fetching
# ---------------------------------------------------------------------------

@router.get("/milestone-updates/{quote_token}")
async def get_milestone_updates(quote_token: str):
    """Return all milestone proof submissions for a scope."""
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/milestone_updates",
            params={
                "scope_token": f"eq.{quote_token}",
                "select": "*",
                "order": "created_at.desc",
            },
            headers=sb_headers(),
        )
    return resp.json() if resp.status_code == 200 else []


@router.get("/variation-orders/{quote_token}")
async def get_variation_orders(quote_token: str):
    """Return all variation orders for a scope."""
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/variation_orders",
            params={
                "scope_token": f"eq.{quote_token}",
                "select": "*",
                "order": "created_at.asc",
            },
            headers=sb_headers(),
        )
    return resp.json() if resp.status_code == 200 else []
