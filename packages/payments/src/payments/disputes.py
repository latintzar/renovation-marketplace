"""Payments-side of a product-level dispute.

A "product-level" dispute is opened by the homeowner when they are unhappy
with the work on a specific milestone. This package module owns the two
database mutations (milestone status → ``disputed``, disputes row insert);
the Chatwoot conversation is created by ``packages/messaging/support``.

Preserved invariants from the audit:

- Milestone must be ``proof_submitted`` or ``released`` to dispute.
- ``disputes`` row carries ``is_sandbox`` so operators can filter.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .errors import MilestoneNotReleasable, QuoteNotPayable
from .repo import DisputeRow, PaymentsRepo
from .sandbox import SandboxContext, resolve_for_quote


@dataclass(frozen=True)
class DisputeInput:
    reason: str
    photos: List[str]
    homeowner_name: str
    homeowner_phone: Optional[str] = None


@dataclass(frozen=True)
class DisputeResult:
    dispute_id: str
    token: str
    milestone_idx: int
    milestone_title: str
    contractor_id: str
    contractor_name: str
    contractor_phone: Optional[str]
    contractor_email: Optional[str]
    amount_cents: int
    sandbox: bool


async def open_dispute_state(
    *,
    repo: PaymentsRepo,
    ctx: SandboxContext,
    token: str,
    idx: int,
    input: DisputeInput,
) -> DisputeResult:
    quote = await repo.get_quote_by_token(token)
    if quote is None:
        raise QuoteNotPayable("Quote not found")

    if idx < 0 or idx >= len(quote.milestones):
        raise MilestoneNotReleasable(
            f"Milestone index {idx} out of bounds (len={len(quote.milestones)})"
        )
    milestone = quote.milestones[idx]

    allowed = {"proof_submitted", "released"}
    status = milestone.get("status")
    if status not in allowed:
        raise MilestoneNotReleasable(
            f"Milestone status '{status}' does not allow dispute (need one of {sorted(allowed)})"
        )

    effective_ctx = resolve_for_quote(quote.is_sandbox, ctx)

    now = datetime.now(timezone.utc).isoformat()
    dispute_row = await repo.insert_dispute(
        {
            "scope_token": token,
            "milestone_index": idx,
            "reason": input.reason,
            "photos": list(input.photos),
            "is_sandbox": effective_ctx.is_sandbox,
            "created_at": now,
        }
    )

    new_milestones: List[Dict[str, Any]] = []
    for i, m in enumerate(quote.milestones):
        if i == idx:
            updated = dict(m)
            updated["status"] = "disputed"
            new_milestones.append(updated)
        else:
            new_milestones.append(m)
    await repo.patch_quote(token, {"milestones": new_milestones})

    contractor = await repo.get_contractor(quote.contractor_id)

    return DisputeResult(
        dispute_id=dispute_row.id,
        token=token,
        milestone_idx=idx,
        milestone_title=str(milestone.get("description", "")),
        contractor_id=quote.contractor_id,
        contractor_name=contractor.name if contractor else "",
        contractor_phone=contractor.phone if contractor else None,
        contractor_email=contractor.email if contractor else None,
        amount_cents=int(milestone.get("amount_cents") or 0),
        sandbox=effective_ctx.is_sandbox,
    )


async def list_disputes(
    *,
    repo: PaymentsRepo,
    token: str,
) -> List[DisputeRow]:
    return await repo.list_disputes(token)


__all__ = [
    "DisputeInput",
    "DisputeResult",
    "open_dispute_state",
    "list_disputes",
]
