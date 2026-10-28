"""Stripe webhook verification + dispatcher.

**Tri-state signature verification**: a webhook payload arrives without any
indication of whether it came from the live or the test endpoint. We try the
live secret first, then the test secret. If both fail we raise
:class:`InvalidWebhookSignature`. The returned tuple carries the
``is_sandbox_event`` flag so downstream handlers know which DB mode to
patch.

**No module globals**: this module never mutates ``stripe.api_key``. The
:func:`verify_stripe_event` function talks to ``stripe.Webhook`` directly,
which is a pure signature-check helper that doesn't touch the network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from .errors import InvalidWebhookPayload, InvalidWebhookSignature
from .repo import PaymentsRepo


# ``stripe.Event`` is an ``attrdict``; we type it as ``Any`` so tests can
# drop in plain dicts.
StripeEvent = Any


# ----------------------------- result types -------------------------------

@dataclass(frozen=True)
class CheckoutCompletedResult:
    quote_token: Optional[str]
    variation_id: Optional[str]
    payment_intent_id: str
    amount_cents: int
    homeowner_email: str
    is_sandbox: bool
    patched: bool


@dataclass(frozen=True)
class AccountUpdatedResult:
    stripe_account_id: str
    contractor_id: Optional[str]
    onboarding_complete: bool


@dataclass(frozen=True)
class PaymentFailedResult:
    quote_token: str


@dataclass(frozen=True)
class ChargeRefundedResult:
    quote_token: Optional[str]
    payment_intent_id: str
    refund_id: str
    amount_refunded_cents: int


@dataclass(frozen=True)
class ChargeDisputeCreatedResult:
    quote_token: Optional[str]
    charge_id: str
    dispute_id: str
    reason: str


# --------------------------- signature verify -----------------------------

def verify_stripe_event(
    *,
    payload: bytes,
    signature: str,
    live_secret: str,
    test_secret: str,
) -> Tuple[StripeEvent, bool]:
    """Tri-state live/test verification.

    Returns ``(event, is_sandbox_event)``. Raises :class:`InvalidWebhookSignature`
    on both-fail, :class:`InvalidWebhookPayload` on JSON parse error.
    """

    try:
        import stripe  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise InvalidWebhookPayload("stripe SDK not installed") from exc

    last_exc: Optional[Exception] = None
    for secret, is_sandbox in ((live_secret, False), (test_secret, True)):
        if not secret:
            continue
        try:
            event = stripe.Webhook.construct_event(
                payload=payload, sig_header=signature, secret=secret
            )
            return event, is_sandbox
        except ValueError as exc:
            raise InvalidWebhookPayload(str(exc)) from exc
        except Exception as exc:
            last_exc = exc
            continue

    raise InvalidWebhookSignature(
        str(last_exc) if last_exc else "No webhook secret verified"
    )


# ----------------------------- dispatcher ---------------------------------

def _event_data(event: StripeEvent) -> Dict[str, Any]:
    data = getattr(event, "data", None)
    if data is None and isinstance(event, dict):
        data = event.get("data", {})
    obj = getattr(data, "object", None) if data is not None else None
    if obj is None and isinstance(data, dict):
        obj = data.get("object", {})
    if hasattr(obj, "to_dict"):
        try:
            obj = obj.to_dict()
        except Exception:  # pragma: no cover
            pass
    if isinstance(obj, dict):
        return obj
    return {}


def _event_type(event: StripeEvent) -> str:
    t = getattr(event, "type", None)
    if t is None and isinstance(event, dict):
        t = event.get("type")
    return t or ""


async def handle_checkout_completed(
    event: StripeEvent, *, is_sandbox: bool, repo: PaymentsRepo
) -> CheckoutCompletedResult:
    obj = _event_data(event)
    metadata = obj.get("metadata") or {}
    variation_id = metadata.get("variation_id")
    quote_token = metadata.get("quote_token")
    payment_intent_id = obj.get("payment_intent") or ""
    amount_cents = int(obj.get("amount_total") or 0)
    customer_details = obj.get("customer_details") or {}
    email = (
        customer_details.get("email")
        or obj.get("customer_email")
        or ""
    )
    homeowner_auth_id = metadata.get("homeowner_auth_id")

    patched = False
    if variation_id:
        await repo.mark_variation_paid(
            variation_id, payment_intent_id=payment_intent_id
        )
        patched = True
    elif quote_token:
        await repo.mark_quote_paid(
            quote_token,
            payment_intent_id=payment_intent_id,
            amount_total_cents=amount_cents,
            homeowner_email=email,
            homeowner_auth_id=homeowner_auth_id,
        )
        patched = True

    return CheckoutCompletedResult(
        quote_token=quote_token,
        variation_id=variation_id,
        payment_intent_id=payment_intent_id,
        amount_cents=amount_cents,
        homeowner_email=email,
        is_sandbox=is_sandbox,
        patched=patched,
    )


async def handle_account_updated(
    event: StripeEvent, *, is_sandbox: bool, repo: PaymentsRepo
) -> AccountUpdatedResult:
    obj = _event_data(event)
    account_id = obj.get("id") or ""
    charges_enabled = bool(obj.get("charges_enabled", False))
    payouts_enabled = bool(obj.get("payouts_enabled", False))
    details_submitted = bool(obj.get("details_submitted", False))
    onboarding_complete = charges_enabled and payouts_enabled and details_submitted

    contractor = await repo.find_contractor_by_stripe_account(account_id)
    contractor_id = contractor.id if contractor else None
    if contractor_id and onboarding_complete and not contractor.stripe_onboarding_complete:
        await repo.mark_onboarding_complete(contractor_id)

    return AccountUpdatedResult(
        stripe_account_id=account_id,
        contractor_id=contractor_id,
        onboarding_complete=onboarding_complete,
    )


async def handle_payment_failed(
    event: StripeEvent, *, is_sandbox: bool, repo: PaymentsRepo
) -> PaymentFailedResult:
    obj = _event_data(event)
    metadata = obj.get("metadata") or {}
    quote_token = metadata.get("quote_token", "")
    if quote_token:
        await repo.mark_quote_payment_failed(quote_token)
    return PaymentFailedResult(quote_token=quote_token)


async def handle_charge_refunded(
    event: StripeEvent, *, is_sandbox: bool, repo: PaymentsRepo
) -> ChargeRefundedResult:
    obj = _event_data(event)
    metadata = obj.get("metadata") or {}
    quote_token = metadata.get("quote_token")
    payment_intent_id = obj.get("payment_intent") or ""
    refund_amount = int(obj.get("amount_refunded") or 0)
    refunds = (obj.get("refunds") or {}).get("data") or []
    refund_id = refunds[0].get("id", "") if refunds else ""

    if quote_token:
        await repo.mark_quote_refunded(quote_token, reason="stripe:charge.refunded")

    return ChargeRefundedResult(
        quote_token=quote_token,
        payment_intent_id=payment_intent_id,
        refund_id=refund_id,
        amount_refunded_cents=refund_amount,
    )


async def handle_charge_dispute_created(
    event: StripeEvent, *, is_sandbox: bool, repo: PaymentsRepo
) -> ChargeDisputeCreatedResult:
    obj = _event_data(event)
    metadata = obj.get("metadata") or {}
    quote_token = metadata.get("quote_token")
    charge_id = obj.get("charge") or ""
    dispute_id = obj.get("id") or ""
    reason = obj.get("reason") or ""

    if quote_token:
        await repo.mark_quote_disputed(quote_token)

    return ChargeDisputeCreatedResult(
        quote_token=quote_token,
        charge_id=charge_id,
        dispute_id=dispute_id,
        reason=reason,
    )


_HANDLERS = {
    "checkout.session.completed": handle_checkout_completed,
    "account.updated": handle_account_updated,
    "payment_intent.payment_failed": handle_payment_failed,
    "charge.refunded": handle_charge_refunded,
    "charge.dispute.created": handle_charge_dispute_created,
}


async def dispatch_event(
    event: StripeEvent,
    *,
    is_sandbox: bool,
    repo: PaymentsRepo,
) -> Dict[str, Any]:
    event_type = _event_type(event)
    handler = _HANDLERS.get(event_type)
    if handler is None:
        return {"received": event_type, "handled": False}
    result = await handler(event, is_sandbox=is_sandbox, repo=repo)
    return {"received": event_type, "handled": True, "result": result}


__all__ = [
    "StripeEvent",
    "CheckoutCompletedResult",
    "AccountUpdatedResult",
    "PaymentFailedResult",
    "ChargeRefundedResult",
    "ChargeDisputeCreatedResult",
    "verify_stripe_event",
    "dispatch_event",
    "handle_checkout_completed",
    "handle_account_updated",
    "handle_payment_failed",
    "handle_charge_refunded",
    "handle_charge_dispute_created",
]
