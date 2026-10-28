"""Public API shape checks for ``payments``."""

from __future__ import annotations

import payments


EXPECTED = {
    # sandbox
    "SandboxContext", "resolve_sandbox", "resolve_for_quote",
    # client
    "StripeClient", "get_stripe_client", "build_stripe_client_from_key",
    # errors
    "PaymentError", "QuoteAlreadyPaid", "QuoteNotPayable",
    "ContractorKycIncomplete", "ContractorNoStripeAccount",
    "MilestoneNotReleasable", "MilestoneAlreadyReleased",
    "VariationNotPending", "RefundNotAllowed", "StripeNotConfigured",
    "StripeCallFailed", "PaymentsIdempotencyLost",
    "InvalidWebhookSignature", "InvalidWebhookPayload",
    # finance
    "QuoteFinancials", "compute_quote_financials",
    "build_milestones_tracking", "parse_euro_string",
    # repo
    "PaymentsRepo", "QuoteRow", "ContractorRow", "MilestoneUpdateRow",
    "VariationRow", "DisputeRow",
    # checkout
    "CheckoutInput", "CheckoutResult",
    # connect
    "AccountPrefill", "AccountResult", "OnboardingLink", "AccountStatus",
    # milestones
    "ProofInput", "SubmitProofResult", "ReleaseResult",
    # variations
    "CreateVariationInput", "VariationCreateResult",
    "VariationApproveResult", "VariationDeclineResult",
    # refunds
    "CancelInput", "CancelProjectResult",
    # disputes
    "DisputeInput", "DisputeResult",
    # webhooks
    "StripeEvent", "CheckoutCompletedResult", "AccountUpdatedResult",
    "PaymentFailedResult", "ChargeRefundedResult",
    "ChargeDisputeCreatedResult", "verify_stripe_event", "dispatch_event",
}


def test_all_count() -> None:
    assert len(payments.__all__) == 55


def test_all_matches_expected() -> None:
    assert set(payments.__all__) == EXPECTED


def test_all_symbols_importable() -> None:
    for sym in payments.__all__:
        assert hasattr(payments, sym), f"missing {sym!r}"


def test_all_error_classes_subclass_payment_error() -> None:
    from payments import PaymentError
    errors = {
        "QuoteAlreadyPaid", "QuoteNotPayable",
        "ContractorKycIncomplete", "ContractorNoStripeAccount",
        "MilestoneNotReleasable", "MilestoneAlreadyReleased",
        "VariationNotPending", "RefundNotAllowed", "StripeNotConfigured",
        "StripeCallFailed", "PaymentsIdempotencyLost",
        "InvalidWebhookSignature", "InvalidWebhookPayload",
    }
    for err_name in errors:
        cls = getattr(payments, err_name)
        assert issubclass(cls, PaymentError), f"{err_name} not PaymentError subclass"
