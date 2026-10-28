"""Payments error hierarchy.

All payments-raised errors inherit from :class:`PaymentError`, which itself is
a subclass of :class:`core.errors.AppError` so the FastAPI global handler in
``apps/scope-backend/main.py`` can convert them to the standard envelope::

    {"ok": false, "error": ..., "code": ...}

Each subclass pins its own ``status`` and ``default_code``. Callers ``except``
by concrete class (not by string matching).
"""

from __future__ import annotations

from typing import Optional

try:
    from core.errors import AppError as _AppError
except Exception:  # pragma: no cover - defensive, core is a hard dep
    class _AppError(Exception):
        status: int = 500
        default_code: Optional[str] = "APP_ERROR"

        def __init__(self, message: str, *, code: Optional[str] = None) -> None:
            super().__init__(message)
            self.message = message
            self.code = code or self.default_code


class PaymentError(_AppError):
    """Base for every payments-raised error."""

    status = 500
    default_code = "PAYMENT_ERROR"


class QuoteAlreadyPaid(PaymentError):
    status = 409
    default_code = "QUOTE_ALREADY_PAID"


class QuoteNotPayable(PaymentError):
    status = 422
    default_code = "QUOTE_NOT_PAYABLE"


class ContractorKycIncomplete(PaymentError):
    status = 422
    default_code = "CONTRACTOR_KYC_INCOMPLETE"


class ContractorNoStripeAccount(PaymentError):
    status = 422
    default_code = "CONTRACTOR_NO_STRIPE_ACCOUNT"


class MilestoneNotReleasable(PaymentError):
    status = 409
    default_code = "MILESTONE_NOT_RELEASABLE"


class MilestoneAlreadyReleased(PaymentError):
    status = 409
    default_code = "MILESTONE_ALREADY_RELEASED"


class VariationNotPending(PaymentError):
    status = 409
    default_code = "VARIATION_NOT_PENDING"


class RefundNotAllowed(PaymentError):
    status = 409
    default_code = "REFUND_NOT_ALLOWED"


class StripeNotConfigured(PaymentError):
    status = 500
    default_code = "STRIPE_NOT_CONFIGURED"


class StripeCallFailed(PaymentError):
    status = 500
    default_code = "STRIPE_CALL_FAILED"


class PaymentsIdempotencyLost(PaymentError):
    status = 500
    default_code = "PAYMENTS_IDEMPOTENCY_LOST"


class InvalidWebhookSignature(PaymentError):
    status = 403
    default_code = "INVALID_WEBHOOK_SIGNATURE"


class InvalidWebhookPayload(PaymentError):
    status = 422
    default_code = "INVALID_WEBHOOK_PAYLOAD"


__all__ = [
    "PaymentError",
    "QuoteAlreadyPaid",
    "QuoteNotPayable",
    "ContractorKycIncomplete",
    "ContractorNoStripeAccount",
    "MilestoneNotReleasable",
    "MilestoneAlreadyReleased",
    "VariationNotPending",
    "RefundNotAllowed",
    "StripeNotConfigured",
    "StripeCallFailed",
    "PaymentsIdempotencyLost",
    "InvalidWebhookSignature",
    "InvalidWebhookPayload",
]
