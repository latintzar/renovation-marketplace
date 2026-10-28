"""Homeowner escrow checkout — Stripe Checkout Session create/reuse.

**Escrow invariant**: no ``payment_intent_data.transfer_data.destination`` in
the Session arguments. Funds hold in Leo's platform account; each milestone
later triggers a separate ``Transfer.create`` to the contractor's Express
account. This is the whole reason the package exists.

**Idempotency key**::

    f"payments:checkout:{quote_token}:{checkout_session_attempt}"

The pre-PATCH bumps ``checkout_session_attempt`` before the Stripe call, so
a retry after a 500 gets a fresh key — matching the on-disk invariants
called out in the audit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .client import StripeClient
from .errors import (
    ContractorKycIncomplete,
    ContractorNoStripeAccount,
    QuoteAlreadyPaid,
    QuoteNotPayable,
    StripeCallFailed,
)
from .finance import compute_quote_financials
from .repo import ContractorRow, PaymentsRepo, QuoteRow
from .sandbox import SandboxContext


@dataclass(frozen=True)
class CheckoutInput:
    quote_token: str
    homeowner_email: Optional[str]
    consent_id: Optional[str]
    app_base_url: str


@dataclass(frozen=True)
class CheckoutResult:
    url: str
    session_id: str
    reused: bool
    sandbox: bool


async def assert_can_accept(
    contractor: ContractorRow,
    *,
    sandbox: bool,
) -> None:
    """Raise if this contractor cannot accept a homeowner payment.

    Under ``sandbox=True`` both checks are bypassed — the sandbox flow pays
    into a test-mode account with no real KYC.
    """

    if sandbox:
        return
    if not contractor.stripe_account_id:
        raise ContractorNoStripeAccount(
            "Contractor has no Stripe Express account connected"
        )
    if not contractor.stripe_onboarding_complete:
        raise ContractorKycIncomplete("Contractor KYC has not completed")


async def maybe_reuse_open_session(
    *,
    client: StripeClient,
    existing_session_id: str,
) -> Optional[str]:
    """If the Stripe Checkout Session with this id is still ``open``, return
    its URL. Otherwise return ``None`` (caller creates a new session)."""

    try:
        session = client.checkout.sessions.retrieve(existing_session_id)
    except Exception:
        return None

    status = getattr(session, "status", None) or (
        session.get("status") if isinstance(session, dict) else None
    )
    if status != "open":
        return None

    url = getattr(session, "url", None) or (
        session.get("url") if isinstance(session, dict) else None
    )
    return url


def _amount_total_cents(quote: QuoteRow) -> int:
    """Read pre-computed ``amount_total_cents`` or fall back to the legacy
    in-process computation for pre-``finance`` rows."""

    if quote.amount_total_cents:
        return quote.amount_total_cents
    financials = compute_quote_financials(quote.quote_data)
    return financials.amount_total_cents


async def create_session(
    *,
    client: StripeClient,
    repo: PaymentsRepo,
    ctx: SandboxContext,
    input: CheckoutInput,
) -> CheckoutResult:
    """Create (or reuse) the homeowner escrow Stripe Checkout Session."""

    quote = await repo.get_quote_by_token(input.quote_token)
    if quote is None:
        raise QuoteNotPayable("Quote not found")

    if quote.payment_status == "paid":
        raise QuoteAlreadyPaid("Scope is already paid")

    if quote.payment_status == "pending" and quote.checkout_session_id:
        existing_url = await maybe_reuse_open_session(
            client=client, existing_session_id=quote.checkout_session_id
        )
        if existing_url:
            return CheckoutResult(
                url=existing_url,
                session_id=quote.checkout_session_id,
                reused=True,
                sandbox=ctx.is_sandbox,
            )

    contractor = await repo.get_contractor(quote.contractor_id)
    if contractor is None:
        raise QuoteNotPayable("Contractor not found")
    await assert_can_accept(contractor, sandbox=ctx.is_sandbox)

    amount_cents = _amount_total_cents(quote)
    if amount_cents <= 0:
        raise QuoteNotPayable("Quote has a zero or negative total")

    next_attempt = (quote.checkout_session_attempt or 0) + 1
    await repo.patch_quote(
        input.quote_token,
        {
            "payment_status": "pending",
            "checkout_session_attempt": next_attempt,
        },
    )

    idempotency_key = f"payments:checkout:{input.quote_token}:{next_attempt}"

    base = input.app_base_url.rstrip("/")
    success_url = f"{base}/app/canvas/{input.quote_token}?paid=true"
    cancel_url = f"{base}/app/canvas/{input.quote_token}"

    line_items = [
        {
            "price_data": {
                "currency": "eur",
                "product_data": {"name": f"Scope {input.quote_token[:8]}"},
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        }
    ]

    metadata: Dict[str, Any] = {
        "quote_token": input.quote_token,
        "contractor_id": quote.contractor_id,
    }
    if input.consent_id:
        metadata["consent_id"] = input.consent_id

    session_kwargs: Dict[str, Any] = {
        "mode": "payment",
        "line_items": line_items,
        "metadata": metadata,
        "success_url": success_url,
        "cancel_url": cancel_url,
    }
    if input.homeowner_email:
        session_kwargs["customer_email"] = input.homeowner_email

    try:
        session = client.checkout.sessions.create(
            params=session_kwargs,
            options={"idempotency_key": idempotency_key},
        )
    except TypeError:
        session = client.checkout.sessions.create(
            **session_kwargs, idempotency_key=idempotency_key
        )
    except Exception as exc:
        raise StripeCallFailed(f"Stripe checkout.sessions.create failed: {exc}") from exc

    session_id = getattr(session, "id", None) or session["id"]
    url = getattr(session, "url", None) or session["url"]

    await repo.record_checkout_session(
        input.quote_token,
        session_id=session_id,
        homeowner_email=input.homeowner_email,
        consent_id=input.consent_id,
        is_sandbox=ctx.is_sandbox,
    )

    return CheckoutResult(
        url=url,
        session_id=session_id,
        reused=False,
        sandbox=ctx.is_sandbox,
    )


__all__ = [
    "CheckoutInput",
    "CheckoutResult",
    "create_session",
    "maybe_reuse_open_session",
    "assert_can_accept",
]
