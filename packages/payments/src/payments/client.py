"""Per-request Stripe client factory.

D1 in ``design.md`` — **no more process-global stripe api_key mutation**. That pattern is a
process-global assignment which, under async FastAPI concurrency, lets request A
set the test key, request B set the live key, and request A's subsequent
``stripe.checkout.Session.create`` call now uses the wrong key. The race is
silent — it produces real charges on wrong accounts.

Every module in :mod:`payments` takes the client as an argument. Tests inject
a ``FakeStripeClient`` with the same namespace attrs.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from .errors import StripeNotConfigured
from .sandbox import SandboxContext


@runtime_checkable
class StripeClient(Protocol):
    """Protocol matching :class:`stripe.StripeClient` (stripe-python >= 7.x)."""

    checkout: Any
    transfers: Any
    refunds: Any
    accounts: Any
    account_links: Any
    customers: Any


def _build_client(api_key: str) -> Any:
    """Build a real ``stripe.StripeClient``. Import is lazy so tests can run
    without ``stripe`` installed (they inject a fake)."""

    try:
        import stripe  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised only without stripe
        raise StripeNotConfigured(
            "stripe SDK not installed",
            code="STRIPE_NOT_CONFIGURED",
        ) from exc

    return stripe.StripeClient(api_key=api_key)


def get_stripe_client(ctx: SandboxContext) -> StripeClient:
    """Return a Stripe client keyed to this request's resolved Stripe secret.

    Raises :class:`StripeNotConfigured` if ``ctx.stripe_key`` is empty.
    Each call returns an isolated client — no process-global state mutated.
    """

    if not ctx.stripe_key:
        raise StripeNotConfigured("Stripe key not configured for this request")

    return _build_client(ctx.stripe_key)


def build_stripe_client_from_key(api_key: Optional[str]) -> StripeClient:
    """Explicit helper used by webhook dispatchers where we've already pulled
    the key out of the :class:`SandboxContext` tri-state verification."""

    if not api_key:
        raise StripeNotConfigured("Stripe key is required")
    return _build_client(api_key)


__all__ = ["StripeClient", "get_stripe_client", "build_stripe_client_from_key"]
