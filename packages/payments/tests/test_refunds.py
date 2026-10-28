"""Unit tests for ``payments.refunds``."""

from __future__ import annotations

import pytest

from payments import CancelInput, RefundNotAllowed
from payments.refunds import cancel_project


@pytest.fixture
def _seed(sb, quote_row_paid, contractor_row):
    sb.tables["quotes"] = [dict(quote_row_paid)]
    sb.tables["contractors"] = [dict(contractor_row)]
    return sb


class TestCancelProject:
    async def test_happy_path_full_refund(
        self, _seed, repo, ctx_live, stripe_client
    ) -> None:
        result = await cancel_project(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            token="tok_main",
            input=CancelInput(
                reason="changed mind", initiator_role="homeowner"
            ),
        )
        assert result.refund_id == "re_test_xyz"
        assert result.amount_refunded_cents == 100_000
        assert result.idempotent_duplicate is False
        call = stripe_client.refunds.created_calls[0]
        assert call["params"]["payment_intent"] == "pi_paid_1"
        assert call["params"]["amount"] == 100_000
        assert call["options"]["idempotency_key"] == "payments:refund:tok_main"
        assert _seed.tables["quotes"][0]["payment_status"] == "refunded"
        assert _seed.tables["quotes"][0]["status"] == "cancelled"
        assert "cancellations" in _seed.tables

    async def test_partial_refund_uses_supplied_amount(
        self, _seed, repo, ctx_live, stripe_client
    ) -> None:
        result = await cancel_project(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            token="tok_main",
            input=CancelInput(
                reason="partial", initiator_role="admin", amount_cents=30_000
            ),
        )
        assert result.amount_refunded_cents == 30_000

    async def test_not_paid_rejects(self, _seed, repo, ctx_live, stripe_client) -> None:
        _seed.tables["quotes"][0]["payment_status"] = "unpaid"
        with pytest.raises(RefundNotAllowed):
            await cancel_project(
                client=stripe_client,
                repo=repo,
                ctx=ctx_live,
                token="tok_main",
                input=CancelInput(reason="x", initiator_role="homeowner"),
            )

    async def test_work_started_blocks_non_admin(
        self, _seed, repo, ctx_live, stripe_client
    ) -> None:
        _seed.tables["quotes"][0]["milestones"][0]["status"] = "proof_submitted"
        with pytest.raises(RefundNotAllowed):
            await cancel_project(
                client=stripe_client,
                repo=repo,
                ctx=ctx_live,
                token="tok_main",
                input=CancelInput(reason="x", initiator_role="homeowner"),
            )

    async def test_admin_can_bypass_work_guard(
        self, _seed, repo, ctx_live, stripe_client
    ) -> None:
        _seed.tables["quotes"][0]["milestones"][0]["status"] = "proof_submitted"
        await cancel_project(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            token="tok_main",
            input=CancelInput(reason="ops", initiator_role="admin"),
        )
        assert _seed.tables["quotes"][0]["payment_status"] == "refunded"

    async def test_idempotency_reconciliation(
        self, _seed, repo, ctx_live, stripe_client
    ) -> None:
        stripe_client.refunds.raise_on_create = type(
            "IdempotencyError", (Exception,), {}
        )("idempotent replay")
        stripe_client.refunds.listings["pi_paid_1"] = [
            {"id": "re_existing", "amount": 100_000}
        ]
        result = await cancel_project(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            token="tok_main",
            input=CancelInput(reason="retry", initiator_role="admin"),
        )
        assert result.idempotent_duplicate is True
        assert result.refund_id == "re_existing"
