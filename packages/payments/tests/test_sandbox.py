"""Unit tests for ``payments.sandbox``."""

from __future__ import annotations

import pytest

from payments import SandboxContext, resolve_for_quote, resolve_sandbox


class TestResolveSandbox:
    async def test_header_true_uses_test_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STRIPE_SECRET_KEY_TEST", "sk_test_abc")
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET_TEST", "whsec_test_abc")
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_xyz")
        ctx = await resolve_sandbox(x_sandbox="true", x_allow_whatsapp=None)
        assert ctx.is_sandbox is True
        assert ctx.stripe_key == "sk_test_abc"
        assert ctx.stripe_webhook_secret == "whsec_test_abc"
        assert ctx.suppress_whatsapp is True

    async def test_header_missing_uses_live_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_xyz")
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_live_xyz")
        ctx = await resolve_sandbox(x_sandbox=None, x_allow_whatsapp=None)
        assert ctx.is_sandbox is False
        assert ctx.stripe_key == "sk_live_xyz"
        assert ctx.stripe_webhook_secret == "whsec_live_xyz"
        assert ctx.suppress_whatsapp is False

    async def test_header_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STRIPE_SECRET_KEY_TEST", "sk_test")
        ctx = await resolve_sandbox(x_sandbox="TRUE", x_allow_whatsapp=None)
        assert ctx.is_sandbox is True

    async def test_sandbox_plus_allow_whatsapp_does_not_suppress(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("STRIPE_SECRET_KEY_TEST", "sk_test")
        ctx = await resolve_sandbox(x_sandbox="true", x_allow_whatsapp="true")
        assert ctx.is_sandbox is True
        assert ctx.suppress_whatsapp is False

    async def test_missing_env_yields_empty_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
        ctx = await resolve_sandbox(x_sandbox=None, x_allow_whatsapp=None)
        assert ctx.stripe_key == ""
        assert ctx.stripe_webhook_secret == ""


class TestResolveForQuote:
    def test_quote_sandbox_promotes_request(
        self, ctx_live: SandboxContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("STRIPE_SECRET_KEY_TEST", "sk_test_forced")
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET_TEST", "whsec_test_forced")
        promoted = resolve_for_quote(True, ctx_live)
        assert promoted.is_sandbox is True
        assert promoted.stripe_key == "sk_test_forced"
        assert promoted.stripe_webhook_secret == "whsec_test_forced"
        assert promoted.suppress_whatsapp is ctx_live.suppress_whatsapp

    def test_quote_live_returns_original_ctx(self, ctx_live: SandboxContext) -> None:
        result = resolve_for_quote(False, ctx_live)
        assert result is ctx_live

    def test_quote_sandbox_but_request_already_sandbox_no_change(
        self, ctx_sandbox: SandboxContext
    ) -> None:
        result = resolve_for_quote(True, ctx_sandbox)
        assert result is ctx_sandbox
