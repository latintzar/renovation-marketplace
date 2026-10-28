"""Unit tests for ``payments.client``."""

from __future__ import annotations

import pytest

from payments import SandboxContext, StripeClient, StripeNotConfigured, get_stripe_client
from payments.client import build_stripe_client_from_key


def test_stripe_client_is_runtime_checkable(stripe_client) -> None:
    assert isinstance(stripe_client, StripeClient)


def test_get_stripe_client_raises_when_key_empty() -> None:
    ctx = SandboxContext(
        is_sandbox=False,
        stripe_key="",
        stripe_webhook_secret="",
        suppress_whatsapp=False,
    )
    with pytest.raises(StripeNotConfigured):
        get_stripe_client(ctx)


def test_build_stripe_client_from_key_requires_key() -> None:
    with pytest.raises(StripeNotConfigured):
        build_stripe_client_from_key(None)
    with pytest.raises(StripeNotConfigured):
        build_stripe_client_from_key("")


def test_get_stripe_client_returns_live_sdk_client(ctx_live) -> None:
    client = get_stripe_client(ctx_live)
    assert hasattr(client, "checkout")
    assert hasattr(client, "transfers")
