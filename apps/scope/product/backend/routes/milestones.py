"""
Milestones — Proof submission and fund release
===============================================

POST /v1/projects/:token/milestones/:idx/proof   — Contractor submits proof photos
POST /v1/projects/:token/milestones/:idx/release  — Homeowner releases funds from escrow

Identity is resolved from the JWT (Authorization header).  No identity fields in request body.
"""

from __future__ import annotations

import datetime
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
    build_stripe_client_from_key,
    get_stripe_client,
    resolve_sandbox,
)
from state_machine import assert_transition
from project_access import is_project_homeowner
from core import http_client
from core import api_error
from routes.projects import get_quote, get_contractor, patch_quote, tracking_url
from routes.notifications import send_notification

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# POST /projects/:token/milestones/:idx/proof
# ---------------------------------------------------------------------------

class SubmitProofBody(BaseModel):
    photos: List[str] = []
    voice_url: Optional[str] = None
    note: Optional[str] = None


@router.post("/projects/{token}/milestones/{idx}/proof")
async def submit_proof(
    token: str,
    idx: int,
    body: SubmitProofBody,
    caller: CurrentUser = Depends(require_auth),
    ctx: SandboxContext = Depends(resolve_sandbox),
):
    """Contractor submits proof photos + note for a milestone.

    - Inserts milestone_updates row (status=proof_submitted)
    - Patches quotes.milestones[idx].status = proof_submitted
    - Notifies homeowner via in-app + WhatsApp (suppressed in sandbox)
    """
    if caller.role != "contractor":
        raise api_error(403, "Only a contractor can submit proof")

    suppress_wa = ctx.suppress_whatsapp
    quote = await get_quote(token)

    if quote.get("contractor_id") != caller.contractor_id:
        raise api_error(403, "You are not assigned to this project")

    if quote.get("payment_status") != "paid":
        raise api_error(400, "Project is not paid — cannot submit proof")

    milestones = quote.get("milestones") or []
    if idx < 0 or idx >= len(milestones):
        raise api_error(400, "Invalid milestone index")

    # Insert milestone_updates row (table uses scope_token column)
    async with http_client(timeout=15) as client:
        ins_resp = await client.post(
            f"{sb_url()}/milestone_updates",
            json={
                "scope_token": token,
                "milestone_index": idx,
                "photos": body.photos,
                "voice_url": body.voice_url,
                "note": body.note,
                "status": "proof_submitted",
            },
            headers=sb_headers(),
        )
    if ins_resp.status_code not in (200, 201):
        logger.error("Failed to insert milestone_update: %s", ins_resp.text)
        raise api_error(500, "Failed to record proof")

    # Patch milestone status in quotes.milestones JSON
    milestones[idx]["status"] = "proof_submitted"
    await patch_quote(token, {"milestones": milestones, "payment_status": "paid"})

    # Advance project status to in_progress on first proof
    if quote.get("status") in ("paid", None):
        await patch_quote(token, {"status": "in_progress"})

    # Notify homeowner
    homeowner_id = quote.get("homeowner_auth_id") or quote.get("homeowner_email") or ""
    homeowner_phone = quote.get("homeowner_phone") or ""
    ho_email = quote.get("homeowner_email") or ""
    contractor = await get_contractor(quote["contractor_id"])
    contractor_name = contractor.get("name", "Tu contratista")
    project_url = tracking_url(token, ho_email)
    milestone_label = milestones[idx].get("title", f"fase {idx + 1}")

    if homeowner_id:
        await send_notification(
            user_id=homeowner_id,
            quote_token=token,
            notif_type="proof_submitted",
            milestone_index=idx,
            phone=homeowner_phone,
            whatsapp_message=(
                f"{contractor_name} ha enviado fotos de la {milestone_label}. "
                f"Revísalas y aprueba el pago. {project_url}"
            ),
            suppress_wa=suppress_wa,
        )

    logger.info(
        "Proof submitted | project=%s milestone=%d photos=%d sandbox=%s",
        token[:8], idx, len(body.photos), ctx.is_sandbox,
    )
    return {"ok": True, "message": "Proof submitted — homeowner notified"}


# ---------------------------------------------------------------------------
# POST /projects/:token/milestones/:idx/release
# ---------------------------------------------------------------------------

@router.post("/projects/{token}/milestones/{idx}/release")
async def release_milestone(
    token: str,
    idx: int,
    caller: CurrentUser = Depends(require_auth),
    ctx: SandboxContext = Depends(resolve_sandbox),
):
    """Homeowner approves a milestone and releases funds from escrow.

    Uses Stripe Transfer with idempotency key to prevent double-release.
    """
    if caller.role != "homeowner":
        raise api_error(403, "Only the homeowner can release milestones")

    quote = await get_quote(token)

    # Identity check
    if not is_project_homeowner(caller, quote):
        raise api_error(403, "Only the project homeowner can release milestones")

    if quote.get("payment_status") != "paid":
        raise api_error(400, "Project is not paid")

    milestones = quote.get("milestones") or []
    if idx < 0 or idx >= len(milestones):
        raise api_error(400, "Invalid milestone index")

    milestone = milestones[idx]
    assert_transition(
        "milestone", milestone.get("status") or "pending", "released",
        actor_role="homeowner",
        status_code=409 if milestone.get("status") == "released" else 400,
    )

    contractor = await get_contractor(quote["contractor_id"])
    stripe_account_id = contractor.get("stripe_account_id", "")
    if not stripe_account_id:
        raise api_error(400, "Contractor has no Stripe account")

    # Resolve amount_cents
    amount_cents = milestone.get("amount_cents", 0)
    if not amount_cents:
        raw_amount = milestone.get("amount", 0)
        try:
            amount_cents = int(float(str(raw_amount).replace("€", "").strip()) * 100)
        except (ValueError, TypeError):
            amount_cents = 0

    if amount_cents <= 0:
        raise api_error(400, "Milestone has no payable amount")

    # Sandbox quote always uses test Stripe key regardless of request header
    quote_is_sandbox = quote.get("is_sandbox", False)
    sandbox = ctx.is_sandbox or quote_is_sandbox
    suppress_wa = ctx.suppress_whatsapp
    try:
        if quote_is_sandbox and not ctx.is_sandbox:
            from config import settings as _settings
            sandbox_key = getattr(_settings, "STRIPE_SECRET_KEY_TEST", "") or os.getenv("STRIPE_SECRET_KEY_TEST", "")
            stripe_client = build_stripe_client_from_key(sandbox_key)
            logger.info("Sandbox quote — overriding to test Stripe key | project=%s", token[:8])
        else:
            stripe_client = get_stripe_client(ctx)
    except StripeNotConfigured:
        raise api_error(500, "Stripe not configured")

    idempotency_key = f"{token}-milestone-{idx}"
    try:
        transfer = stripe_client.transfers.create(
            amount=amount_cents,
            currency="eur",
            destination=stripe_account_id,
            idempotency_key=idempotency_key,
            metadata={
                "quote_token": token,
                "milestone_index": idx,
                "milestone_title": milestone.get("title", ""),
            },
        )
        transfer_id = transfer.id
        logger.info(
            "Transfer created | project=%s milestone=%d amount_eur=%.2f transfer=%s sandbox=%s",
            token[:8], idx, amount_cents / 100, transfer_id[:16], sandbox,
        )
    except stripe.error.IdempotencyError:
        logger.info("Idempotency hit — already released | project=%s milestone=%d", token[:8], idx)
        transfer_id = "idempotent-duplicate"
    except stripe.error.StripeError as e:
        logger.error("Transfer failed | project=%s: %s", token[:8], e)
        raise HTTPException(
            status_code=500,
            detail=f"Transfer failed: {getattr(e, 'user_message', None) or str(e)}",
        )

    # Update milestone_updates row
    now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    async with http_client(timeout=15) as client:
        await client.patch(
            f"{sb_url()}/milestone_updates",
            params={"scope_token": f"eq.{token}", "milestone_index": f"eq.{idx}"},
            json={"status": "released", "released_at": now_iso, "stripe_transfer_id": transfer_id},
            headers=sb_headers(),
        )

    # Update quotes.milestones JSON
    milestones[idx]["status"] = "released"
    all_released = all(m.get("status") == "released" for m in milestones)
    quote_patch: dict = {"milestones": milestones}
    if all_released:
        quote_patch["status"] = "complete"
        quote_patch["completed_at"] = now_iso
    await patch_quote(token, quote_patch)

    # Notifications
    contractor_name = contractor.get("name", "Tu contratista")
    contractor_phone = contractor.get("phone", "")
    contractor_user_id = contractor.get("id") or quote["contractor_id"]
    homeowner_id = quote.get("homeowner_auth_id") or quote.get("homeowner_email") or ""
    ho_email = quote.get("homeowner_email") or ""
    project_url = tracking_url(token, ho_email)
    milestone_title = milestone.get("title", f"Fase {idx + 1}")
    amount_eur = f"€{amount_cents / 100:.0f}"

    await send_notification(
        user_id=contractor_user_id,
        quote_token=token,
        notif_type="milestone_released",
        milestone_index=idx,
        phone=contractor_phone,
        whatsapp_message=f"{amount_eur} liberado · {milestone_title} aprobado. Ver en app: {project_url}",
        suppress_wa=suppress_wa,
    )
    if homeowner_id:
        await send_notification(
            user_id=homeowner_id,
            quote_token=token,
            notif_type="payment_released",
            milestone_index=idx,
            suppress_wa=suppress_wa,
        )

    if all_released:
        from routes.notifications import send_whatsapp
        if contractor_phone:
            await send_whatsapp(
                contractor_phone,
                f"¡Trabajo completado! Todos los pagos han sido transferidos. {project_url}",
                suppress=suppress_wa,
            )
        homeowner_phone = quote.get("homeowner_phone", "")
        if homeowner_phone:
            await send_whatsapp(
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
