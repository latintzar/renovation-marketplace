"""Shared fixtures for the messaging test suite.

Principles mirror :mod:`voice.tests.conftest`:

* **Env isolation.** All messaging-relevant env vars are cleared between
  tests so nothing depends on host Meta / Resend / Supabase secrets.
* **Host-adapter reset.** :func:`messaging.clear_adapters` runs between
  tests so tool handlers never observe state from a previous test.
* **HTTP mock.** ``respx`` patches outbound requests (Meta graph API,
  Resend, Supabase REST, BOE/LexAPI, VIES).

Post-Wave-6: the agent pool lives in the scope app
(``apps/scope/product/backend/agent/``), not here, so there is no agent-pool
fixture in this conftest. Scope tests reset the pool in their own
``conftest.py``.
"""

from __future__ import annotations

import os
from typing import Iterator

import pytest

_MESSAGING_ENV_VARS = [
    "WHATSAPP_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "META_VERIFY_TOKEN",
    "RESEND_API_KEY",
    "RESEND_FROM",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "LEO_OUTREACH_DAILY_LIMIT",
    "LEO_OUTREACH_CONTACT_COOLDOWN_DAYS",
    "LEO_PHONE_ID",
    "MEM0_API_KEY",
    "MEM0_ORG_ID",
    "MEM0_PROJECT_ID",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "LITELLM_BASE_URL",
    "LITELLM_API_KEY",
    "AWS_REGION",
]


@pytest.fixture(autouse=True)
def _messaging_env_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear every messaging-related env var before each test."""
    for name in _MESSAGING_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _reset_host_adapters() -> Iterator[None]:
    """Clear any host adapters registered during a prior test."""
    from messaging import clear_adapters

    clear_adapters()
    yield
    clear_adapters()


@pytest.fixture
def stub_supabase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set dummy Supabase env so imports that eagerly read them stay happy."""
    monkeypatch.setenv("SUPABASE_URL", "https://stub.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "stub-service-role")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "stub-service-role")


@pytest.fixture
def stub_meta_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set dummy Meta/WhatsApp env for tests exercising outbound WA calls."""
    monkeypatch.setenv("WHATSAPP_TOKEN", "stub-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "000000000000")
    monkeypatch.setenv("LEO_PHONE_ID", "34600000000")


@pytest.fixture
def stub_resend_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set dummy Resend env for outbound email tests."""
    monkeypatch.setenv("RESEND_API_KEY", "stub-resend-key")
    monkeypatch.setenv("RESEND_FROM", "Leo <leo@test.casa>")
