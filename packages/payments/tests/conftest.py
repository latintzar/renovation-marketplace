"""Shared fixtures for `payments` unit tests.

Provides a ``FakeStripeClient`` matching the :class:`payments.StripeClient`
Protocol and an in-memory ``FakeSupabase`` matching the subset of
:class:`core.db.Supabase` the repo uses. No network, no real Stripe SDK
calls.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import pytest

from payments import SandboxContext
from payments.repo import PaymentsRepo


# ----------------------------- Fake Stripe --------------------------------


class _Namespace:
    """Callable/attribute namespace matching a Stripe client resource."""

    def __init__(self, **methods: Any) -> None:
        for name, fn in methods.items():
            setattr(self, name, fn)


class CheckoutSessionsAPI:
    def __init__(self) -> None:
        self.created_calls: List[Dict[str, Any]] = []
        self.retrieved_ids: List[str] = []
        self.next_session_id = "cs_test_123"
        self.next_session_url = "https://checkout.stripe.com/c/cs_test_123"
        self.retrieve_status = "open"
        self.raise_on_create: Optional[Exception] = None

    def create(self, params: Optional[Dict[str, Any]] = None, options: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        payload = dict(params or {})
        payload.update(kwargs)
        opts = dict(options or {})
        if "idempotency_key" in payload:
            opts["idempotency_key"] = payload.pop("idempotency_key")
        self.created_calls.append({"params": payload, "options": opts})
        if self.raise_on_create:
            raise self.raise_on_create
        return {"id": self.next_session_id, "url": self.next_session_url, "status": "open"}

    def retrieve(self, session_id: str) -> Dict[str, Any]:
        self.retrieved_ids.append(session_id)
        return {"id": session_id, "url": f"https://checkout.stripe.com/c/{session_id}", "status": self.retrieve_status}


class TransfersAPI:
    def __init__(self) -> None:
        self.created_calls: List[Dict[str, Any]] = []
        self.listings: Dict[str, List[Dict[str, Any]]] = {}
        self.next_transfer_id = "tr_test_abc"
        self.raise_on_create: Optional[Exception] = None

    def create(self, params: Optional[Dict[str, Any]] = None, options: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        payload = dict(params or {})
        payload.update(kwargs)
        opts = dict(options or {})
        if "idempotency_key" in payload:
            opts["idempotency_key"] = payload.pop("idempotency_key")
        self.created_calls.append({"params": payload, "options": opts})
        if self.raise_on_create:
            raise self.raise_on_create
        return {"id": self.next_transfer_id, "amount": payload.get("amount", 0)}

    def list(self, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        payload = dict(params or {})
        payload.update(kwargs)
        group = payload.get("transfer_group", "")
        return {"data": self.listings.get(group, [])}


class RefundsAPI:
    def __init__(self) -> None:
        self.created_calls: List[Dict[str, Any]] = []
        self.listings: Dict[str, List[Dict[str, Any]]] = {}
        self.next_refund_id = "re_test_xyz"
        self.raise_on_create: Optional[Exception] = None

    def create(self, params: Optional[Dict[str, Any]] = None, options: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        payload = dict(params or {})
        payload.update(kwargs)
        opts = dict(options or {})
        if "idempotency_key" in payload:
            opts["idempotency_key"] = payload.pop("idempotency_key")
        self.created_calls.append({"params": payload, "options": opts})
        if self.raise_on_create:
            raise self.raise_on_create
        return {"id": self.next_refund_id, "amount": payload.get("amount", 0)}

    def list(self, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        payload = dict(params or {})
        payload.update(kwargs)
        pi = payload.get("payment_intent", "")
        return {"data": self.listings.get(pi, [])}


class AccountsAPI:
    def __init__(self) -> None:
        self.created: List[Dict[str, Any]] = []
        self.retrieved_ids: List[str] = []
        self.next_account_id = "acct_test_1"
        self.retrieve_payload: Dict[str, Any] = {
            "id": "acct_test_1",
            "charges_enabled": True,
            "payouts_enabled": True,
            "details_submitted": True,
            "requirements": {},
        }

    def create(self, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        payload = dict(params or {})
        payload.update(kwargs)
        self.created.append(payload)
        return {"id": self.next_account_id}

    def retrieve(self, account_id: str) -> Dict[str, Any]:
        self.retrieved_ids.append(account_id)
        return dict(self.retrieve_payload)


class AccountLinksAPI:
    def __init__(self) -> None:
        self.created: List[Dict[str, Any]] = []

    def create(self, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        payload = dict(params or {})
        payload.update(kwargs)
        self.created.append(payload)
        return {"url": "https://connect.stripe.com/setup/abc", "expires_at": 9999999999}


class FakeStripeClient:
    """Minimal drop-in for the :class:`payments.StripeClient` Protocol."""

    def __init__(self) -> None:
        self.checkout = _Namespace(sessions=CheckoutSessionsAPI())
        self.transfers = TransfersAPI()
        self.refunds = RefundsAPI()
        self.accounts = AccountsAPI()
        self.account_links = AccountLinksAPI()
        self.customers = _Namespace()


# --------------------------- Fake Supabase --------------------------------


class FakeSupabase:
    """Tiny in-memory table store matching :class:`core.db.Supabase` surface."""

    def __init__(self) -> None:
        self.tables: Dict[str, List[Dict[str, Any]]] = {}

    def _matches(self, row: Dict[str, Any], filters: Dict[str, str]) -> bool:
        for col, expr in filters.items():
            op, _, value = expr.partition(".")
            row_value = row.get(col)
            if op == "eq":
                if str(row_value) != value:
                    return False
            else:
                return False
        return True

    async def select(
        self,
        table: str,
        *,
        columns: str = "*",
        filters: Optional[Dict[str, str]] = None,
        limit: Optional[int] = None,
        order: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        rows = self.tables.get(table, [])
        if filters:
            rows = [r for r in rows if self._matches(r, filters)]
        if limit is not None:
            rows = rows[:limit]
        return [dict(r) for r in rows]

    async def insert(self, table: str, row: Dict[str, Any], *, prefer: Optional[str] = "return=representation") -> Any:
        stored = dict(row)
        stored.setdefault("id", str(uuid.uuid4()))
        self.tables.setdefault(table, []).append(stored)
        return dict(stored)

    async def update(
        self,
        table: str,
        patch: Dict[str, Any],
        *,
        filters: Dict[str, str],
        prefer: Optional[str] = "return=representation",
    ) -> List[Dict[str, Any]]:
        rows = self.tables.get(table, [])
        updated: List[Dict[str, Any]] = []
        for row in rows:
            if self._matches(row, filters):
                row.update(patch)
                updated.append(dict(row))
        return updated


# ---------------------------- fixtures ------------------------------------


@pytest.fixture
def stripe_client() -> FakeStripeClient:
    return FakeStripeClient()


@pytest.fixture
def sb() -> FakeSupabase:
    return FakeSupabase()


@pytest.fixture
def repo(sb: FakeSupabase) -> PaymentsRepo:
    return PaymentsRepo(sb)


@pytest.fixture
def ctx_live() -> SandboxContext:
    return SandboxContext(
        is_sandbox=False,
        stripe_key="sk_live_fake",
        stripe_webhook_secret="whsec_live_fake",
        suppress_whatsapp=False,
    )


@pytest.fixture
def ctx_sandbox() -> SandboxContext:
    return SandboxContext(
        is_sandbox=True,
        stripe_key="sk_test_fake",
        stripe_webhook_secret="whsec_test_fake",
        suppress_whatsapp=True,
    )


@pytest.fixture
def quote_row_paid() -> Dict[str, Any]:
    return {
        "token": "tok_main",
        "contractor_id": "con_1",
        "homeowner_email": "hom@example.com",
        "homeowner_auth_id": "auth_h",
        "homeowner_phone": "+34600111222",
        "amount_total_cents": 100_000,
        "stripe_fee_cents": 5_000,
        "materials_upfront_cents": 0,
        "iva_rate": 21,
        "payment_status": "paid",
        "checkout_session_id": "cs_paid",
        "checkout_session_attempt": 1,
        "payment_intent_id": "pi_paid_1",
        "is_sandbox": False,
        "milestones": [
            {"index": 0, "description": "Demo", "amount_cents": 50_000, "status": "pending"},
            {"index": 1, "description": "Tiles", "amount_cents": 50_000, "status": "pending"},
        ],
        "status": "paid",
        "completed_at": None,
        "consent_id": None,
        "quote_data": {
            "line_items": [
                {"description": "Demo", "amount": 500},
                {"description": "Tiles", "amount": 500},
            ],
            "service_fee_percent": 5,
            "iva_rate": 21,
        },
    }


@pytest.fixture
def contractor_row() -> Dict[str, Any]:
    return {
        "id": "con_1",
        "name": "Juan Constructor",
        "email": "con@example.com",
        "phone": "+34600333444",
        "stripe_account_id": "acct_connect_1",
        "stripe_onboarding_complete": True,
    }
