"""Unit tests for ``payments.connect``."""

from __future__ import annotations

import pytest

from payments import AccountPrefill
from payments.connect import (
    create_account,
    create_onboarding_link,
    get_account_status,
)


class TestCreateAccount:
    async def test_idempotent_when_account_exists(
        self, sb, repo, ctx_live, stripe_client, contractor_row
    ) -> None:
        sb.tables["contractors"] = [dict(contractor_row)]
        result = await create_account(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            contractor_id="con_1",
            prefill=AccountPrefill(),
        )
        assert result.existing is True
        assert result.stripe_account_id == "acct_connect_1"
        assert stripe_client.accounts.created == []

    async def test_creates_new_account_with_manual_payouts(
        self, sb, repo, ctx_live, stripe_client, contractor_row
    ) -> None:
        fresh = dict(contractor_row)
        fresh["stripe_account_id"] = None
        sb.tables["contractors"] = [fresh]
        result = await create_account(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            contractor_id="con_1",
            prefill=AccountPrefill(email="e@x", first_name="E"),
        )
        assert result.existing is False
        assert result.stripe_account_id == "acct_test_1"
        call = stripe_client.accounts.created[0]
        assert call["type"] == "express"
        assert call["country"] == "ES"
        assert call["capabilities"]["transfers"]["requested"] is True
        assert call["settings"]["payouts"]["schedule"]["interval"] == "manual"
        assert call["individual"]["email"] == "e@x"

    async def test_sandbox_marks_complete(
        self, sb, repo, ctx_sandbox, stripe_client, contractor_row
    ) -> None:
        fresh = dict(contractor_row)
        fresh["stripe_account_id"] = None
        fresh["stripe_onboarding_complete"] = False
        sb.tables["contractors"] = [fresh]
        await create_account(
            client=stripe_client,
            repo=repo,
            ctx=ctx_sandbox,
            contractor_id="con_1",
            prefill=AccountPrefill(),
        )
        assert sb.tables["contractors"][0]["stripe_onboarding_complete"] is True


class TestCreateOnboardingLink:
    async def test_uses_eventually_due(
        self, sb, repo, ctx_live, stripe_client, contractor_row
    ) -> None:
        sb.tables["contractors"] = [dict(contractor_row)]
        link = await create_onboarding_link(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            contractor_id="con_1",
            return_url="https://return",
            refresh_url="https://refresh",
        )
        assert link.url.startswith("https://connect.stripe.com/")
        call = stripe_client.account_links.created[0]
        assert call["collection_options"]["fields"] == "eventually_due"
        assert call["account"] == "acct_connect_1"


class TestGetAccountStatus:
    async def test_complete_account(
        self, sb, repo, ctx_live, stripe_client, contractor_row
    ) -> None:
        incomplete = dict(contractor_row)
        incomplete["stripe_onboarding_complete"] = False
        sb.tables["contractors"] = [incomplete]
        status = await get_account_status(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            contractor_id="con_1",
        )
        assert status.has_account is True
        assert status.onboarding_complete is True
        assert sb.tables["contractors"][0]["stripe_onboarding_complete"] is True

    async def test_no_account_returns_empty_status(self, sb, repo, ctx_live, stripe_client, contractor_row) -> None:
        row = dict(contractor_row)
        row["stripe_account_id"] = None
        sb.tables["contractors"] = [row]
        status = await get_account_status(
            client=stripe_client,
            repo=repo,
            ctx=ctx_live,
            contractor_id="con_1",
        )
        assert status.has_account is False
        assert status.onboarding_complete is False
