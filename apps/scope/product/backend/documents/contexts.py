"""Payload → Jinja-context dict builders (package-internal).

Replaces ``_build_agreement_context`` and ``_build_invoice_context`` at
``routes/documents.py:105-206``. The public surface is the ``*Doc``
classes in ``agreements.py`` / ``invoices.py`` / ``variations.py``; the
templates never see raw Supabase rows, only typed payloads.

No money arithmetic lives here: :class:`domain.money.Money` carries
``.euros`` for template display and canonical multiply/add semantics.
"""

from __future__ import annotations

from typing import Any, Dict

from core.money import iva_amount_percent

from .consent import (
    DOCUMENT_VERSION_AGREEMENT,
    DOCUMENT_VERSION_INVOICE,
    DOCUMENT_VERSION_VARIATION,
)
from .dates import format_date_es
from .payloads import InvoicePayload, Money, QuotePayload, VariationPayload

__all__ = [
    "build_agreement_context",
    "build_invoice_context",
    "build_variation_context",
]


def _milestone_dict(m: Any) -> Dict[str, Any]:
    released = m.released_at.isoformat() if m.released_at else ""
    released_display = format_date_es(m.released_at) if m.released_at else ""
    return {
        "title": m.title,
        "amount_cents": m.amount.cents,
        "amount_eur": m.amount.euros,
        "released_at": released_display,
        "released_at_iso": released,
    }


def build_agreement_context(payload: QuotePayload) -> Dict[str, Any]:
    """Return the Jinja context dict for the agreement template.

    The context is a flat dict keyed by names the template uses
    (``quote_token``, ``milestones``, ``total_amount_eur``, …). All
    monetary values come from :class:`domain.money.Money`.
    """

    return {
        "quote_token": payload.quote_token,
        "document_version": DOCUMENT_VERSION_AGREEMENT,
        "agreement_date": format_date_es(payload.agreement_date),
        "homeowner_name": payload.homeowner.name,
        "homeowner_email": payload.homeowner.email,
        "contractor_name": payload.contractor.name,
        "contractor_trade": payload.contractor.trade or "",
        "contractor_address": payload.contractor.address or "",
        "job_title": payload.job.title,
        "job_address": payload.job.address,
        "job_description": payload.job.description or "",
        "milestones": [_milestone_dict(m) for m in payload.milestones],
        "total_amount_eur": payload.total.euros,
        "leo_fee_eur": payload.leo_fee.euros,
        "materials_upfront_eur": payload.materials_upfront.euros,
    }


def build_invoice_context(payload: InvoicePayload) -> Dict[str, Any]:
    """Return the Jinja context dict for the invoice template.

    IVA is computed via :func:`domain.money.iva_amount` (D1). The
    ``work_subtotal`` = ``total - leo_fee`` convention preserved from
    the legacy handler.
    """

    work_subtotal = payload.total - payload.leo_fee
    if payload.iva_rate_pct:
        iva = Money.from_euros(
            iva_amount_percent(work_subtotal.euros, payload.iva_rate_pct)
        )
    else:
        iva = Money.from_cents(0)
    return {
        "quote_token": payload.quote_token,
        "document_version": DOCUMENT_VERSION_INVOICE,
        "completion_date": format_date_es(payload.completion_date),
        "homeowner_email": payload.homeowner.email,
        "contractor_name": payload.contractor.name,
        "contractor_trade": payload.contractor.trade or "",
        "job_title": payload.job.title,
        "job_address": payload.job.address,
        "milestones": [_milestone_dict(m) for m in payload.milestones],
        "materials_upfront_cents": payload.materials_upfront.cents,
        "work_subtotal_eur": work_subtotal.euros,
        "leo_fee_eur": payload.leo_fee.euros,
        "iva_eur": iva.euros,
        "iva_rate": payload.iva_rate_pct,
        "total_charged_eur": payload.total.euros,
        "payment_intent_id": payload.payment_intent_id or "",
    }


def build_variation_context(payload: VariationPayload) -> Dict[str, Any]:
    """Return the Jinja context dict for the variation template (stub)."""

    return {
        "quote_token": payload.quote_token,
        "document_version": DOCUMENT_VERSION_VARIATION,
        "variation_id": payload.variation_id,
        "variation_date": format_date_es(payload.variation_date),
        "homeowner_name": payload.homeowner.name,
        "homeowner_email": payload.homeowner.email,
        "contractor_name": payload.contractor.name,
        "contractor_trade": payload.contractor.trade or "",
        "job_title": payload.job.title,
        "job_address": payload.job.address,
        "change_summary": payload.change_summary,
        "milestones_delta": [_milestone_dict(m) for m in payload.milestones_delta],
        "delta_total_eur": payload.delta_total.euros,
    }
