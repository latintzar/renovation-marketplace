"""Unit tests for ``payments.webhooks``."""

from __future__ import annotations

import json
import time

import pytest
import stripe

from payments import InvalidWebhookSignature, PaymentsRepo, dispatch_event, verify_stripe_event


def _sign_payload(payload: bytes, secret: str) -> str:
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
    v1 = stripe.WebhookSignature._compute_signature(signed_payload, secret)
    return f"t={timestamp},v1={v1}"


class TestVerifyStripeEvent:
    def test_verifies_with_live_secret(self) -> None:
        payload = json.dumps(
            {
                "id": "evt_1",
                "object": "event",
                "type": "checkout.session.completed",
                "data": {"object": {}},
            }
        ).encode()
        sig = _sign_payload(payload, "whsec_live")
        event, is_sandbox = verify_stripe_event(
            payload=payload,
            signature=sig,
            live_secret="whsec_live",
            test_secret="whsec_test",
        )
        assert is_sandbox is False
        assert event.type == "checkout.session.completed"

    def test_falls_back_to_test_secret(self) -> None:
        payload = json.dumps(
            {
                "id": "evt_1",
                "object": "event",
                "type": "checkout.session.completed",
                "data": {"object": {}},
            }
        ).encode()
        sig = _sign_payload(payload, "whsec_test")
        event, is_sandbox = verify_stripe_event(
            payload=payload,
            signature=sig,
            live_secret="whsec_live",
            test_secret="whsec_test",
        )
        assert is_sandbox is True

    def test_both_fail_raises(self) -> None:
        payload = json.dumps(
            {
                "id": "evt_1",
                "object": "event",
                "type": "checkout.session.completed",
                "data": {"object": {}},
            }
        ).encode()
        sig = _sign_payload(payload, "whsec_other")
        with pytest.raises(InvalidWebhookSignature):
            verify_stripe_event(
                payload=payload,
                signature=sig,
                live_secret="whsec_live",
                test_secret="whsec_test",
            )

    def test_empty_secrets_raises(self) -> None:
        with pytest.raises(InvalidWebhookSignature):
            verify_stripe_event(
                payload=b"{}",
                signature="t=1,v1=xx",
                live_secret="",
                test_secret="",
            )


class TestDispatchEvent:
    async def test_checkout_completed_patches_quote(
        self, sb, repo, quote_row_paid
    ) -> None:
        q = dict(quote_row_paid)
        q["payment_status"] = "pending"
        sb.tables["quotes"] = [q]
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"quote_token": "tok_main"},
                    "payment_intent": "pi_ok",
                    "amount_total": 100_000,
                    "customer_details": {"email": "h@example.com"},
                }
            },
        }
        result = await dispatch_event(event, is_sandbox=False, repo=repo)
        assert result["handled"] is True
        assert sb.tables["quotes"][0]["payment_status"] == "paid"

    async def test_checkout_completed_variation(self, sb, repo) -> None:
        sb.tables["variation_orders"] = [
            {"id": "v1", "scope_token": "tok", "status": "pending"}
        ]
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"variation_id": "v1"},
                    "payment_intent": "pi_v1",
                    "amount_total": 5000,
                    "customer_details": {"email": ""},
                }
            },
        }
        result = await dispatch_event(event, is_sandbox=True, repo=repo)
        assert result["handled"] is True
        assert sb.tables["variation_orders"][0]["status"] == "approved"

    async def test_account_updated_marks_complete(
        self, sb, repo, contractor_row
    ) -> None:
        incomplete = dict(contractor_row)
        incomplete["stripe_onboarding_complete"] = False
        sb.tables["contractors"] = [incomplete]
        event = {
            "type": "account.updated",
            "data": {
                "object": {
                    "id": "acct_connect_1",
                    "charges_enabled": True,
                    "payouts_enabled": True,
                    "details_submitted": True,
                }
            },
        }
        result = await dispatch_event(event, is_sandbox=False, repo=repo)
        assert result["handled"] is True
        assert sb.tables["contractors"][0]["stripe_onboarding_complete"] is True

    async def test_payment_failed(self, sb, repo, quote_row_paid) -> None:
        sb.tables["quotes"] = [dict(quote_row_paid)]
        event = {
            "type": "payment_intent.payment_failed",
            "data": {"object": {"metadata": {"quote_token": "tok_main"}}},
        }
        result = await dispatch_event(event, is_sandbox=False, repo=repo)
        assert result["handled"] is True
        assert sb.tables["quotes"][0]["payment_status"] == "failed"

    async def test_charge_refunded(self, sb, repo, quote_row_paid) -> None:
        sb.tables["quotes"] = [dict(quote_row_paid)]
        event = {
            "type": "charge.refunded",
            "data": {
                "object": {
                    "metadata": {"quote_token": "tok_main"},
                    "payment_intent": "pi_paid_1",
                    "amount_refunded": 50_000,
                    "refunds": {"data": [{"id": "re_a"}]},
                }
            },
        }
        result = await dispatch_event(event, is_sandbox=False, repo=repo)
        assert result["handled"] is True
        assert sb.tables["quotes"][0]["payment_status"] == "refunded"

    async def test_charge_dispute_created(self, sb, repo, quote_row_paid) -> None:
        sb.tables["quotes"] = [dict(quote_row_paid)]
        event = {
            "type": "charge.dispute.created",
            "data": {
                "object": {
                    "id": "dp_1",
                    "charge": "ch_1",
                    "reason": "fraudulent",
                    "metadata": {"quote_token": "tok_main"},
                }
            },
        }
        result = await dispatch_event(event, is_sandbox=False, repo=repo)
        assert result["handled"] is True
        assert sb.tables["quotes"][0]["payment_status"] == "disputed"

    async def test_unknown_event_type_returns_not_handled(self, repo) -> None:
        result = await dispatch_event(
            {"type": "mystery.event", "data": {"object": {}}},
            is_sandbox=False,
            repo=repo,
        )
        assert result["handled"] is False
