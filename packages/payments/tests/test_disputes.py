"""Unit tests for ``payments.disputes``."""

from __future__ import annotations

import pytest

from payments import DisputeInput, MilestoneNotReleasable, QuoteNotPayable
from payments.disputes import list_disputes, open_dispute_state


@pytest.fixture
def _seed(sb, quote_row_paid, contractor_row):
    sb.tables["quotes"] = [dict(quote_row_paid)]
    sb.tables["contractors"] = [dict(contractor_row)]
    return sb


class TestOpenDispute:
    async def test_happy_path_on_proof_submitted(
        self, _seed, repo, ctx_live
    ) -> None:
        _seed.tables["quotes"][0]["milestones"][0]["status"] = "proof_submitted"
        result = await open_dispute_state(
            repo=repo,
            ctx=ctx_live,
            token="tok_main",
            idx=0,
            input=DisputeInput(
                reason="leaking",
                photos=["p.jpg"],
                homeowner_name="Homer",
                homeowner_phone="+34600000000",
            ),
        )
        assert result.milestone_idx == 0
        assert result.contractor_id == "con_1"
        assert _seed.tables["quotes"][0]["milestones"][0]["status"] == "disputed"
        assert "disputes" in _seed.tables

    async def test_works_on_released_milestone(
        self, _seed, repo, ctx_live
    ) -> None:
        _seed.tables["quotes"][0]["milestones"][0]["status"] = "released"
        result = await open_dispute_state(
            repo=repo,
            ctx=ctx_live,
            token="tok_main",
            idx=0,
            input=DisputeInput(
                reason="bad",
                photos=[],
                homeowner_name="H",
            ),
        )
        assert result.milestone_idx == 0

    async def test_pending_milestone_cannot_be_disputed(
        self, _seed, repo, ctx_live
    ) -> None:
        with pytest.raises(MilestoneNotReleasable):
            await open_dispute_state(
                repo=repo,
                ctx=ctx_live,
                token="tok_main",
                idx=0,
                input=DisputeInput(
                    reason="x",
                    photos=[],
                    homeowner_name="H",
                ),
            )

    async def test_missing_quote_raises(self, repo, ctx_live) -> None:
        with pytest.raises(QuoteNotPayable):
            await open_dispute_state(
                repo=repo,
                ctx=ctx_live,
                token="missing",
                idx=0,
                input=DisputeInput(reason="x", photos=[], homeowner_name="H"),
            )

    async def test_out_of_bounds_raises(self, _seed, repo, ctx_live) -> None:
        with pytest.raises(MilestoneNotReleasable):
            await open_dispute_state(
                repo=repo,
                ctx=ctx_live,
                token="tok_main",
                idx=99,
                input=DisputeInput(reason="x", photos=[], homeowner_name="H"),
            )


class TestListDisputes:
    async def test_empty_initially(self, _seed, repo) -> None:
        disputes = await list_disputes(repo=repo, token="tok_main")
        assert disputes == []

    async def test_returns_inserted(self, _seed, repo, ctx_live) -> None:
        _seed.tables["quotes"][0]["milestones"][0]["status"] = "proof_submitted"
        await open_dispute_state(
            repo=repo,
            ctx=ctx_live,
            token="tok_main",
            idx=0,
            input=DisputeInput(reason="x", photos=[], homeowner_name="H"),
        )
        disputes = await list_disputes(repo=repo, token="tok_main")
        assert len(disputes) == 1
