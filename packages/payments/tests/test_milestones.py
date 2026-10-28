"""Unit tests for ``payments.milestones``."""

from __future__ import annotations

import pytest

from payments import (
    MilestoneAlreadyReleased,
    MilestoneNotReleasable,
    ProofInput,
    QuoteNotPayable,
)
from payments.milestones import release, submit_proof


@pytest.fixture
def _seed_paid(sb, quote_row_paid, contractor_row):
    sb.tables["quotes"] = [dict(quote_row_paid)]
    sb.tables["contractors"] = [dict(contractor_row)]
    return sb


class TestSubmitProof:
    async def test_happy_path(self, _seed_paid, repo, ctx_live) -> None:
        result = await submit_proof(
            repo=repo,
            ctx=ctx_live,
            token="tok_main",
            idx=0,
            caller_contractor_id="con_1",
            caller_name="Juan",
            proof=ProofInput(photos=["a.jpg"], voice_url=None, note="ready"),
        )
        assert result.idx == 0
        assert result.milestone_title == "Demo"
        assert result.project_auto_started is True
        quote = _seed_paid.tables["quotes"][0]
        assert quote["status"] == "in_progress"
        assert quote["milestones"][0]["status"] == "proof_submitted"
        assert "milestone_updates" in _seed_paid.tables

    async def test_wrong_contractor_rejects(self, _seed_paid, repo, ctx_live) -> None:
        with pytest.raises(MilestoneNotReleasable):
            await submit_proof(
                repo=repo,
                ctx=ctx_live,
                token="tok_main",
                idx=0,
                caller_contractor_id="other",
                caller_name="Mal",
                proof=ProofInput(photos=[]),
            )

    async def test_milestone_out_of_bounds(self, _seed_paid, repo, ctx_live) -> None:
        with pytest.raises(MilestoneNotReleasable):
            await submit_proof(
                repo=repo,
                ctx=ctx_live,
                token="tok_main",
                idx=99,
                caller_contractor_id="con_1",
                caller_name="Juan",
                proof=ProofInput(photos=[]),
            )

    async def test_already_submitted_rejects(self, _seed_paid, repo, ctx_live) -> None:
        _seed_paid.tables["quotes"][0]["milestones"][0]["status"] = "proof_submitted"
        with pytest.raises(MilestoneNotReleasable):
            await submit_proof(
                repo=repo,
                ctx=ctx_live,
                token="tok_main",
                idx=0,
                caller_contractor_id="con_1",
                caller_name="Juan",
                proof=ProofInput(photos=[]),
            )

    async def test_missing_quote_raises(self, repo, ctx_live) -> None:
        with pytest.raises(QuoteNotPayable):
            await submit_proof(
                repo=repo,
                ctx=ctx_live,
                token="missing",
                idx=0,
                caller_contractor_id="con_1",
                caller_name="Juan",
                proof=ProofInput(photos=[]),
            )


class TestRelease:
    async def test_happy_path_first_milestone(
        self, _seed_paid, repo, ctx_live, stripe_client
    ) -> None:
        _seed_paid.tables["quotes"][0]["milestones"][0]["status"] = "proof_submitted"
        result = await release(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            token="tok_main",
            idx=0,
        )
        assert result.transfer_id == "tr_test_abc"
        assert result.idempotent_duplicate is False
        assert result.all_released is False
        assert result.amount_cents == 50_000
        created = stripe_client.transfers.created_calls[0]
        assert created["params"]["amount"] == 50_000
        assert created["params"]["destination"] == "acct_connect_1"
        assert created["options"]["idempotency_key"] == "payments:release:tok_main:0"
        assert created["params"]["transfer_group"] == "quote:tok_main"

    async def test_release_last_milestone_marks_complete(
        self, _seed_paid, repo, ctx_live, stripe_client
    ) -> None:
        q = _seed_paid.tables["quotes"][0]
        q["milestones"][0]["status"] = "released"
        q["milestones"][1]["status"] = "proof_submitted"
        result = await release(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            token="tok_main",
            idx=1,
        )
        assert result.all_released is True
        assert result.completed_at is not None
        assert q["status"] == "complete"

    async def test_already_released_rejects(
        self, _seed_paid, repo, ctx_live, stripe_client
    ) -> None:
        _seed_paid.tables["quotes"][0]["milestones"][0]["status"] = "released"
        with pytest.raises(MilestoneAlreadyReleased):
            await release(
                client=stripe_client,
                repo=repo,
                ctx=ctx_live,
                token="tok_main",
                idx=0,
            )

    async def test_not_proof_submitted_rejects(
        self, _seed_paid, repo, ctx_live, stripe_client
    ) -> None:
        with pytest.raises(MilestoneNotReleasable):
            await release(
                client=stripe_client,
                repo=repo,
                ctx=ctx_live,
                token="tok_main",
                idx=0,
            )

    async def test_idempotency_reconciliation(
        self, _seed_paid, repo, ctx_live, stripe_client
    ) -> None:
        _seed_paid.tables["quotes"][0]["milestones"][0]["status"] = "proof_submitted"
        stripe_client.transfers.raise_on_create = type(
            "IdempotencyError", (Exception,), {}
        )("idempotent replay")
        stripe_client.transfers.listings["quote:tok_main"] = [
            {"id": "tr_existing", "amount": 50_000}
        ]
        result = await release(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            token="tok_main",
            idx=0,
        )
        assert result.idempotent_duplicate is True
        assert result.transfer_id == "tr_existing"

    async def test_quote_with_is_sandbox_promotes_ctx(
        self, _seed_paid, repo, ctx_live, stripe_client
    ) -> None:
        _seed_paid.tables["quotes"][0]["is_sandbox"] = True
        _seed_paid.tables["quotes"][0]["milestones"][0]["status"] = "proof_submitted"
        import os
        os.environ["STRIPE_SECRET_KEY_TEST"] = "sk_test_xx"
        try:
            result = await release(
                client=stripe_client,
                repo=repo,
                ctx=ctx_live,
                token="tok_main",
                idx=0,
            )
        finally:
            os.environ.pop("STRIPE_SECRET_KEY_TEST", None)
        assert result.sandbox is True
