"""Per-request Stripe-mode + WhatsApp-suppression resolver.

Reads the request headers ``X-Sandbox`` and ``X-Allow-WhatsApp`` (both case-insensitive
values of ``true``) and resolves the Stripe key + webhook secret from env directly
(no ``config.settings`` coupling — that layer lives in ``apps/scope-backend``).

Invariants preserved from ``unmigrated/backend/shared/sandbox.py``:

- ``is_sandbox`` and ``suppress_whatsapp`` are **orthogonal**. ``X-Allow-WhatsApp: true``
  causes a sandbox call to still emit real WhatsApp messages (used by notification tests).
- Missing env yields empty strings; callers are expected to wrap via ``get_stripe_client``
  which raises :class:`StripeNotConfigured` rather than returning a no-key client.
- Webhooks do NOT go through this function — they have their own tri-state verifier
  in :mod:`payments.webhooks`.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from fastapi import Header

logger = logging.getLogger(__name__)


_STRIPE_SECRET_KEY = "STRIPE_SECRET_KEY"
_STRIPE_SECRET_KEY_TEST = "STRIPE_SECRET_KEY_TEST"
_STRIPE_WEBHOOK_SECRET = "STRIPE_WEBHOOK_SECRET"
_STRIPE_WEBHOOK_SECRET_TEST = "STRIPE_WEBHOOK_SECRET_TEST"


def _env(name: str) -> str:
    return os.getenv(name, "") or ""


@dataclass(frozen=True)
class SandboxContext:
    """Per-request Stripe-mode + messaging-suppression context."""

    is_sandbox: bool
    stripe_key: str
    stripe_webhook_secret: str
    suppress_whatsapp: bool


async def resolve_sandbox(
    x_sandbox: Optional[str] = Header(None),
    x_allow_whatsapp: Optional[str] = Header(None),
) -> SandboxContext:
    """FastAPI dependency. Returns a :class:`SandboxContext` for this request.

    ``X-Sandbox: true`` swaps Stripe keys to test-mode and suppresses real
    WhatsApp unless ``X-Allow-WhatsApp: true`` overrides the suppression.
    """

    is_sandbox = (x_sandbox or "").lower() == "true"
    allow_whatsapp = (x_allow_whatsapp or "").lower() == "true"

    if is_sandbox:
        stripe_key = _env(_STRIPE_SECRET_KEY_TEST)
        stripe_webhook_secret = _env(_STRIPE_WEBHOOK_SECRET_TEST)
        logger.debug("Sandbox mode active — using Stripe test keys")
    else:
        stripe_key = _env(_STRIPE_SECRET_KEY)
        stripe_webhook_secret = _env(_STRIPE_WEBHOOK_SECRET)

    suppress_whatsapp = is_sandbox and not allow_whatsapp

    return SandboxContext(
        is_sandbox=is_sandbox,
        stripe_key=stripe_key,
        stripe_webhook_secret=stripe_webhook_secret,
        suppress_whatsapp=suppress_whatsapp,
    )


def resolve_for_quote(quote_is_sandbox: bool, ctx: SandboxContext) -> SandboxContext:
    """If a quote row was created in sandbox mode but the request header wasn't,
    return a :class:`SandboxContext` with test keys; otherwise return ``ctx``.

    This consolidates the duplicated sandbox-quote-override pattern that used to
    appear in ``routes/milestones.py`` and ``routes/milestone.py``.
    """

    if quote_is_sandbox and not ctx.is_sandbox:
        return SandboxContext(
            is_sandbox=True,
            stripe_key=_env(_STRIPE_SECRET_KEY_TEST),
            stripe_webhook_secret=_env(_STRIPE_WEBHOOK_SECRET_TEST),
            suppress_whatsapp=ctx.suppress_whatsapp,
        )
    return ctx


__all__ = ["SandboxContext", "resolve_sandbox", "resolve_for_quote"]
