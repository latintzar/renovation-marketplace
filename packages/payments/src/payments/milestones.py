"""Milestone proof submission + escrow release.

Release idempotency key::

    f"payments:release:{quote_token}:{milestone_index}"

On :class:`stripe.error.IdempotencyError`, the real ``transfer_id`` is
reconciled via ``transfer_group`` lookup rather than surfacing the
``idempotent-duplicate`` sentinel that the legacy route leaked to the UI
(D9 in ``design.md``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .client import StripeClient
from .errors import (
    MilestoneAlreadyReleased,
    MilestoneNotReleasable,
    QuoteNotPayable,
    StripeCallFailed,
)
from .repo import PaymentsRepo, QuoteRow
from .sandbox import SandboxContext, resolve_for_quote


# ------------------------------- I/O types --------------------------------

@dataclass(frozen=True)
class ProofInput:
    photos: List[str]
    voice_url: Optional[str] = None
    note: Optional[str] = None


@dataclass(frozen=True)
class SubmitProofResult:
    token: str
    idx: int
    milestone_title: str
    project_auto_started: bool
    homeowner_auth_id: Optional[str]
    homeowner_phone: Optional[str]
    contractor_name: str
    message: str


@dataclass(frozen=True)
class ReleaseResult:
    token: str
    idx: int
    transfer_id: str
    idempotent_duplicate: bool
    amount_cents: int
    milestone_title: str
    all_released: bool
    completed_at: Optional[str]
    contractor_id: str
    contractor_name: str
    contractor_phone: Optional[str]
    contractor_stripe_account: str
    homeowner_auth_id: Optional[str]
    homeowner_phone: Optional[str]
    homeowner_email: Optional[str]
    sandbox: bool


# ------------------------------ helpers -----------------------------------

def _get_milestone(quote: QuoteRow, idx: int) -> Dict[str, Any]:
    if idx < 0 or idx >= len(quote.milestones):
        raise MilestoneNotReleasable(
            f"Milestone index {idx} out of bounds (len={len(quote.milestones)})"
        )
    return quote.milestones[idx]


def _advance_milestone_status(
    milestones: List[Dict[str, Any]],
    idx: int,
    *,
    new_status: str,
) -> List[Dict[str, Any]]:
    """Return a new list with ``milestones[idx].status = new_status`` and a
    ``released_at``/``marked_complete_at`` timestamp stamped as appropriate."""

    now = datetime.now(timezone.utc).isoformat()
    out: List[Dict[str, Any]] = []
    for i, m in enumerate(milestones):
        if i != idx:
            out.append(m)
            continue
        updated = dict(m)
        updated["status"] = new_status
        if new_status == "proof_submitted":
            updated["marked_complete_at"] = now
        elif new_status == "released":
            updated["released_at"] = now
        out.append(updated)
    return out


# ------------------------------- actions ----------------------------------

async def submit_proof(
    *,
    repo: PaymentsRepo,
    ctx: SandboxContext,
    token: str,
    idx: int,
    caller_contractor_id: str,
    caller_name: str,
    proof: ProofInput,
) -> SubmitProofResult:
    """Contractor submits proof of work on a milestone."""

    quote = await repo.get_quote_by_token(token)
    if quote is None:
        raise QuoteNotPayable("Quote not found")
    if quote.contractor_id != caller_contractor_id:
        raise MilestoneNotReleasable("Caller is not the contractor on this quote")
    if quote.payment_status not in ("paid", "in_progress"):
        raise MilestoneNotReleasable(
            f"Quote payment_status '{quote.payment_status}' does not allow proof submission"
        )

    milestone = _get_milestone(quote, idx)
    if milestone.get("status") != "pending":
        raise MilestoneNotReleasable(
            f"Milestone status is '{milestone.get('status')}' (expected 'pending')"
        )

    await repo.insert_milestone_update(
        {
            "scope_token": token,
            "milestone_index": idx,
            "status": "proof_submitted",
            "photos": list(proof.photos),
            "voice_url": proof.voice_url,
            "note": proof.note,
        }
    )

    new_milestones = _advance_milestone_status(
        quote.milestones, idx, new_status="proof_submitted"
    )
    patch: Dict[str, Any] = {"milestones": new_milestones}

    project_auto_started = False
    if quote.status == "paid":
        patch["status"] = "in_progress"
        project_auto_started = True

    await repo.patch_quote(token, patch)

    return SubmitProofResult(
        token=token,
        idx=idx,
        milestone_title=str(milestone.get("description", "")),
        project_auto_started=project_auto_started,
        homeowner_auth_id=quote.homeowner_auth_id,
        homeowner_phone=quote.homeowner_phone,
        contractor_name=caller_name,
        message=proof.note or "",
    )


async def release(
    *,
    client: StripeClient,
    repo: PaymentsRepo,
    ctx: SandboxContext,
    token: str,
    idx: int,
    caller_homeowner_auth_id: Optional[str] = None,
) -> ReleaseResult:
    """Homeowner releases funds for a milestone from escrow to the contractor."""

    quote = await repo.get_quote_by_token(token)
    if quote is None:
        raise QuoteNotPayable("Quote not found")
    if (
        caller_homeowner_auth_id
        and quote.homeowner_auth_id
        and caller_homeowner_auth_id != quote.homeowner_auth_id
    ):
        raise MilestoneNotReleasable("Caller does not own this quote")

    milestone = _get_milestone(quote, idx)
    status = milestone.get("status")
    if status == "released":
        raise MilestoneAlreadyReleased(f"Milestone {idx} already released")
    if status != "proof_submitted":
        raise MilestoneNotReleasable(
            f"Milestone status '{status}' (expected 'proof_submitted')"
        )

    contractor = await repo.get_contractor(quote.contractor_id)
    if contractor is None or not contractor.stripe_account_id:
        raise MilestoneNotReleasable(
            "Contractor has no Stripe Connect account for payout"
        )

    effective_ctx = resolve_for_quote(quote.is_sandbox, ctx)

    amount_cents = int(milestone.get("amount_cents") or 0)
    if amount_cents <= 0:
        raise MilestoneNotReleasable(
            f"Milestone {idx} has no positive amount_cents"
        )

    idempotency_key = f"payments:release:{token}:{idx}"
    transfer_group = f"quote:{token}"

    transfer_params: Dict[str, Any] = {
        "amount": amount_cents,
        "currency": "eur",
        "destination": contractor.stripe_account_id,
        "transfer_group": transfer_group,
        "metadata": {
            "quote_token": token,
            "milestone_index": str(idx),
        },
    }

    idempotent_duplicate = False
    transfer_id: str = ""
    try:
        transfer = _stripe_call(
            client.transfers.create,
            transfer_params,
            idempotency_key=idempotency_key,
        )
        transfer_id = getattr(transfer, "id", None) or transfer["id"]
    except _IdempotencyError as exc:
        idempotent_duplicate = True
        transfer_id = _reconcile_transfer_id(
            client, transfer_group=transfer_group, fallback_amount=amount_cents
        )
        if not transfer_id:
            raise StripeCallFailed(
                "Idempotency replayed but transfer not found"
            ) from exc
    except Exception as exc:
        raise StripeCallFailed(f"Stripe transfers.create failed: {exc}") from exc

    released_at = datetime.now(timezone.utc).isoformat()
    await repo.mark_milestone_released(
        token=token, idx=idx, transfer_id=transfer_id, released_at=released_at
    )

    new_milestones = _advance_milestone_status(
        quote.milestones, idx, new_status="released"
    )
    all_released = all(m.get("status") == "released" for m in new_milestones)

    patch: Dict[str, Any] = {"milestones": new_milestones}
    completed_at: Optional[str] = None
    if all_released:
        completed_at = released_at
        patch["status"] = "complete"
        patch["completed_at"] = completed_at
    await repo.patch_quote(token, patch)

    return ReleaseResult(
        token=token,
        idx=idx,
        transfer_id=transfer_id,
        idempotent_duplicate=idempotent_duplicate,
        amount_cents=amount_cents,
        milestone_title=str(milestone.get("description", "")),
        all_released=all_released,
        completed_at=completed_at,
        contractor_id=contractor.id,
        contractor_name=contractor.name,
        contractor_phone=contractor.phone,
        contractor_stripe_account=contractor.stripe_account_id,
        homeowner_auth_id=quote.homeowner_auth_id,
        homeowner_phone=quote.homeowner_phone,
        homeowner_email=quote.homeowner_email,
        sandbox=effective_ctx.is_sandbox,
    )


# ---------------------- Stripe idempotency plumbing -----------------------

class _IdempotencyError(Exception):
    """Internal sentinel used to detect a replayed idempotency key."""


def _stripe_call(fn: Any, params: Dict[str, Any], *, idempotency_key: str) -> Any:
    """Invoke a Stripe client method with an idempotency key, mapping the
    SDK's ``IdempotencyError`` to our internal sentinel."""

    try:
        return fn(params=params, options={"idempotency_key": idempotency_key})
    except TypeError:
        pass
    except Exception as exc:
        if _is_idempotency_error(exc):
            raise _IdempotencyError(str(exc)) from exc
        raise
    try:
        return fn(**params, idempotency_key=idempotency_key)
    except Exception as exc:
        if _is_idempotency_error(exc):
            raise _IdempotencyError(str(exc)) from exc
        raise


def _is_idempotency_error(exc: Exception) -> bool:
    klass = exc.__class__.__name__
    if klass == "IdempotencyError":
        return True
    if "idempot" in str(exc).lower():
        return True
    return False


def _reconcile_transfer_id(
    client: StripeClient,
    *,
    transfer_group: str,
    fallback_amount: int,
) -> str:
    """Look up the original ``transfer_id`` via ``transfer_group`` so callers
    never receive the ``'idempotent-duplicate'`` sentinel."""

    try:
        listing = client.transfers.list(params={"transfer_group": transfer_group})
    except TypeError:
        listing = client.transfers.list(transfer_group=transfer_group)
    except Exception:  # pragma: no cover - lookup failure
        return ""

    items = getattr(listing, "data", None)
    if items is None and isinstance(listing, dict):
        items = listing.get("data", [])
    items = items or []

    for item in items:
        amount = getattr(item, "amount", None)
        if amount is None and isinstance(item, dict):
            amount = item.get("amount")
        if amount == fallback_amount:
            return getattr(item, "id", None) or item.get("id", "")
    if items:
        first = items[0]
        return getattr(first, "id", None) or first.get("id", "")
    return ""


__all__ = [
    "ProofInput",
    "SubmitProofResult",
    "ReleaseResult",
    "submit_proof",
    "release",
]
