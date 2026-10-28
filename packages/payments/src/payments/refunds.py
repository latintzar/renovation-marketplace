"""Project cancellation + refund via ``stripe.Refund.create``.

Guard rules preserved from ``routes/milestone.py::cancel_job`` and
``routes/projects.py::cancel_project``:

- Project must have ``payment_status == 'paid'`` (you cannot cancel an
  unpaid quote — there is nothing to refund).
- No milestone may be past ``pending`` when the cancellation is initiated
  by ``homeowner`` or ``contractor`` (the "no work started" invariant).
  ``admin`` actors bypass this check.
- Idempotency key::

      f"payments:refund:{quote_token}"

  On replay the returned ``refund_id`` is read from the original refund
  via ``refund.retrieve`` — callers see ``idempotent_duplicate=True``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

from .client import StripeClient
from .errors import (
    QuoteNotPayable,
    RefundNotAllowed,
    StripeCallFailed,
)
from .repo import PaymentsRepo, QuoteRow
from .sandbox import SandboxContext, resolve_for_quote


@dataclass(frozen=True)
class CancelInput:
    reason: str
    initiator_role: Literal["homeowner", "contractor", "admin"]
    amount_cents: Optional[int] = None


@dataclass(frozen=True)
class CancelProjectResult:
    token: str
    refund_id: str
    amount_refunded_cents: int
    reason: str
    initiator_role: str
    idempotent_duplicate: bool


def _guard_no_work_started(quote: QuoteRow, *, role: str) -> None:
    if role == "admin":
        return
    for m in quote.milestones:
        status = m.get("status", "pending")
        if status not in ("pending",):
            raise RefundNotAllowed(
                f"Cannot cancel — milestone index {m.get('index')} is '{status}'"
            )


async def cancel_project(
    *,
    client: StripeClient,
    repo: PaymentsRepo,
    ctx: SandboxContext,
    token: str,
    input: CancelInput,
) -> CancelProjectResult:
    quote = await repo.get_quote_by_token(token)
    if quote is None:
        raise QuoteNotPayable("Quote not found")
    if quote.payment_status != "paid":
        raise RefundNotAllowed(
            f"Quote payment_status '{quote.payment_status}' is not refundable"
        )
    if not quote.payment_intent_id:
        raise RefundNotAllowed("Quote has no Stripe payment_intent_id to refund")

    _guard_no_work_started(quote, role=input.initiator_role)

    effective_ctx = resolve_for_quote(quote.is_sandbox, ctx)

    refund_amount = input.amount_cents or quote.amount_total_cents
    if not refund_amount or refund_amount <= 0:
        raise RefundNotAllowed("Cannot determine refund amount")

    params: Dict[str, Any] = {
        "payment_intent": quote.payment_intent_id,
        "amount": refund_amount,
        "reason": "requested_by_customer",
        "metadata": {
            "quote_token": token,
            "reason": input.reason[:500],
            "initiator_role": input.initiator_role,
        },
    }

    idempotency_key = f"payments:refund:{token}"

    idempotent_duplicate = False
    refund_id: str = ""
    refunded_amount: int = refund_amount
    try:
        refund = _refund_create(
            client, params=params, idempotency_key=idempotency_key
        )
        refund_id = getattr(refund, "id", None) or refund["id"]
        refunded_amount = int(
            getattr(refund, "amount", None)
            or (refund.get("amount") if isinstance(refund, dict) else refund_amount)
        )
    except _IdempotencyError:
        idempotent_duplicate = True
        refund_id = _reconcile_refund(
            client,
            payment_intent=quote.payment_intent_id,
        )
        if not refund_id:
            raise StripeCallFailed(
                "Idempotency replayed but refund not found"
            )
    except Exception as exc:
        raise StripeCallFailed(f"Stripe refunds.create failed: {exc}") from exc

    await repo.insert_cancellation(
        {
            "scope_token": token,
            "reason": input.reason,
            "initiator_role": input.initiator_role,
            "amount_cents": refunded_amount,
            "stripe_refund_id": refund_id,
        }
    )
    await repo.mark_quote_refunded(token, reason=input.reason)

    return CancelProjectResult(
        token=token,
        refund_id=refund_id,
        amount_refunded_cents=refunded_amount,
        reason=input.reason,
        initiator_role=input.initiator_role,
        idempotent_duplicate=idempotent_duplicate,
    )


# ------------------ Stripe idempotency plumbing ---------------------------


class _IdempotencyError(Exception):
    pass


def _refund_create(
    client: StripeClient, *, params: Dict[str, Any], idempotency_key: str
) -> Any:
    try:
        return client.refunds.create(
            params=params, options={"idempotency_key": idempotency_key}
        )
    except TypeError:
        pass
    except Exception as exc:
        if exc.__class__.__name__ == "IdempotencyError" or "idempot" in str(exc).lower():
            raise _IdempotencyError(str(exc)) from exc
        raise
    try:
        return client.refunds.create(**params, idempotency_key=idempotency_key)
    except Exception as exc:
        if exc.__class__.__name__ == "IdempotencyError" or "idempot" in str(exc).lower():
            raise _IdempotencyError(str(exc)) from exc
        raise


def _reconcile_refund(client: StripeClient, *, payment_intent: str) -> str:
    try:
        listing = client.refunds.list(params={"payment_intent": payment_intent})
    except TypeError:
        listing = client.refunds.list(payment_intent=payment_intent)
    except Exception:  # pragma: no cover
        return ""

    items = getattr(listing, "data", None)
    if items is None and isinstance(listing, dict):
        items = listing.get("data", [])
    if not items:
        return ""

    first = items[0]
    return getattr(first, "id", None) or first.get("id", "")


__all__ = [
    "CancelInput",
    "CancelProjectResult",
    "cancel_project",
]
