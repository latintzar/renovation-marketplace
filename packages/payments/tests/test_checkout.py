"""Unit tests for ``payments.checkout``."""

from __future__ import annotations

import pytest

from payments import (
    CheckoutInput,
    ContractorKycIncomplete,
    ContractorNoStripeAccount,
    QuoteAlreadyPaid,
    QuoteNotPayable,
)
from payments.checkout import create_session, maybe_reuse_open_session


@pytest.fixture
def _seed_paid(sb, quote_row_paid, contractor_row):
    q = dict(quote_row_paid)
    q["payment_status"] = "unpaid"
    q["checkout_session_attempt"] = 0
    sb.tables["quotes"] = [q]
    sb.tables["contractors"] = [dict(contractor_row)]
    return sb


class TestCreateSession:
    async def test_happy_path(self, _seed_paid, repo, ctx_live, stripe_client) -> None:
        result = await create_session(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            input=CheckoutInput(
                quote_token="tok_main",
                homeowner_email="hom@example.com",
                consent_id=None,
                app_base_url="https://app.example.com",
            ),
        )
        assert result.reused is False
        assert result.session_id == "cs_test_123"
        assert result.sandbox is False
        created = stripe_client.checkout.sessions.created_calls
        assert len(created) == 1
        assert created[0]["options"]["idempotency_key"] == "payments:checkout:tok_main:1"
        params = created[0]["params"]
        assert params["mode"] == "payment"
        assert params["line_items"][0]["price_data"]["unit_amount"] == 100_000
        assert params["success_url"].endswith("?paid=true")

    async def test_already_paid_rejects(self, _seed_paid, repo, ctx_live, stripe_client) -> None:
        _seed_paid.tables["quotes"][0]["payment_status"] = "paid"
        with pytest.raises(QuoteAlreadyPaid):
            await create_session(
                client=stripe_client,
                repo=repo,
                ctx=ctx_live,
                input=CheckoutInput(
                    quote_token="tok_main",
                    homeowner_email=None,
                    consent_id=None,
                    app_base_url="https://x",
                ),
            )

    async def test_pending_with_open_session_reuses(
        self, _seed_paid, repo, ctx_live, stripe_client
    ) -> None:
        _seed_paid.tables["quotes"][0]["payment_status"] = "pending"
        _seed_paid.tables["quotes"][0]["checkout_session_id"] = "cs_existing"
        stripe_client.checkout.sessions.retrieve_status = "open"
        result = await create_session(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            input=CheckoutInput(
                quote_token="tok_main",
                homeowner_email=None,
                consent_id=None,
                app_base_url="https://x",
            ),
        )
        assert result.reused is True
        assert result.session_id == "cs_existing"
        assert stripe_client.checkout.sessions.created_calls == []

    async def test_pending_with_expired_session_creates_new(
        self, _seed_paid, repo, ctx_live, stripe_client
    ) -> None:
        _seed_paid.tables["quotes"][0]["payment_status"] = "pending"
        _seed_paid.tables["quotes"][0]["checkout_session_id"] = "cs_expired"
        stripe_client.checkout.sessions.retrieve_status = "expired"
        result = await create_session(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            input=CheckoutInput(
                quote_token="tok_main",
                homeowner_email=None,
                consent_id=None,
                app_base_url="https://x",
            ),
        )
        assert result.reused is False

    async def test_no_stripe_account_rejects_live(
        self, _seed_paid, repo, ctx_live, stripe_client
    ) -> None:
        _seed_paid.tables["contractors"][0]["stripe_account_id"] = None
        with pytest.raises(ContractorNoStripeAccount):
            await create_session(
                client=stripe_client,
                repo=repo,
                ctx=ctx_live,
                input=CheckoutInput(
                    quote_token="tok_main",
                    homeowner_email=None,
                    consent_id=None,
                    app_base_url="https://x",
                ),
            )

    async def test_sandbox_bypasses_kyc(
        self, _seed_paid, repo, ctx_sandbox, stripe_client
    ) -> None:
        _seed_paid.tables["contractors"][0]["stripe_onboarding_complete"] = False
        _seed_paid.tables["contractors"][0]["stripe_account_id"] = None
        result = await create_session(
            client=stripe_client,
            repo=repo,
            ctx=ctx_sandbox,
            input=CheckoutInput(
                quote_token="tok_main",
                homeowner_email=None,
                consent_id=None,
                app_base_url="https://x",
            ),
        )
        assert result.sandbox is True

    async def test_incomplete_kyc_rejects_live(
        self, _seed_paid, repo, ctx_live, stripe_client
    ) -> None:
        _seed_paid.tables["contractors"][0]["stripe_onboarding_complete"] = False
        with pytest.raises(ContractorKycIncomplete):
            await create_session(
                client=stripe_client,
                repo=repo,
                ctx=ctx_live,
                input=CheckoutInput(
                    quote_token="tok_main",
                    homeowner_email=None,
                    consent_id=None,
                    app_base_url="https://x",
                ),
            )

    async def test_quote_not_found_raises(self, repo, ctx_live, stripe_client) -> None:
        with pytest.raises(QuoteNotPayable):
            await create_session(
                client=stripe_client,
                repo=repo,
                ctx=ctx_live,
                input=CheckoutInput(
                    quote_token="missing",
                    homeowner_email=None,
                    consent_id=None,
                    app_base_url="https://x",
                ),
            )

    async def test_attempt_counter_increments(
        self, _seed_paid, repo, ctx_live, stripe_client
    ) -> None:
        await create_session(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            input=CheckoutInput(
                quote_token="tok_main",
                homeowner_email=None,
                consent_id=None,
                app_base_url="https://x",
            ),
        )
        assert (
            _seed_paid.tables["quotes"][0]["checkout_session_attempt"] == 1
        )


class TestMaybeReuseOpenSession:
    async def test_returns_url_for_open(self, stripe_client) -> None:
        stripe_client.checkout.sessions.retrieve_status = "open"
        url = await maybe_reuse_open_session(
            client=stripe_client, existing_session_id="cs_x"
        )
        assert url is not None
        assert url.startswith("https://checkout.stripe.com/")

    async def test_returns_none_for_expired(self, stripe_client) -> None:
        stripe_client.checkout.sessions.retrieve_status = "expired"
        url = await maybe_reuse_open_session(
            client=stripe_client, existing_session_id="cs_x"
        )
        assert url is None
