"""
Admin — Internal admin and Customer 360 endpoints
==================================================

These endpoints are for internal use only (Peter / support tool sidebars).
They are NOT secured with auth in the current MVP — add IP allowlisting or
a shared secret header before exposing to the internet.

Endpoints:
  GET  /api/admin/customer/:phone   — Customer 360 aggregation
  POST /api/admin/api-keys          — Create a new API key (internal use only)
  GET  /api/admin/api-keys          — List all active API keys
  DELETE /api/admin/api-keys/:id    — Deactivate an API key
"""

from __future__ import annotations

import logging
import os
import secrets
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core import sb_url, sb_headers
from core import http_client
from core import api_error

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# API Key management  (POST/GET/DELETE /api/admin/api-keys)
# ---------------------------------------------------------------------------

class CreateApiKeyRequest(BaseModel):
    name: str
    permissions: list[str] = ["read"]
    owner_id: Optional[str] = None


@router.post("/api/admin/api-keys")
async def create_api_key(body: CreateApiKeyRequest):
    """Generate a new API key and store it. Returns the key (only shown once)."""
    raw_key = "leo_key_" + secrets.token_urlsafe(32)
    payload: Dict[str, Any] = {
        "key": raw_key,
        "name": body.name,
        "permissions": body.permissions,
        "is_active": True,
    }
    if body.owner_id:
        payload["owner_id"] = body.owner_id

    async with http_client(timeout=10) as client:
        resp = await client.post(
            f"{sb_url()}/api_keys",
            headers=sb_headers(),
            json=payload,
        )
    if resp.status_code not in (200, 201):
        logger.error("Failed to create API key: %s", resp.text[:200])
        raise api_error(500, "Failed to create API key")

    row = resp.json()[0] if isinstance(resp.json(), list) else resp.json()
    logger.info("API key created: name=%s id=%s", body.name, str(row.get("id", ""))[:8])
    return {
        "id": row.get("id"),
        "key": raw_key,  # only time the raw key is returned — store it now
        "name": body.name,
        "permissions": body.permissions,
        "created_at": row.get("created_at"),
    }


@router.get("/api/admin/api-keys")
async def list_api_keys():
    """List all active API keys (keys are masked)."""
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/api_keys",
            headers=sb_headers(),
            params={
                "is_active": "eq.true",
                "select": "id,name,permissions,owner_id,created_at,last_used_at",
                "order": "created_at.desc",
            },
        )
    if resp.status_code != 200:
        raise api_error(500, "Failed to fetch API keys")
    return resp.json()


@router.delete("/api/admin/api-keys/{key_id}")
async def deactivate_api_key(key_id: str):
    """Deactivate an API key by ID (soft delete)."""
    async with http_client(timeout=10) as client:
        resp = await client.patch(
            f"{sb_url()}/api_keys",
            headers=sb_headers(),
            params={"id": f"eq.{key_id}"},
            json={"is_active": False},
        )
    if resp.status_code not in (200, 204):
        raise api_error(500, "Failed to deactivate key")
    logger.info("API key deactivated: %s", key_id[:8])
    return {"deactivated": key_id}


# ---------------------------------------------------------------------------
# GET /api/admin/customer/:phone — Customer 360
# ---------------------------------------------------------------------------

@router.get("/api/admin/customer/{phone}")
async def get_customer_360(phone: str):
    """Aggregate all available data for a customer identified by phone number.

    Data sources:
    - Supabase: contractor profile (if contractor), scopes, milestones, job messages
    - Stripe: payment history for scopes where this phone appears
    - mem0: AI memories for this phone
    - activity_events: recent frontend event timeline

    This JSON is consumed by:
    - Intercom Canvas Kit panel (GET canvas → return this JSON → Intercom renders it)
    - Crisp sidebar widget
    - Internal admin tooling

    Phone number is canonical identity (E.164 or local format — we try both).
    """
    if not phone:
        raise api_error(400, "phone required")

    # Normalise phone: strip + and spaces for DB lookups
    raw_phone = phone.strip()
    clean_phone = raw_phone.lstrip("+").replace(" ", "").replace("-", "")

    customer_data: Dict[str, Any] = {
        "phone": raw_phone,
        "identity": None,
        "role": "unknown",
        "scopes": [],
        "recent_events": [],
        "stripe": None,
        "memories": [],
        "error_parts": [],
    }

    # ── 1. Contractor lookup ──────────────────────────────────────────────────
    try:
        async with http_client(timeout=10) as client:
            cr = await client.get(
                f"{sb_url()}/contractors",
                params={
                    "or": f"(phone.eq.{clean_phone},phone.eq.+{clean_phone},phone.eq.{raw_phone})",
                    "select": "id,name,trade,phone,claimed,stripe_account_id,stripe_onboarding_complete,created_at",
                    "limit": "1",
                },
                headers=sb_headers(),
            )
        if cr.status_code == 200 and cr.json():
            row = cr.json()[0]
            customer_data["identity"] = {
                "id": row["id"],
                "name": row.get("name", ""),
                "trade": row.get("trade", ""),
                "phone": row.get("phone", ""),
                "claimed": row.get("claimed", False),
                "member_since": (row.get("created_at", "") or "")[:10],
            }
            customer_data["role"] = "contractor"
            contractor_id = row["id"]
            stripe_account_id = row.get("stripe_account_id", "")

            # ── 2. Contractor scopes ──────────────────────────────────────
            try:
                async with http_client(timeout=10) as client:
                    sr = await client.get(
                        f"{sb_url()}/quotes",
                        params={
                            "contractor_id": f"eq.{contractor_id}",
                            "select": "token,quote_data,status,payment_status,amount_total_cents,milestones,is_sandbox,created_at,finalized_at",
                            "order": "created_at.desc",
                            "limit": "20",
                            "is_sandbox": "eq.false",
                        },
                        headers=sb_headers(),
                    )
                if sr.status_code == 200:
                    for scope in sr.json():
                        scope_summary = {
                            "token": scope.get("token", "")[:8] + "…",
                            "title": (scope.get("quote_data") or {}).get("title", "Scope"),
                            "status": scope.get("status", ""),
                            "payment_status": scope.get("payment_status", ""),
                            "amount_eur": round((scope.get("amount_total_cents") or 0) / 100, 2),
                            "created_at": (scope.get("created_at") or "")[:10],
                            "milestones_count": len(scope.get("milestones") or []),
                            "milestones_released": sum(
                                1 for m in (scope.get("milestones") or []) if m.get("status") == "released"
                            ),
                        }
                        customer_data["scopes"].append(scope_summary)
            except Exception as exc:
                logger.warning("Customer 360: scopes fetch failed: %s", exc)
                customer_data["error_parts"].append("scopes")

            # ── 3. Stripe Connect account status ──────────────────────────
            if stripe_account_id:
                try:
                    import stripe
                    stripe_key = ""
                    try:
                        from config import settings
                        stripe_key = settings.STRIPE_SECRET_KEY or os.getenv("STRIPE_SECRET_KEY", "")
                    except Exception:
                        stripe_key = os.getenv("STRIPE_SECRET_KEY", "")

                    if stripe_key:
                        from payments import build_stripe_client_from_key
                        stripe_client = build_stripe_client_from_key(stripe_key)
                        acct = stripe_client.accounts.retrieve(stripe_account_id)
                        customer_data["stripe"] = {
                            "account_id": stripe_account_id,
                            "charges_enabled": bool(acct.charges_enabled),
                            "payouts_enabled": bool(acct.payouts_enabled),
                            "details_submitted": bool(acct.details_submitted),
                        }
                except Exception as exc:
                    logger.warning("Customer 360: Stripe lookup failed: %s", exc)
                    customer_data["error_parts"].append("stripe")

    except Exception as exc:
        logger.warning("Customer 360: contractor lookup failed: %s", exc)

    # ── 4. Homeowner lookup (if not found as contractor) ─────────────────────
    if customer_data["role"] == "unknown":
        try:
            async with http_client(timeout=10) as client:
                hr = await client.get(
                    f"{sb_url()}/quotes",
                    params={
                        "or": f"(homeowner_phone.eq.{clean_phone},homeowner_phone.eq.+{clean_phone},homeowner_phone.eq.{raw_phone})",
                        "select": "token,quote_data,status,payment_status,amount_total_cents,milestones,contractor_id,created_at",
                        "order": "created_at.desc",
                        "limit": "10",
                        "is_sandbox": "eq.false",
                    },
                    headers=sb_headers(),
                )
            if hr.status_code == 200 and hr.json():
                customer_data["role"] = "homeowner"
                customer_data["identity"] = {"phone": raw_phone, "name": "Homeowner"}
                for scope in hr.json():
                    scope_summary = {
                        "token": scope.get("token", "")[:8] + "…",
                        "title": (scope.get("quote_data") or {}).get("title", "Scope"),
                        "status": scope.get("status", ""),
                        "payment_status": scope.get("payment_status", ""),
                        "amount_eur": round((scope.get("amount_total_cents") or 0) / 100, 2),
                        "created_at": (scope.get("created_at") or "")[:10],
                    }
                    customer_data["scopes"].append(scope_summary)
        except Exception as exc:
            logger.warning("Customer 360: homeowner lookup failed: %s", exc)

    # ── 5. Activity events (recent timeline) ─────────────────────────────────
    try:
        async with http_client(timeout=8) as client:
            er = await client.get(
                f"{sb_url()}/activity_events",
                params={
                    "or": f"(phone.eq.{clean_phone},phone.eq.+{clean_phone},phone.eq.{raw_phone})",
                    "select": "event,properties,quote_token,created_at",
                    "order": "created_at.desc",
                    "limit": "30",
                    "is_sandbox": "eq.false",
                },
                headers=sb_headers(),
            )
        if er.status_code == 200:
            customer_data["recent_events"] = [
                {
                    "event": row.get("event", ""),
                    "quote_token": (row.get("quote_token") or "")[:8],
                    "created_at": (row.get("created_at") or "")[:19].replace("T", " "),
                }
                for row in er.json()
            ]
    except Exception as exc:
        logger.warning("Customer 360: events fetch failed: %s", exc)
        customer_data["error_parts"].append("events")

    # ── 6. mem0 memories ─────────────────────────────────────────────────────
    try:
        import mem0
        m = mem0.MemoryClient()
        memories = m.search(raw_phone, agent_id="leo-quote", limit=10)
        customer_data["memories"] = [
            {"text": mem.get("memory", ""), "created": mem.get("created_at", "")[:10]}
            for mem in (memories or [])
        ]
    except Exception:
        pass  # mem0 is optional — silently skip if not configured

    customer_data["found"] = customer_data["role"] != "unknown"
    logger.info(
        "Customer 360 | phone=%s*** role=%s scopes=%d events=%d",
        raw_phone[:6], customer_data["role"],
        len(customer_data["scopes"]), len(customer_data["recent_events"]),
    )
    return customer_data
