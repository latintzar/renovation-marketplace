"""Unit tests for ``payments.repo``."""

from __future__ import annotations

import pytest

from payments import (
    ContractorRow,
    DisputeRow,
    MilestoneUpdateRow,
    PaymentsRepo,
    QuoteRow,
    VariationRow,
)


class TestRowFromRow:
    def test_quote_row_renames_stripe_fee_to_leo_fee(self) -> None:
        row = QuoteRow.from_row({"token": "t", "stripe_fee_cents": 500})
        assert row.leo_fee_cents == 500

    def test_quote_row_defaults(self) -> None:
        row = QuoteRow.from_row({"token": "t", "contractor_id": "c"})
        assert row.payment_status == "unpaid"
        assert row.status == "draft"
        assert row.milestones == []

    def test_contractor_row(self) -> None:
        row = ContractorRow.from_row(
            {
                "id": "c1",
                "name": "Juan",
                "stripe_account_id": "acct_1",
                "stripe_onboarding_complete": True,
            }
        )
        assert row.id == "c1"
        assert row.stripe_onboarding_complete is True

    def test_milestone_update_row_photos_preserved(self) -> None:
        row = MilestoneUpdateRow.from_row(
            {"id": "m1", "scope_token": "t", "milestone_index": 0, "photos": ["a.jpg"]}
        )
        assert row.photos == ["a.jpg"]

    def test_variation_row_defaults(self) -> None:
        row = VariationRow.from_row({"id": "v1", "scope_token": "t"})
        assert row.status == "pending"
        assert row.amount_cents == 0

    def test_dispute_row(self) -> None:
        row = DisputeRow.from_row(
            {
                "id": "d1",
                "scope_token": "t",
                "milestone_index": 1,
                "reason": "bad",
                "is_sandbox": True,
                "created_at": "2024-01-01",
            }
        )
        assert row.milestone_index == 1
        assert row.is_sandbox is True


class TestQuoteReadWrite:
    async def test_get_quote_by_token(self, sb, repo, quote_row_paid) -> None:
        sb.tables["quotes"] = [quote_row_paid]
        q = await repo.get_quote_by_token("tok_main")
        assert q is not None
        assert q.contractor_id == "con_1"
        assert q.leo_fee_cents == 5_000  # stripe_fee_cents mapped

    async def test_get_quote_returns_none_when_absent(self, repo) -> None:
        assert await repo.get_quote_by_token("nope") is None

    async def test_patch_quote_applies_fee_rename(self, sb, repo, quote_row_paid) -> None:
        sb.tables["quotes"] = [dict(quote_row_paid)]
        await repo.patch_quote("tok_main", {"leo_fee_cents": 9_999})
        assert sb.tables["quotes"][0]["stripe_fee_cents"] == 9_999
        assert "leo_fee_cents" not in sb.tables["quotes"][0]

    async def test_record_checkout_session(self, sb, repo, quote_row_paid) -> None:
        sb.tables["quotes"] = [dict(quote_row_paid)]
        await repo.record_checkout_session(
            "tok_main",
            session_id="cs_1",
            homeowner_email="h@example.com",
            consent_id="c1",
            is_sandbox=True,
        )
        row = sb.tables["quotes"][0]
        assert row["checkout_session_id"] == "cs_1"
        assert row["payment_status"] == "pending"
        assert row["is_sandbox"] is True
        assert row["consent_id"] == "c1"

    async def test_mark_quote_paid_sets_all_fields(self, sb, repo, quote_row_paid) -> None:
        sb.tables["quotes"] = [dict(quote_row_paid)]
        await repo.mark_quote_paid(
            "tok_main",
            payment_intent_id="pi_1",
            amount_total_cents=100_000,
            homeowner_email="paid@example.com",
            homeowner_auth_id="auth_h",
        )
        row = sb.tables["quotes"][0]
        assert row["payment_status"] == "paid"
        assert row["payment_intent_id"] == "pi_1"
        assert row["homeowner_email"] == "paid@example.com"
        assert row["homeowner_auth_id"] == "auth_h"


class TestContractorOps:
    async def test_get_contractor(self, sb, repo, contractor_row) -> None:
        sb.tables["contractors"] = [contractor_row]
        c = await repo.get_contractor("con_1")
        assert c is not None
        assert c.stripe_account_id == "acct_connect_1"

    async def test_find_contractor_by_stripe_account(
        self, sb, repo, contractor_row
    ) -> None:
        sb.tables["contractors"] = [contractor_row]
        c = await repo.find_contractor_by_stripe_account("acct_connect_1")
        assert c is not None and c.id == "con_1"

    async def test_record_account_created_sandbox_marks_complete(
        self, sb, repo, contractor_row
    ) -> None:
        sb.tables["contractors"] = [dict(contractor_row)]
        await repo.record_account_created(
            "con_1", stripe_account_id="acct_new", sandbox=True
        )
        row = sb.tables["contractors"][0]
        assert row["stripe_account_id"] == "acct_new"
        assert row["stripe_onboarding_complete"] is True


class TestMilestoneOps:
    async def test_insert_milestone_update(self, sb, repo) -> None:
        row = await repo.insert_milestone_update(
            {
                "scope_token": "tok_main",
                "milestone_index": 0,
                "status": "proof_submitted",
                "photos": ["a.jpg"],
            }
        )
        assert row.status == "proof_submitted"
        assert "milestone_updates" in sb.tables

    async def test_mark_milestone_released_updates_row(self, sb, repo) -> None:
        sb.tables["milestone_updates"] = [
            {"scope_token": "tok", "milestone_index": 0, "status": "proof_submitted"}
        ]
        await repo.mark_milestone_released(
            token="tok", idx=0, transfer_id="tr_1", released_at="2024-01-01"
        )
        assert sb.tables["milestone_updates"][0]["status"] == "released"
        assert sb.tables["milestone_updates"][0]["stripe_transfer_id"] == "tr_1"


class TestVariationOps:
    async def test_insert_and_list_variations(self, sb, repo) -> None:
        row = await repo.insert_variation(
            {"scope_token": "tok", "amount_cents": 5_000, "description": "extra"}
        )
        assert row.amount_cents == 5_000
        listing = await repo.list_variations("tok")
        assert len(listing) == 1

    async def test_mark_variation_paid(self, sb, repo) -> None:
        row = await repo.insert_variation(
            {"scope_token": "tok", "amount_cents": 1000, "description": "d"}
        )
        await repo.mark_variation_paid(row.id, payment_intent_id="pi_x")
        stored = sb.tables["variation_orders"][0]
        assert stored["status"] == "approved"
        assert stored["payment_intent_id"] == "pi_x"


class TestDisputeOps:
    async def test_insert_and_list_disputes(self, sb, repo) -> None:
        await repo.insert_dispute(
            {
                "scope_token": "tok",
                "milestone_index": 0,
                "reason": "bad work",
                "is_sandbox": False,
                "created_at": "2024-01-01",
            }
        )
        disputes = await repo.list_disputes("tok")
        assert len(disputes) == 1
        assert disputes[0].reason == "bad work"
