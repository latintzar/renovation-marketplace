"""Leo payments — Stripe Checkout (escrow), Connect, Transfers, Variations,
Refunds, Disputes, Webhooks.

Every Stripe SDK call in the Leo backend flows through this package. Nothing
else imports ``stripe`` directly post-migration.

Public API (54 symbols) re-exported here; submodules expose the same types
but consumers should only import from ``payments`` (so the private shape can
evolve)::

    from payments import (
        SandboxContext, resolve_sandbox, get_stripe_client,
        CheckoutInput, create_session,
        PaymentsRepo, compute_quote_financials,
        verify_stripe_event, dispatch_event,
    )
"""

from __future__ import annotations

from .sandbox import SandboxContext, resolve_for_quote, resolve_sandbox
from .client import StripeClient, build_stripe_client_from_key, get_stripe_client
from .errors import (
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
from .finance import (
    QuoteFinancials,
    build_milestones_tracking,
    compute_quote_financials,
    parse_euro_string,
)
from .repo import (
    ContractorRow,
    DisputeRow,
    MilestoneUpdateRow,
    PaymentsRepo,
    QuoteRow,
    VariationRow,
)
from .checkout import CheckoutInput, CheckoutResult
from .connect import (
    AccountPrefill,
    AccountResult,
    AccountStatus,
    OnboardingLink,
)
from .milestones import ProofInput, ReleaseResult, SubmitProofResult
from .variations import (
    CreateVariationInput,
    VariationApproveResult,
    VariationCreateResult,
    VariationDeclineResult,
)
from .refunds import CancelInput, CancelProjectResult
from .disputes import DisputeInput, DisputeResult
from .webhooks import (
    AccountUpdatedResult,
    ChargeDisputeCreatedResult,
    ChargeRefundedResult,
    CheckoutCompletedResult,
    PaymentFailedResult,
    StripeEvent,
    dispatch_event,
    verify_stripe_event,
)

__all__ = [
    # sandbox
    "SandboxContext",
    "resolve_sandbox",
    "resolve_for_quote",
    # client
    "StripeClient",
    "get_stripe_client",
    "build_stripe_client_from_key",
    # errors
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
    # finance
    "QuoteFinancials",
    "compute_quote_financials",
    "build_milestones_tracking",
    "parse_euro_string",
    # repo
    "PaymentsRepo",
    "QuoteRow",
    "ContractorRow",
    "MilestoneUpdateRow",
    "VariationRow",
    "DisputeRow",
    # checkout
    "CheckoutInput",
    "CheckoutResult",
    # connect
    "AccountPrefill",
    "AccountResult",
    "OnboardingLink",
    "AccountStatus",
    # milestones
    "ProofInput",
    "SubmitProofResult",
    "ReleaseResult",
    # variations
    "CreateVariationInput",
    "VariationCreateResult",
    "VariationApproveResult",
    "VariationDeclineResult",
    # refunds
    "CancelInput",
    "CancelProjectResult",
    # disputes
    "DisputeInput",
    "DisputeResult",
    # webhooks
    "StripeEvent",
    "CheckoutCompletedResult",
    "AccountUpdatedResult",
    "PaymentFailedResult",
    "ChargeRefundedResult",
    "ChargeDisputeCreatedResult",
    "verify_stripe_event",
    "dispatch_event",
]
