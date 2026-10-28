"""Unit tests for the payments error hierarchy."""

from __future__ import annotations

import pytest

from payments import (
    ContractorKycIncomplete,
    ContractorNoStripeAccount,
    InvalidWebhookPayload,
    InvalidWebhookSignature,
    MilestoneAlreadyReleased,
    MilestoneNotReleasable,
    PaymentError,
    PaymentsIdempotencyLost,
    QuoteAlreadyPaid,
    QuoteNotPayable,
    RefundNotAllowed,
    StripeCallFailed,
    StripeNotConfigured,
    VariationNotPending,
)

EXPECTED_ERRORS = [
    (QuoteAlreadyPaid, 409, "QUOTE_ALREADY_PAID"),
    (QuoteNotPayable, 422, "QUOTE_NOT_PAYABLE"),
    (ContractorKycIncomplete, 422, "CONTRACTOR_KYC_INCOMPLETE"),
    (ContractorNoStripeAccount, 422, "CONTRACTOR_NO_STRIPE_ACCOUNT"),
    (MilestoneNotReleasable, 409, "MILESTONE_NOT_RELEASABLE"),
    (MilestoneAlreadyReleased, 409, "MILESTONE_ALREADY_RELEASED"),
    (VariationNotPending, 409, "VARIATION_NOT_PENDING"),
    (RefundNotAllowed, 409, "REFUND_NOT_ALLOWED"),
    (StripeNotConfigured, 500, "STRIPE_NOT_CONFIGURED"),
    (StripeCallFailed, 500, "STRIPE_CALL_FAILED"),
    (PaymentsIdempotencyLost, 500, "PAYMENTS_IDEMPOTENCY_LOST"),
    (InvalidWebhookSignature, 403, "INVALID_WEBHOOK_SIGNATURE"),
    (InvalidWebhookPayload, 422, "INVALID_WEBHOOK_PAYLOAD"),
]


@pytest.mark.parametrize("cls,status,code", EXPECTED_ERRORS)
def test_error_inherits_from_payment_error(cls, status, code) -> None:
    assert issubclass(cls, PaymentError)


@pytest.mark.parametrize("cls,status,code", EXPECTED_ERRORS)
def test_error_status_and_default_code(cls, status, code) -> None:
    assert cls.status == status
    assert cls.default_code == code


def test_payment_error_carries_message() -> None:
    err = PaymentError("something failed", code="OVERRIDE")
    assert err.code == "OVERRIDE"
    assert "something failed" in str(err)


def test_default_code_when_not_overridden() -> None:
    err = QuoteAlreadyPaid("already paid")
    assert err.code == "QUOTE_ALREADY_PAID"


def test_payment_error_is_exception_subclass() -> None:
    err = PaymentError("boom")
    assert isinstance(err, Exception)


def test_caught_by_payment_error_base() -> None:
    try:
        raise StripeCallFailed("stripe failed")
    except PaymentError as exc:
        assert exc.default_code == "STRIPE_CALL_FAILED"
