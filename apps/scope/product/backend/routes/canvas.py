"""
Canvas — Shareable document URLs
=================================

Public endpoint that returns canvas data (brief, profile, or quote) by token.
No auth required for GET — anyone with the URL can view the document.

Endpoints:
  GET  /api/canvas/{token}     — Return canvas data (brief, profile, or quote)
  POST /api/quote/finalize     — Persist a finalized quote, return shareable URL
  POST /api/quote/update       — Update a draft quote by token
  POST /api/claim-profile      — Link a contractor profile to a Supabase auth user
  GET  /api/quotes             — List all quotes for a contractor
  GET  /api/homeowner/quotes   — List all quotes for a homeowner email
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, AliasChoices

from core import sb_url, sb_key, sb_headers, CurrentUser, require_contractor
from core import api_error  # noqa: F401 — ensures shared/errors.py is reachable
from payments import SandboxContext, resolve_sandbox
from payments.finance import compute_quote_financials
from core import http_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Supabase query helpers ────────────────────────────────────────────

async def _get_job_by_token(token: str) -> Optional[Dict[str, Any]]:
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/jobs",
            params={"inbox_token": f"eq.{token}", "select": "*", "limit": "1"},
            headers=sb_headers(),
        )
        if resp.status_code == 200:
            rows = resp.json()
            return rows[0] if rows else None
    return None


async def _get_contractor_display(contractor_id: str) -> tuple[str, str]:
    """Fetch contractor name and trade for display in the tracking page."""
    if not contractor_id:
        return "", ""
    try:
        async with http_client(timeout=8) as client:
            resp = await client.get(
                f"{sb_url()}/contractors",
                params={"id": f"eq.{contractor_id}", "select": "name,dossier", "limit": "1"},
                headers=sb_headers(),
            )
            if resp.status_code == 200:
                rows = resp.json()
                if rows:
                    name = rows[0].get("name", "")
                    dossier = rows[0].get("dossier") or {}
                    trade = dossier.get("trade", "")
                    return name, trade
    except Exception as e:
        logger.warning("Contractor display lookup failed for %s: %s", contractor_id[:12], e)
    return "", ""


async def _get_quote_by_token(token: str) -> Optional[Dict[str, Any]]:
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/quotes",
            params={"token": f"eq.{token}", "select": "*", "limit": "1"},
            headers=sb_headers(),
        )
        if resp.status_code == 200:
            rows = resp.json()
            return rows[0] if rows else None
    return None


# ── GET /api/canvas/{token} ───────────────────────────────────────────

@router.get("/canvas/{token}")
async def api_get_canvas(token: str):
    """Return canvas data for a shareable URL.

    Supports: briefs (inbox_token on jobs table), profiles (canvas_token on
    contractors table), quotes (token on quotes table).
    Returns canvas_type + typed data for the frontend to render the right template.
    """
    # 1. Check quotes first (new flow)
    quote_row = await _get_quote_by_token(token)
    if quote_row:
        quote_data = quote_row.get("quote_data") or {}
        if quote_data.get("title"):
            contractor_id = quote_row.get("contractor_id", "")
            contractor_name, contractor_trade = await _get_contractor_display(contractor_id)
            logger.info("Canvas served | type=quote token=%s", token[:8])
            return {
                "canvas_type": "quote",
                "quote": quote_data,
                "quote_data": quote_data,
                "scope": quote_data,
                "scope_data": quote_data,
                "milestones": [{**m, "title": m.get("title") or m.get("description", "")} for m in quote_row.get("milestones") or []],
                "contractor_id": contractor_id,
                "contractor_name": contractor_name,
                "contractor_trade": contractor_trade,
                "quote_token": token,
                "status": quote_row.get("status", "draft"),
                "payment_status": quote_row.get("payment_status", "unpaid"),
                "amount_total_cents": quote_row.get("amount_total_cents"),
                "homeowner_email": quote_row.get("homeowner_email"),
                "is_sandbox": bool(quote_row.get("is_sandbox", False)),
            }

    # 2. Check briefs
    job = await _get_job_by_token(token)
    if job:
        brief = job.get("brief") or {}
        if brief.get("title") or brief.get("description"):
            logger.info("Canvas served | type=brief token=%s", token[:8])
            return {
                "canvas_type": "brief",
                "brief": brief,
                "photos": job.get("brief_photos", []),
            }

    # 3. Check contractor profiles (with claim status)
    # Serve the canvas even if business_name/trade are empty — enrichment may
    # still be running. The frontend shows a loading/pending state in that case.
    try:
        from records.dossier import get_by_token
        contractor = await get_by_token(token)
        if contractor:
            canvas = contractor.get("canvas") or {}
            logger.info("Canvas served | type=profile token=%s enriched=%s",
                        token[:8], bool(canvas.get("business_name") or canvas.get("trade")))
            return {
                "canvas_type": "profile",
                "profile": canvas,
                "contractor_id": contractor.get("id", ""),
                "claimed": bool(contractor.get("claimed", False)),
                "stripe_onboarding_complete": bool(contractor.get("stripe_onboarding_complete", False)),
            }
    except Exception as e:
        logger.warning("Profile canvas lookup failed for token %s: %s", token[:8], e)

    logger.info("Canvas not found | token=%s", token[:8])
    raise HTTPException(status_code=404, detail="Canvas not found")


# ── POST /api/quote/finalize ──────────────────────────────────────────

class QuoteFinalizeRequest(BaseModel):
    contractor_id: str
    quote_data: Dict[str, Any] = Field(validation_alias=AliasChoices("quote_data", "scope_data"))
    auth_user_id: Optional[str] = None


@router.post("/quote/finalize")
async def api_finalize_quote(
    req: QuoteFinalizeRequest,
    ctx: SandboxContext = Depends(resolve_sandbox),
    caller: CurrentUser = Depends(require_contractor),
):
    """Persist a finalized quote to Supabase and return a shareable URL.

    Called when the contractor taps 'Finalize' in the quote builder.
    Generates a unique token for the standalone canvas link.

    Computes and stores financial fields at finalize time so they are
    available to the payment flow without re-deriving from quote_data.

    When X-Sandbox: true, is_sandbox is set on the quote row so the
    homeowner's browser can auto-enable sandbox mode when they open the link.
    """
    if req.contractor_id != caller.contractor_id:
        raise HTTPException(status_code=403, detail="Use your assigned contractor identity")
    if req.auth_user_id and req.auth_user_id != caller.id:
        raise HTTPException(status_code=403, detail="Use your authenticated user identity")
    sandbox = ctx.is_sandbox
    _url = sb_url()
    _key = sb_key()
    if not _url or not _key:
        raise HTTPException(status_code=500, detail="Database not configured")

    import uuid
    token = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    quote_data = dict(req.quote_data)
    if not quote_data.get("created_at"):
        quote_data["created_at"] = now[:10]  # YYYY-MM-DD

    fin = compute_quote_financials(quote_data)
    logger.info(
        "Quote financials | milestones_subtotal=%.2f materials=%.2f fee=%.2f iva=%.2f total=%.2f",
        fin.milestones_subtotal_cents / 100,
        fin.materials_upfront_cents / 100,
        fin.fee_cents / 100,
        fin.iva_cents / 100,
        fin.amount_total_cents / 100,
    )

    row = {
        "contractor_id": req.contractor_id,
        "auth_user_id": caller.id,
        "token": token,
        "quote_data": quote_data,
        "status": "finalized",
        "finalized_at": now,
        "amount_total_cents": fin.amount_total_cents,
        "materials_upfront_cents": fin.materials_upfront_cents,
        "stripe_fee_cents": fin.fee_cents,
        "iva_rate": fin.iva_rate,
        "milestones": fin.milestones,
        "is_sandbox": sandbox,
    }

    async with http_client(timeout=15) as client:
        resp = await client.post(
            f"{_url}/quotes",
            json=row,
            headers=sb_headers(),
        )
        if resp.status_code not in (200, 201):
            logger.error("Quote finalize insert failed: %d %s", resp.status_code, resp.text[:300])
            raise HTTPException(status_code=500, detail="Failed to save quote")

    logger.info(
        "Quote finalized | contractor=%s token=%s total_eur=%.2f phases=%d sandbox=%s",
        req.contractor_id[:12], token[:8],
        fin.amount_total_cents / 100,
        len(fin.milestones),
        sandbox,
    )
    return {
        "ok": True,
        "token": token,
        "canvas_url": f"{os.getenv('SCOPE_WEB_BASE_PATH', '/app')}/canvas/{token}",
        "amount_total_cents": fin.amount_total_cents,
    }


# ── GET /api/quotes ───────────────────────────────────────────────────

@router.get("/quotes")
async def api_list_quotes(contractor_id: str):
    """List all quotes for a contractor, most recent first.

    Returns quote summaries for the Dashboard "My Quotes" view.
    Uses pre-computed amount_total_cents (set at finalize time) so totals include
    materials_upfront, Leo fee, and IVA — not just the sum of line items.
    """
    if not contractor_id:
        raise HTTPException(status_code=400, detail="contractor_id required")

    async with http_client(timeout=15) as client:
        resp = await client.get(
            f"{sb_url()}/quotes",
            params={
                "contractor_id": f"eq.{contractor_id}",
                "select": (
                    "token,quote_data,status,payment_status,"
                    "amount_total_cents,materials_upfront_cents,milestones,"
                    "created_at,started_at,completed_at"
                ),
                "order": "created_at.desc",
            },
            headers=sb_headers(),
        )

    if resp.status_code != 200:
        logger.error("Quotes list failed: %d %s", resp.status_code, resp.text[:200])
        raise HTTPException(status_code=500, detail="Failed to fetch quotes")

    rows = resp.json()
    quotes_list = []
    for row in rows:
        qd = row.get("quote_data") or {}
        milestones = row.get("milestones") or []
        line_items = qd.get("line_items") or []

        amount_total_cents = row.get("amount_total_cents")
        if amount_total_cents is None:
            fin = compute_quote_financials(qd)
            amount_total_cents = fin.amount_total_cents

        milestones_total = len(milestones) if milestones else len(line_items)
        milestones_released = sum(1 for m in milestones if m.get("status") == "released")

        quotes_list.append({
            "token": row.get("token", ""),
            "title": qd.get("title") or "Untitled quote",
            "amount_total_cents": amount_total_cents,
            "materials_upfront_cents": row.get("materials_upfront_cents", 0),
            "status": row.get("status", "draft"),
            "payment_status": row.get("payment_status", "unpaid"),
            "milestones": [{**m, "title": m.get("title") or m.get("description", "")} for m in milestones],
            "milestones_total": milestones_total,
            "milestones_released": milestones_released,
            "created_at": row.get("created_at", ""),
            "started_at": row.get("started_at"),
            "completed_at": row.get("completed_at"),
        })

    logger.info("Quotes listed | contractor=%s count=%d", contractor_id[:12], len(quotes_list))
    return {"quotes": quotes_list, "scopes": quotes_list}


# ── POST /api/quote/update ────────────────────────────────────────────

class QuoteUpdateRequest(BaseModel):
    token: str
    quote_data: Dict[str, Any] = Field(validation_alias=AliasChoices("quote_data", "scope_data"))
    contractor_id: str


@router.post("/quote/update")
async def api_update_quote(req: QuoteUpdateRequest, caller: CurrentUser = Depends(require_contractor)):
    """Update an existing quote row by token.

    Called from FirstQuote in edit mode (editToken URL param).
    Validates that the requesting contractor owns the quote.
    The share link (token) stays the same — homeowners keep the same URL.
    """
    if req.contractor_id != caller.contractor_id:
        raise HTTPException(status_code=403, detail="Use your assigned contractor identity")
    quote_row = await _get_quote_by_token(req.token)
    if not quote_row:
        raise HTTPException(status_code=404, detail="Quote not found")

    if quote_row.get("contractor_id", "") != req.contractor_id:
        raise HTTPException(status_code=403, detail="Not your quote")

    if quote_row.get("payment_status") == "paid":
        raise HTTPException(status_code=409, detail="Use a variation for a paid project")
    fin = compute_quote_financials(dict(req.quote_data))
    async with http_client(timeout=15) as client:
        resp = await client.patch(
            f"{sb_url()}/quotes",
            params={"token": f"eq.{req.token}"},
            json={"quote_data": dict(req.quote_data), "amount_total_cents": fin.amount_total_cents,
                  "materials_upfront_cents": fin.materials_upfront_cents, "stripe_fee_cents": fin.fee_cents,
                  "iva_rate": fin.iva_rate, "milestones": fin.milestones},
            headers=sb_headers(),
        )
        if resp.status_code not in (200, 201, 204):
            logger.error("Quote update failed: %d %s", resp.status_code, resp.text[:300])
            raise HTTPException(status_code=500, detail="Failed to update quote")

    logger.info("Quote updated | contractor=%s token=%s", req.contractor_id[:12], req.token[:8])
    return {"ok": True, "token": req.token, "canvas_url": f"{os.getenv('SCOPE_WEB_BASE_PATH', '/app')}/canvas/{req.token}"}


# ── POST /api/claim-profile ───────────────────────────────────────────

class ClaimProfileRequest(BaseModel):
    canvas_token: str
    access_token: str  # Supabase JWT from Google OAuth


@router.post("/claim-profile")
async def api_claim_profile(req: ClaimProfileRequest):
    """Link a contractor profile to a Supabase auth user (claim flow).

    Called from the AuthCallback page after Google OAuth completes.
    Verifies the JWT, finds the contractor by canvas_token, and marks it claimed.
    """
    from core import _verify_supabase_jwt

    user = await _verify_supabase_jwt(req.access_token)
    if not user or not user.get("id"):
        logger.warning("Claim profile: invalid JWT | token=%s", req.canvas_token[:8])
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    auth_user_id = user["id"]
    auth_email = user.get("email", "")

    try:
        from records.dossier import get_by_token
        contractor = await get_by_token(req.canvas_token)
    except Exception as e:
        logger.error("Claim profile: dossier lookup failed: %s", e)
        raise HTTPException(status_code=500, detail="Profile lookup failed")

    if not contractor:
        raise HTTPException(status_code=404, detail="Profile not found")

    contractor_id = contractor.get("id", "")
    if not contractor_id:
        raise HTTPException(status_code=500, detail="Profile has no ID")

    existing_auth = contractor.get("auth_user_id")
    if existing_auth and existing_auth != auth_user_id:
        raise HTTPException(status_code=409, detail="This profile has already been claimed by another account")

    now = datetime.now(timezone.utc).isoformat()

    async with http_client(timeout=15) as client:
        resp = await client.patch(
            f"{sb_url()}/contractors",
            params={"id": f"eq.{contractor_id}"},
            json={"auth_user_id": auth_user_id, "claimed": True, "claimed_at": now},
            headers=sb_headers(),
        )
        if resp.status_code not in (200, 201, 204):
            logger.error("Claim profile patch failed: %d %s", resp.status_code, resp.text[:300])
            raise HTTPException(status_code=500, detail="Failed to claim profile")

    logger.info(
        "Profile claimed | contractor=%s auth_user=%s email=%s",
        contractor_id[:12], auth_user_id[:8], auth_email,
    )
    return {"ok": True, "contractor_id": contractor_id, "auth_user_id": auth_user_id, "claimed": True}


# ── GET /api/contractor/by-auth-user/{auth_user_id} ──────────────────

@router.get("/contractor/by-auth-user/{auth_user_id}")
async def get_contractor_by_auth_user(auth_user_id: str):
    """Look up a claimed contractor by their Supabase auth user ID.

    Used by Login.tsx and AuthCallback.tsx to restore session for returning
    contractors who sign in via Google OAuth without a claim token.
    """
    if not auth_user_id:
        raise HTTPException(status_code=400, detail="auth_user_id required")

    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/contractors",
            params={
                "auth_user_id": f"eq.{auth_user_id}",
                "claimed": "eq.true",
                "select": "id,name,phone,stripe_onboarding_complete,dossier",
                "limit": "1",
            },
            headers=sb_headers(),
        )

    if resp.status_code == 400:
        # Usually invalid UUID format or column issue
        logger.warning("by-auth-user lookup 400: %s", resp.text[:200])
        raise HTTPException(status_code=404, detail="No claimed contractor for this auth user")
    if resp.status_code != 200:
        logger.error("by-auth-user lookup failed: %d %s", resp.status_code, resp.text[:200])
        raise HTTPException(status_code=500, detail="Lookup failed")

    rows = resp.json()
    if not rows:
        raise HTTPException(status_code=404, detail="No claimed contractor for this auth user")

    row = rows[0]
    logger.info(
        "Contractor session restored | contractor=%s auth_user=%s",
        row["id"][:12], auth_user_id[:8],
    )
    dossier = row.get("dossier") or {}
    return {
        "ok": True,
        "contractor_id": row["id"],
        "contractor_name": row.get("name", ""),
        "contractor_trade": dossier.get("trade", ""),
        "stripe_onboarding_complete": bool(row.get("stripe_onboarding_complete", False)),
    }


# ── POST /api/contractor/set-phone ────────────────────────────────────

class SetPhoneRequest(BaseModel):
    contractor_id: str
    phone: str


@router.post("/contractor/set-phone")
async def api_set_phone(req: SetPhoneRequest):
    """Store phone number on a contractor record and kick off social proof."""
    phone = req.phone.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="phone required")

    clean = phone.lstrip("+").replace(" ", "").replace("-", "")
    if len(clean) < 7:
        raise HTTPException(status_code=400, detail="phone too short")

    try:
        from records.dossier import set_phone
        await set_phone(req.contractor_id, clean)
        logger.info("Phone stored | contractor=%s phone=%s***", req.contractor_id[:12], clean[:6])
    except Exception as e:
        logger.error("set-phone: failed to store phone for %s: %s", req.contractor_id[:12], e)
        raise HTTPException(status_code=500, detail="Failed to store phone")

    import asyncio
    from routes.profile_import import _run_social_proof_background_by_id
    asyncio.create_task(_run_social_proof_background_by_id(req.contractor_id, clean))
    logger.info("Social proof queued | contractor=%s", req.contractor_id[:12])

    return {"ok": True, "contractor_id": req.contractor_id}


# ── GET /api/homeowner/quotes ─────────────────────────────────────────

@router.get("/homeowner/quotes")
async def get_homeowner_quotes(email: str, limit: int = 50):
    """Return all quotes for a homeowner email, ordered by created_at DESC.

    Used by MyQuotes.tsx to show the homeowner's job hub.
    """
    if not email:
        raise HTTPException(status_code=400, detail="email is required")

    async with http_client(timeout=15) as client:
        resp = await client.get(
            f"{sb_url()}/quotes",
            params={
                "homeowner_email": f"eq.{email}",
                "select": "token,quote_data,status,payment_status,amount_total_cents,milestones,contractor_id,created_at,finalized_at,completed_at",
                "order": "created_at.desc",
                "limit": str(limit),
            },
            headers=sb_headers(),
        )
    if resp.status_code != 200:
        logger.error("Homeowner quotes fetch failed for %s: %s", email, resp.text)
        return []

    quotes = resp.json()

    enriched = []
    contractor_cache: dict = {}
    for quote in quotes:
        contractor_id = quote.get("contractor_id", "")
        if contractor_id and contractor_id not in contractor_cache:
            async with http_client(timeout=10) as client:
                cr = await client.get(
                    f"{sb_url()}/contractors",
                    params={"id": f"eq.{contractor_id}", "select": "name,trade,photo_url", "limit": "1"},
                    headers=sb_headers(),
                )
            if cr.status_code == 200 and cr.json():
                contractor_cache[contractor_id] = cr.json()[0]
            else:
                contractor_cache[contractor_id] = {}

        contractor_info = contractor_cache.get(contractor_id, {})
        enriched.append({
            **quote,
            "scope_data": quote.get("quote_data") or {},
            "contractor_name": contractor_info.get("name", ""),
            "contractor_trade": contractor_info.get("trade", ""),
            "contractor_photo_url": contractor_info.get("photo_url", ""),
        })

    logger.info("Homeowner quotes fetched | email=%s count=%d", email[:20], len(enriched))
    return enriched
