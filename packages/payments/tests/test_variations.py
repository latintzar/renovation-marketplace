"""Unit tests for ``payments.variations``."""

from __future__ import annotations

import pytest

from payments import CreateVariationInput, VariationNotPending
from payments.variations import (
    approve_variation,
    create_variation,
    decline_variation,
)


@pytest.fixture
def _seed(sb, quote_row_paid, contractor_row):
    sb.tables["quotes"] = [dict(quote_row_paid)]
    sb.tables["contractors"] = [dict(contractor_row)]
    return sb


class TestCreateVariation:
    async def test_happy_path(self, _seed, repo, ctx_live) -> None:
        result = await create_variation(
            repo=repo,
            ctx=ctx_live,
            token="tok_main",
            caller_contractor_id="con_1",
            caller_name="Juan",
            input=CreateVariationInput(
                amount_cents=15_000, description="extra tiles"
            ),
        )
        assert result.amount_cents == 15_000
        assert result.contractor_name == "Juan"
        stored = _seed.tables["variation_orders"][0]
        assert stored["status"] == "pending"

    async def test_wrong_contractor_rejects(self, _seed, repo, ctx_live) -> None:
        with pytest.raises(VariationNotPending):
            await create_variation(
                repo=repo,
                ctx=ctx_live,
                token="tok_main",
                caller_contractor_id="other",
                caller_name="Mal",
                input=CreateVariationInput(amount_cents=1000, description="d"),
            )

    async def test_zero_amount_rejected(self, _seed, repo, ctx_live) -> None:
        with pytest.raises(VariationNotPending):
            await create_variation(
                repo=repo,
                ctx=ctx_live,
                token="tok_main",
                caller_contractor_id="con_1",
                caller_name="Juan",
                input=CreateVariationInput(amount_cents=0, description="zero"),
            )


class TestApproveVariation:
    async def test_happy_path(self, _seed, repo, ctx_live, stripe_client) -> None:
        row = await repo.insert_variation(
            {
                "scope_token": "tok_main",
                "status": "pending",
                "amount_cents": 15_000,
                "description": "extra",
            }
        )
        result = await approve_variation(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            token="tok_main",
            variation_id=row.id,
            app_base_url="https://app.example.com",
        )
        assert result.variation_id == row.id
        assert result.checkout_url.startswith("https://checkout.stripe.com/")
        call = stripe_client.checkout.sessions.created_calls[0]
        assert call["params"]["success_url"].endswith("?variation_paid=true")
        assert (
            call["options"]["idempotency_key"]
            == f"payments:variation-approve:{row.id}"
        )

    async def test_not_pending_rejects(self, _seed, repo, ctx_live, stripe_client) -> None:
        row = await repo.insert_variation(
            {
                "scope_token": "tok_main",
                "status": "approved",
                "amount_cents": 1000,
                "description": "d",
            }
        )
        with pytest.raises(VariationNotPending):
            await approve_variation(
                client=stripe_client,
                repo=repo,
                ctx=ctx_live,
                token="tok_main",
                variation_id=row.id,
                app_base_url="https://x",
            )

    async def test_wrong_token_rejects(self, _seed, repo, ctx_live, stripe_client) -> None:
        row = await repo.insert_variation(
            {
                "scope_token": "other_token",
                "status": "pending",
                "amount_cents": 1000,
                "description": "d",
            }
        )
        with pytest.raises(VariationNotPending):
            await approve_variation(
                client=stripe_client,
                repo=repo,
                ctx=ctx_live,
                token="tok_main",
                variation_id=row.id,
                app_base_url="https://x",
            )


class TestDeclineVariation:
    async def test_happy_path(self, _seed, repo, ctx_live) -> None:
        row = await repo.insert_variation(
            {
                "scope_token": "tok_main",
                "status": "pending",
                "amount_cents": 1000,
                "description": "d",
            }
        )
        result = await decline_variation(
            repo=repo,
            ctx=ctx_live,
            token="tok_main",
            variation_id=row.id,
        )
        assert result.contractor_id == "con_1"
        stored = _seed.tables["variation_orders"][0]
        assert stored["status"] == "declined"

    async def test_already_declined_rejects(self, _seed, repo, ctx_live) -> None:
        row = await repo.insert_variation(
            {
                "scope_token": "tok_main",
                "status": "declined",
                "amount_cents": 1000,
                "description": "d",
            }
        )
        with pytest.raises(VariationNotPending):
            await decline_variation(
                repo=repo,
                ctx=ctx_live,
                token="tok_main",
                variation_id=row.id,
            )
