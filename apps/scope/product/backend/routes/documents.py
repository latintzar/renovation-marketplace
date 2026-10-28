"""
Documents — Consent records, agreement PDF, and invoice PDF
===========================================================

Route handlers that adapt scope-app Supabase rows into the typed payloads
consumed by ``apps/scope/product/backend/documents/``. Jinja/WeasyPrint rendering,
template loading, consent hashing, context-building, and DocuSeal glue all
live in ``documents/`` — this module is the thin Supabase → payload
adapter. ``documents`` was demoted from ``packages/`` in Phase 5 Wave 8
(single consumer; regraduates to ``packages/doc_engine/`` when a second
app needs the render/consent/DocuSeal primitives).

Endpoints:
  POST /api/documents/:quote_token/record-consent
  GET  /api/documents/:quote_token/agreement
  GET  /api/documents/:quote_token/invoice
"""

from __future__ import annotations

import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from core import api_error, http_client, sb_headers, sb_url
from documents import (
    AgreementDoc,
    InvoiceDoc,
    InvoicePayload,
    JobInfo,
    Milestone,
    Money,
    PartyInfo,
    QuotePayload,
)

logger = logging.getLogger(__name__)
router = APIRouter()

APP_BASE_URL_DEFAULT = "http://127.0.0.1:18260"


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
        return {}
    return resp.json()[0]


def _milestone_amount_cents(m: dict) -> int:
    cents = m.get("amount_cents", 0)
    if cents:
        return int(cents)
    raw = m.get("amount", 0)
    try:
        return int(float(str(raw).replace("€", "").strip()) * 100)
    except (ValueError, TypeError):
        return 0


def _parse_release_date(value: Optional[str]) -> Optional[datetime.date]:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except Exception:
        return None


def _quote_payload(quote: dict, contractor: dict) -> QuotePayload:
    """Build the typed :class:`QuotePayload` for :class:`AgreementDoc`.

    Pulls milestones / totals from the Supabase row (falling back to
    ``quote_data.line_items`` when the tracking array hasn't been
    materialised yet). Pure adapter — no money arithmetic here; the
    package computes any derived values.
    """
    quote_data = quote.get("quote_data") or {}
    raw_milestones = quote.get("milestones") or quote_data.get("line_items") or []

    milestones: list[Milestone] = []
    for m in raw_milestones:
        milestones.append(
            Milestone(
                title=m.get("description") or m.get("title") or "",
                amount=Money.from_cents(_milestone_amount_cents(m)),
                released_at=_parse_release_date(m.get("released_at")),
            )
        )

    total_cents = int(quote.get("amount_total_cents") or sum(m.amount.cents for m in milestones))
    leo_fee_cents = int(quote.get("stripe_fee_cents") or 0)
    materials_cents = int(quote.get("materials_upfront_cents") or 0)
    iva_rate = int(quote.get("iva_rate") or 0)

    homeowner_email = quote.get("homeowner_email") or ""
    homeowner_name = quote_data.get("homeowner_name") or homeowner_email

    return QuotePayload(
        quote_token=quote["token"],
        homeowner=PartyInfo(name=homeowner_name, email=homeowner_email),
        contractor=PartyInfo(
            name=contractor.get("name", ""),
            email=contractor.get("email", ""),
            trade=contractor.get("trade") or None,
            address=contractor.get("location") or None,
        ),
        job=JobInfo(
            title=quote_data.get("title") or "Obra",
            address=quote_data.get("location") or "",
            description=quote_data.get("description") or None,
        ),
        milestones=milestones,
        total=Money.from_cents(total_cents),
        leo_fee=Money.from_cents(leo_fee_cents),
        materials_upfront=Money.from_cents(materials_cents),
        iva_rate_pct=iva_rate,
        agreement_date=datetime.date.today(),
    )


def _invoice_payload(quote: dict, contractor: dict, milestone_updates: list[dict]) -> InvoicePayload:
    """Typed :class:`InvoicePayload` for :class:`InvoiceDoc`.

    Merges per-milestone release dates from the ``milestone_updates``
    rows into the tracking milestones. Completion date comes from the
    quote row (``completed_at`` ISO-8601 string).
    """
    quote_data = quote.get("quote_data") or {}
    raw_milestones = quote.get("milestones") or quote_data.get("line_items") or []

    release_by_idx: dict[int, Optional[datetime.date]] = {}
    for mu in milestone_updates:
        idx = mu.get("milestone_index", -1)
        release_by_idx[idx] = _parse_release_date(mu.get("released_at"))

    milestones: list[Milestone] = []
    for i, m in enumerate(raw_milestones):
        milestones.append(
            Milestone(
                title=m.get("description") or m.get("title") or "",
                amount=Money.from_cents(_milestone_amount_cents(m)),
                released_at=release_by_idx.get(i) or _parse_release_date(m.get("released_at")),
            )
        )

    total_cents = int(quote.get("amount_total_cents") or 0)
    leo_fee_cents = int(quote.get("stripe_fee_cents") or 0)
    materials_cents = int(quote.get("materials_upfront_cents") or 0)
    iva_rate = int(quote.get("iva_rate") or 0)

    completion_date = _parse_release_date(quote.get("completed_at")) or datetime.date.today()
    homeowner_email = quote.get("homeowner_email") or ""
    homeowner_name = quote_data.get("homeowner_name") or homeowner_email

    return InvoicePayload(
        quote_token=quote["token"],
        homeowner=PartyInfo(name=homeowner_name, email=homeowner_email),
        contractor=PartyInfo(
            name=contractor.get("name", ""),
            email=contractor.get("email", ""),
            trade=contractor.get("trade") or None,
            address=contractor.get("location") or None,
        ),
        job=JobInfo(
            title=quote_data.get("title") or "Obra",
            address=quote_data.get("location") or "",
            description=quote_data.get("description") or None,
        ),
        milestones=milestones,
        materials_upfront=Money.from_cents(materials_cents),
        leo_fee=Money.from_cents(leo_fee_cents),
        iva_rate_pct=iva_rate,
        total=Money.from_cents(total_cents),
        completion_date=completion_date,
        payment_intent_id=quote.get("payment_intent_id") or None,
    )


def _base_url() -> str:
    import os

    return os.getenv("APP_BASE_URL", APP_BASE_URL_DEFAULT)


# ---------------------------------------------------------------------------
# Consent recording
# ---------------------------------------------------------------------------

class RecordConsentRequest(BaseModel):
    homeowner_email: str
    homeowner_auth_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None


@router.post("/documents/{quote_token}/record-consent")
async def record_consent(quote_token: str, req: RecordConsentRequest, request: Request):
    """Record pre-payment consent for a scope agreement.

    Hashes the rendered agreement HTML via :meth:`AgreementDoc.content_hash`
    and stores it alongside the IP, user_agent, and email so the record is
    dispute-defensible per eIDAS Simple Electronic Signature.
    """
    quote = await _get_quote(quote_token)
    contractor = await _get_contractor(quote.get("contractor_id", ""))

    payload = _quote_payload(quote, contractor)
    document_hash = AgreementDoc(payload).content_hash()

    ip_address = req.ip_address or (request.client.host if request.client else None)

    async with http_client(timeout=10) as client:
        ins_resp = await client.post(
            f"{sb_url()}/consents",
            json={
                "scope_token": quote_token,
                "user_id": req.homeowner_auth_id,
                "email": req.homeowner_email,
                "ip_address": ip_address,
                "user_agent": req.user_agent,
                "session_id": req.session_id,
                "document_version": "v1",
                "document_hash": document_hash,
            },
            headers=sb_headers(),
        )
    if ins_resp.status_code not in (200, 201):
        logger.error("Failed to record consent: %s", ins_resp.text)
        raise api_error(500, "Failed to record consent")

    consent_row = ins_resp.json()[0] if ins_resp.json() else {}
    consent_id = consent_row.get("id")

    patch: dict = {}
    if consent_id:
        patch["consent_id"] = consent_id
    if req.homeowner_auth_id:
        patch["homeowner_auth_id"] = req.homeowner_auth_id
    if req.homeowner_email:
        patch["homeowner_email"] = req.homeowner_email
    if patch:
        async with http_client(timeout=10) as client:
            await client.patch(
                f"{sb_url()}/quotes",
                params={"token": f"eq.{quote_token}"},
                json=patch,
                headers=sb_headers(),
            )

    logger.info(
        "Consent recorded | quote=%s consent=%s hash=%s...",
        quote_token[:8],
        consent_id,
        document_hash[:16],
    )
    return {"ok": True, "consent_id": consent_id, "document_hash": document_hash}


# ---------------------------------------------------------------------------
# Agreement document
# ---------------------------------------------------------------------------

@router.get("/documents/{quote_token}/agreement")
async def get_agreement(quote_token: str, format: str = "html"):
    """Render the construction agreement as HTML or PDF."""
    quote = await _get_quote(quote_token)
    contractor = await _get_contractor(quote.get("contractor_id", ""))
    doc = AgreementDoc(_quote_payload(quote, contractor))

    if format == "pdf":
        pdf_bytes = await doc.render_pdf(base_url=_base_url())
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{doc.filename(ext="pdf")}"'},
        )
    return HTMLResponse(content=doc.render_html())


# ---------------------------------------------------------------------------
# Invoice document
# ---------------------------------------------------------------------------

@router.get("/documents/{quote_token}/invoice")
async def get_invoice(quote_token: str, format: str = "html"):
    """Render the job invoice as HTML or PDF. Only valid when scope is complete."""
    quote = await _get_quote(quote_token)

    if quote.get("status") != "complete":
        raise api_error(400, "Invoice only available after job is complete")

    contractor = await _get_contractor(quote.get("contractor_id", ""))

    async with http_client(timeout=10) as client:
        mu_resp = await client.get(
            f"{sb_url()}/milestone_updates",
            params={"scope_token": f"eq.{quote_token}", "select": "milestone_index,released_at"},
            headers=sb_headers(),
        )
    milestone_updates = mu_resp.json() if mu_resp.status_code == 200 else []

    doc = InvoiceDoc(_invoice_payload(quote, contractor, milestone_updates))

    if format == "pdf":
        pdf_bytes = await doc.render_pdf(base_url=_base_url())
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{doc.filename(ext="pdf")}"'},
        )
    return HTMLResponse(content=doc.render_html())
