"""Contractor Stripe Express onboarding.

Preserves the two invariants called out in the audit:

- ``settings.payouts.schedule.interval = "manual"`` — Leo controls payouts;
  funds land in the contractor's Express account but do not auto-payout to
  the bank.
- ``collection_options.fields = "eventually_due"`` on the AccountLink so
  Stripe collects every required field upfront and we never surface a
  second-onboarding interruption.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .client import StripeClient
from .errors import StripeCallFailed
from .repo import PaymentsRepo
from .sandbox import SandboxContext


@dataclass(frozen=True)
class AccountPrefill:
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@dataclass(frozen=True)
class AccountResult:
    stripe_account_id: str
    existing: bool
    kyc_bypassed: bool


@dataclass(frozen=True)
class OnboardingLink:
    url: str
    expires_at: int


@dataclass(frozen=True)
class AccountStatus:
    has_account: bool
    charges_enabled: bool
    payouts_enabled: bool
    details_submitted: bool
    onboarding_complete: bool
    requirements: Dict[str, Any]


def _call(fn, *args, **kwargs) -> Any:
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # pragma: no cover - mapped by caller wrappers
        raise StripeCallFailed(f"Stripe call failed: {exc}") from exc


async def create_account(
    *,
    client: StripeClient,
    repo: PaymentsRepo,
    ctx: SandboxContext,
    contractor_id: str,
    prefill: AccountPrefill,
) -> AccountResult:
    """Create a Stripe Express account for a contractor, idempotent per-contractor."""

    contractor = await repo.get_contractor(contractor_id)
    if contractor and contractor.stripe_account_id:
        return AccountResult(
            stripe_account_id=contractor.stripe_account_id,
            existing=True,
            kyc_bypassed=ctx.is_sandbox,
        )

    individual: Dict[str, Any] = {}
    if prefill.email:
        individual["email"] = prefill.email
    if prefill.first_name:
        individual["first_name"] = prefill.first_name
    if prefill.last_name:
        individual["last_name"] = prefill.last_name

    params: Dict[str, Any] = {
        "type": "express",
        "country": "ES",
        "capabilities": {
            "transfers": {"requested": True},
        },
        "settings": {
            "payouts": {"schedule": {"interval": "manual"}},
        },
    }
    if individual:
        params["individual"] = individual

    account = _call(client.accounts.create, params=params) if _accepts_params_kwarg(
        client.accounts.create
    ) else _call(client.accounts.create, **params)

    account_id = getattr(account, "id", None) or account["id"]

    await repo.record_account_created(
        contractor_id,
        stripe_account_id=account_id,
        sandbox=ctx.is_sandbox,
    )

    return AccountResult(
        stripe_account_id=account_id,
        existing=False,
        kyc_bypassed=ctx.is_sandbox,
    )


async def create_onboarding_link(
    *,
    client: StripeClient,
    repo: PaymentsRepo,
    ctx: SandboxContext,
    contractor_id: str,
    return_url: str,
    refresh_url: str,
) -> OnboardingLink:
    """Generate a Stripe AccountLink for contractor onboarding."""

    contractor = await repo.get_contractor(contractor_id)
    if contractor is None or not contractor.stripe_account_id:
        raise StripeCallFailed("Contractor has no Stripe account")

    params: Dict[str, Any] = {
        "account": contractor.stripe_account_id,
        "return_url": return_url,
        "refresh_url": refresh_url,
        "type": "account_onboarding",
        "collection_options": {"fields": "eventually_due"},
    }

    link = _call(client.account_links.create, params=params) if _accepts_params_kwarg(
        client.account_links.create
    ) else _call(client.account_links.create, **params)

    url = getattr(link, "url", None) or link["url"]
    expires_at = getattr(link, "expires_at", None) or (
        link.get("expires_at") if isinstance(link, dict) else None
    )
    if expires_at is None:
        expires_at = int(time.time()) + 3600

    return OnboardingLink(url=url, expires_at=int(expires_at))


async def get_account_status(
    *,
    client: StripeClient,
    repo: PaymentsRepo,
    ctx: SandboxContext,
    contractor_id: str,
) -> AccountStatus:
    """Read live Stripe account state and opportunistically mark onboarding complete."""

    contractor = await repo.get_contractor(contractor_id)
    if contractor is None or not contractor.stripe_account_id:
        return AccountStatus(
            has_account=False,
            charges_enabled=False,
            payouts_enabled=False,
            details_submitted=False,
            onboarding_complete=False,
            requirements={},
        )

    account = _call(client.accounts.retrieve, contractor.stripe_account_id)

    def _get(key: str, default: Any = None) -> Any:
        value = getattr(account, key, None)
        if value is None and isinstance(account, dict):
            value = account.get(key, default)
        return value if value is not None else default

    requirements = _get("requirements", {}) or {}
    if hasattr(requirements, "to_dict"):
        requirements = requirements.to_dict()

    charges_enabled = bool(_get("charges_enabled", False))
    payouts_enabled = bool(_get("payouts_enabled", False))
    details_submitted = bool(_get("details_submitted", False))
    onboarding_complete = charges_enabled and payouts_enabled and details_submitted

    if onboarding_complete and not contractor.stripe_onboarding_complete:
        await repo.mark_onboarding_complete(contractor_id)

    return AccountStatus(
        has_account=True,
        charges_enabled=charges_enabled,
        payouts_enabled=payouts_enabled,
        details_submitted=details_submitted,
        onboarding_complete=onboarding_complete,
        requirements=dict(requirements) if isinstance(requirements, dict) else {},
    )


def _accepts_params_kwarg(fn: Any) -> bool:
    """Stripe 7.x+ clients expose ``.create(params={...})`` via a typed
    signature; legacy stubs may only accept ``**kwargs``. Probe once."""

    try:
        import inspect

        sig = inspect.signature(fn)
    except (ValueError, TypeError):
        return True
    return "params" in sig.parameters


__all__ = [
    "AccountPrefill",
    "AccountResult",
    "OnboardingLink",
    "AccountStatus",
    "create_account",
    "create_onboarding_link",
    "get_account_status",
]
