"""Variation-order lifecycle — create, approve, decline.

Approve-time idempotency key::

    f"payments:variation-approve:{variation_id}"

Variation success URL: ``{app_base}/app/project/{token}?variation_paid=true``
— the SPA reads this query parameter to show the approved-banner (must be
preserved; the audit highlighted this).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .client import StripeClient
from .errors import (
    QuoteNotPayable,
    StripeCallFailed,
    VariationNotPending,
)
from .repo import PaymentsRepo
from .sandbox import SandboxContext


@dataclass(frozen=True)
class CreateVariationInput:
    amount_cents: int
    description: str
    photos: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class VariationCreateResult:
    variation_id: str
    token: str
    amount_cents: int
    contractor_name: str
    homeowner_auth_id: Optional[str]
    homeowner_phone: Optional[str]
    message: str


@dataclass(frozen=True)
class VariationApproveResult:
    variation_id: str
    checkout_url: str
    session_id: str
    token: str
    amount_cents: int
    sandbox: bool


@dataclass(frozen=True)
class VariationDeclineResult:
    variation_id: str
    token: str
    contractor_id: str
    contractor_phone: Optional[str]
    message: str


async def create_variation(
    *,
    repo: PaymentsRepo,
    ctx: SandboxContext,
    token: str,
    caller_contractor_id: str,
    caller_name: str,
    input: CreateVariationInput,
) -> VariationCreateResult:
    quote = await repo.get_quote_by_token(token)
    if quote is None:
        raise QuoteNotPayable("Quote not found")
    if quote.contractor_id != caller_contractor_id:
        raise VariationNotPending("Caller is not the contractor on this quote")
    if input.amount_cents <= 0:
        raise VariationNotPending("Variation amount must be positive")

    row = await repo.insert_variation(
        {
            "scope_token": token,
            "status": "pending",
            "amount_cents": input.amount_cents,
            "description": input.description,
            "photos": list(input.photos),
        }
    )

    return VariationCreateResult(
        variation_id=row.id,
        token=token,
        amount_cents=input.amount_cents,
        contractor_name=caller_name,
        homeowner_auth_id=quote.homeowner_auth_id,
        homeowner_phone=quote.homeowner_phone,
        message=input.description,
    )


async def approve_variation(
    *,
    client: StripeClient,
    repo: PaymentsRepo,
    ctx: SandboxContext,
    token: str,
    variation_id: str,
    app_base_url: str,
) -> VariationApproveResult:
    variation = await repo.get_variation(variation_id)
    if variation is None or variation.scope_token != token:
        raise VariationNotPending("Variation not found for this token")
    if variation.status != "pending":
        raise VariationNotPending(
            f"Variation status '{variation.status}' is not pending"
        )

    base = app_base_url.rstrip("/")
    success_url = f"{base}/app/project/{token}?variation_paid=true"
    cancel_url = f"{base}/app/project/{token}?variation_cancelled=true"

    line_items = [
        {
            "price_data": {
                "currency": "eur",
                "product_data": {
                    "name": f"Variation order for scope {token[:8]}",
                },
                "unit_amount": variation.amount_cents,
            },
            "quantity": 1,
        }
    ]

    metadata: Dict[str, Any] = {
        "quote_token": token,
        "variation_id": variation_id,
    }

    params: Dict[str, Any] = {
        "mode": "payment",
        "line_items": line_items,
        "metadata": metadata,
        "success_url": success_url,
        "cancel_url": cancel_url,
    }

    idempotency_key = f"payments:variation-approve:{variation_id}"
    try:
        session = client.checkout.sessions.create(
            params=params, options={"idempotency_key": idempotency_key}
        )
    except TypeError:
        session = client.checkout.sessions.create(
            **params, idempotency_key=idempotency_key
        )
    except Exception as exc:
        raise StripeCallFailed(
            f"Stripe variation checkout session create failed: {exc}"
        ) from exc

    session_id = getattr(session, "id", None) or session["id"]
    url = getattr(session, "url", None) or session["url"]

    await repo.patch_variation(variation_id, {"checkout_session_id": session_id})

    return VariationApproveResult(
        variation_id=variation_id,
        checkout_url=url,
        session_id=session_id,
        token=token,
        amount_cents=variation.amount_cents,
        sandbox=ctx.is_sandbox,
    )


async def decline_variation(
    *,
    repo: PaymentsRepo,
    ctx: SandboxContext,
    token: str,
    variation_id: str,
) -> VariationDeclineResult:
    variation = await repo.get_variation(variation_id)
    if variation is None or variation.scope_token != token:
        raise VariationNotPending("Variation not found for this token")
    if variation.status != "pending":
        raise VariationNotPending(
            f"Variation status '{variation.status}' is not pending"
        )

    quote = await repo.get_quote_by_token(token)
    if quote is None:
        raise VariationNotPending("Quote not found for this variation")

    await repo.patch_variation(variation_id, {"status": "declined"})

    contractor = await repo.get_contractor(quote.contractor_id)
    contractor_phone = contractor.phone if contractor else None

    return VariationDeclineResult(
        variation_id=variation_id,
        token=token,
        contractor_id=quote.contractor_id,
        contractor_phone=contractor_phone,
        message=variation.description,
    )


__all__ = [
    "CreateVariationInput",
    "VariationCreateResult",
    "VariationApproveResult",
    "VariationDeclineResult",
    "create_variation",
    "approve_variation",
    "decline_variation",
]
