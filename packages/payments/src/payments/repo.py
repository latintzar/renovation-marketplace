"""Supabase repository for every table payments touches.

Consolidates the raw-HTTP Supabase calls that used to live inline in six
route files. Every method takes a :class:`core.db.Supabase` instance and
returns strongly-typed :class:`dataclass` rows (not raw dicts).

Column-name rename: the database column ``stripe_fee_cents`` is exposed as
``leo_fee_cents`` on :class:`QuoteRow` (D12 in ``design.md`` — the column
name is legacy; the value is Leo's platform fee, not Stripe's processing
fee). Write-path ``patch_quote`` accepts either name transparently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.db import Supabase


# ------------------------------- row types ---------------------------------

@dataclass
class QuoteRow:
    token: str
    contractor_id: str
    homeowner_email: Optional[str]
    homeowner_auth_id: Optional[str]
    homeowner_phone: Optional[str]
    amount_total_cents: Optional[int]
    leo_fee_cents: Optional[int]
    materials_upfront_cents: Optional[int]
    iva_rate: Optional[float]
    payment_status: str
    checkout_session_id: Optional[str]
    checkout_session_attempt: int
    payment_intent_id: Optional[str]
    is_sandbox: bool
    milestones: List[Dict[str, Any]]
    status: str
    completed_at: Optional[str]
    consent_id: Optional[str]
    quote_data: Dict[str, Any]

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "QuoteRow":
        return cls(
            token=row.get("token", ""),
            contractor_id=row.get("contractor_id", ""),
            homeowner_email=row.get("homeowner_email"),
            homeowner_auth_id=row.get("homeowner_auth_id"),
            homeowner_phone=row.get("homeowner_phone"),
            amount_total_cents=row.get("amount_total_cents"),
            leo_fee_cents=row.get("stripe_fee_cents"),
            materials_upfront_cents=row.get("materials_upfront_cents"),
            iva_rate=row.get("iva_rate"),
            payment_status=row.get("payment_status", "unpaid"),
            checkout_session_id=row.get("checkout_session_id"),
            checkout_session_attempt=int(row.get("checkout_session_attempt") or 0),
            payment_intent_id=row.get("payment_intent_id"),
            is_sandbox=bool(row.get("is_sandbox", False)),
            milestones=list(row.get("milestones") or []),
            status=row.get("status", "draft"),
            completed_at=row.get("completed_at"),
            consent_id=row.get("consent_id"),
            quote_data=dict(row.get("quote_data") or {}),
        )


@dataclass
class ContractorRow:
    id: str
    name: str
    email: Optional[str]
    phone: Optional[str]
    stripe_account_id: Optional[str]
    stripe_onboarding_complete: bool

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "ContractorRow":
        return cls(
            id=row.get("id", ""),
            name=row.get("name", ""),
            email=row.get("email"),
            phone=row.get("phone"),
            stripe_account_id=row.get("stripe_account_id"),
            stripe_onboarding_complete=bool(row.get("stripe_onboarding_complete", False)),
        )


@dataclass
class MilestoneUpdateRow:
    id: str
    scope_token: str
    milestone_index: int
    status: str
    photos: Optional[List[str]] = None
    voice_url: Optional[str] = None
    note: Optional[str] = None
    stripe_transfer_id: Optional[str] = None
    released_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "MilestoneUpdateRow":
        return cls(
            id=row.get("id", ""),
            scope_token=row.get("scope_token", ""),
            milestone_index=int(row.get("milestone_index", 0)),
            status=row.get("status", "pending"),
            photos=list(row.get("photos") or []) if row.get("photos") is not None else None,
            voice_url=row.get("voice_url"),
            note=row.get("note"),
            stripe_transfer_id=row.get("stripe_transfer_id"),
            released_at=row.get("released_at"),
        )


@dataclass
class VariationRow:
    id: str
    scope_token: str
    status: str
    amount_cents: int
    description: str
    checkout_session_id: Optional[str] = None
    payment_intent_id: Optional[str] = None
    photos: List[str] = field(default_factory=list)

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "VariationRow":
        return cls(
            id=row.get("id", ""),
            scope_token=row.get("scope_token", ""),
            status=row.get("status", "pending"),
            amount_cents=int(row.get("amount_cents") or 0),
            description=row.get("description", ""),
            checkout_session_id=row.get("checkout_session_id"),
            payment_intent_id=row.get("payment_intent_id"),
            photos=list(row.get("photos") or []),
        )


@dataclass
class DisputeRow:
    id: str
    scope_token: str
    milestone_index: int
    reason: str
    photos: Optional[List[str]]
    chatwoot_conversation_id: Optional[int]
    is_sandbox: bool
    created_at: str

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "DisputeRow":
        return cls(
            id=row.get("id", ""),
            scope_token=row.get("scope_token", ""),
            milestone_index=int(row.get("milestone_index", 0)),
            reason=row.get("reason", ""),
            photos=list(row.get("photos") or []) if row.get("photos") is not None else None,
            chatwoot_conversation_id=row.get("chatwoot_conversation_id"),
            is_sandbox=bool(row.get("is_sandbox", False)),
            created_at=row.get("created_at", ""),
        )


def _rename_fee(patch: Dict[str, Any]) -> Dict[str, Any]:
    """Rename ``leo_fee_cents`` -> ``stripe_fee_cents`` at the DB boundary."""

    if "leo_fee_cents" in patch:
        out = dict(patch)
        out["stripe_fee_cents"] = out.pop("leo_fee_cents")
        return out
    return patch


# ------------------------------ repository ---------------------------------

class PaymentsRepo:
    """Thin typed wrapper over :class:`core.db.Supabase`."""

    def __init__(self, sb: Supabase) -> None:
        self._sb = sb

    # --- quotes ------------------------------------------------------------

    async def get_quote_by_token(self, token: str) -> Optional[QuoteRow]:
        rows = await self._sb.select(
            "quotes", filters={"token": f"eq.{token}"}, limit=1
        )
        return QuoteRow.from_row(rows[0]) if rows else None

    async def patch_quote(self, token: str, patch: Dict[str, Any]) -> None:
        await self._sb.update(
            "quotes",
            _rename_fee(patch),
            filters={"token": f"eq.{token}"},
            prefer=None,
        )

    async def record_checkout_session(
        self,
        token: str,
        *,
        session_id: str,
        homeowner_email: Optional[str],
        consent_id: Optional[str],
        is_sandbox: bool,
    ) -> None:
        patch: Dict[str, Any] = {
            "checkout_session_id": session_id,
            "payment_status": "pending",
            "is_sandbox": is_sandbox,
        }
        if homeowner_email is not None:
            patch["homeowner_email"] = homeowner_email
        if consent_id is not None:
            patch["consent_id"] = consent_id
        await self.patch_quote(token, patch)

    async def mark_quote_paid(
        self,
        token: str,
        *,
        payment_intent_id: str,
        amount_total_cents: int,
        homeowner_email: str,
        homeowner_auth_id: Optional[str],
    ) -> None:
        patch: Dict[str, Any] = {
            "payment_status": "paid",
            "payment_intent_id": payment_intent_id,
            "amount_total_cents": amount_total_cents,
            "homeowner_email": homeowner_email,
        }
        if homeowner_auth_id:
            patch["homeowner_auth_id"] = homeowner_auth_id
        await self.patch_quote(token, patch)

    async def mark_quote_payment_failed(self, token: str) -> None:
        await self.patch_quote(token, {"payment_status": "failed"})

    async def mark_quote_refunded(self, token: str, *, reason: str) -> None:
        await self.patch_quote(
            token,
            {
                "payment_status": "refunded",
                "status": "cancelled",
                "cancellation_reason": reason,
            },
        )

    async def mark_quote_disputed(self, token: str) -> None:
        await self.patch_quote(token, {"payment_status": "disputed"})

    # --- contractors -------------------------------------------------------

    async def get_contractor(self, contractor_id: str) -> Optional[ContractorRow]:
        rows = await self._sb.select(
            "contractors",
            filters={"id": f"eq.{contractor_id}"},
            limit=1,
        )
        return ContractorRow.from_row(rows[0]) if rows else None

    async def patch_contractor(self, contractor_id: str, patch: Dict[str, Any]) -> None:
        await self._sb.update(
            "contractors",
            patch,
            filters={"id": f"eq.{contractor_id}"},
            prefer=None,
        )

    async def find_contractor_by_stripe_account(
        self, stripe_account_id: str
    ) -> Optional[ContractorRow]:
        rows = await self._sb.select(
            "contractors",
            filters={"stripe_account_id": f"eq.{stripe_account_id}"},
            limit=1,
        )
        return ContractorRow.from_row(rows[0]) if rows else None

    async def record_account_created(
        self,
        contractor_id: str,
        *,
        stripe_account_id: str,
        sandbox: bool,
    ) -> None:
        patch: Dict[str, Any] = {"stripe_account_id": stripe_account_id}
        if sandbox:
            patch["stripe_onboarding_complete"] = True
        await self.patch_contractor(contractor_id, patch)

    async def mark_onboarding_complete(self, contractor_id: str) -> None:
        await self.patch_contractor(
            contractor_id, {"stripe_onboarding_complete": True}
        )

    # --- milestone_updates -------------------------------------------------

    async def insert_milestone_update(self, row: Dict[str, Any]) -> MilestoneUpdateRow:
        result = await self._sb.insert("milestone_updates", row)
        payload = result if isinstance(result, dict) else row
        return MilestoneUpdateRow.from_row(payload)

    async def mark_milestone_released(
        self,
        *,
        token: str,
        idx: int,
        transfer_id: str,
        released_at: str,
    ) -> None:
        await self._sb.update(
            "milestone_updates",
            {
                "status": "released",
                "stripe_transfer_id": transfer_id,
                "released_at": released_at,
            },
            filters={
                "scope_token": f"eq.{token}",
                "milestone_index": f"eq.{idx}",
            },
            prefer=None,
        )

    async def list_milestone_updates(self, token: str) -> List[MilestoneUpdateRow]:
        rows = await self._sb.select(
            "milestone_updates",
            filters={"scope_token": f"eq.{token}"},
        )
        return [MilestoneUpdateRow.from_row(r) for r in rows]

    # --- variation_orders --------------------------------------------------

    async def insert_variation(self, row: Dict[str, Any]) -> VariationRow:
        result = await self._sb.insert("variation_orders", row)
        payload = result if isinstance(result, dict) else row
        return VariationRow.from_row(payload)

    async def get_variation(self, variation_id: str) -> Optional[VariationRow]:
        rows = await self._sb.select(
            "variation_orders",
            filters={"id": f"eq.{variation_id}"},
            limit=1,
        )
        return VariationRow.from_row(rows[0]) if rows else None

    async def patch_variation(self, variation_id: str, patch: Dict[str, Any]) -> None:
        await self._sb.update(
            "variation_orders",
            patch,
            filters={"id": f"eq.{variation_id}"},
            prefer=None,
        )

    async def mark_variation_paid(
        self,
        variation_id: str,
        *,
        payment_intent_id: str,
    ) -> None:
        await self.patch_variation(
            variation_id,
            {"status": "approved", "payment_intent_id": payment_intent_id},
        )

    async def list_variations(self, token: str) -> List[VariationRow]:
        rows = await self._sb.select(
            "variation_orders",
            filters={"scope_token": f"eq.{token}"},
        )
        return [VariationRow.from_row(r) for r in rows]

    # --- cancellations -----------------------------------------------------

    async def insert_cancellation(self, row: Dict[str, Any]) -> Dict[str, Any]:
        result = await self._sb.insert("cancellations", row)
        if isinstance(result, dict):
            return result
        return row

    # --- disputes ----------------------------------------------------------

    async def insert_dispute(self, row: Dict[str, Any]) -> DisputeRow:
        result = await self._sb.insert("disputes", row)
        payload = result if isinstance(result, dict) else row
        return DisputeRow.from_row(payload)

    async def list_disputes(self, token: str) -> List[DisputeRow]:
        rows = await self._sb.select(
            "disputes", filters={"scope_token": f"eq.{token}"}
        )
        return [DisputeRow.from_row(r) for r in rows]


__all__ = [
    "PaymentsRepo",
    "QuoteRow",
    "ContractorRow",
    "MilestoneUpdateRow",
    "VariationRow",
    "DisputeRow",
]
