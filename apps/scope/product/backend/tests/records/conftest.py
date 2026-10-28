"""Shared fixtures for the :mod:`records` tests.

Every test is hermetic: no live Supabase, no live LiteLLM proxy. We mock
the two external surfaces records depends on:

- **Supabase REST** via :mod:`respx` against ``sb_url()``.
- **LiteLLM proxy** via ``monkeypatch`` of :func:`llm.embed` and
  :func:`llm.chat` — records only ever consumes these from the public
  ``llm`` surface so patching the top-level binding is sufficient.

The ``env_isolated`` autouse fixture strips all Supabase + LiteLLM env
vars before each test so a leaky ``.env.local`` can't flip a test
result. Individual tests opt-in to the env they need via the
``supabase_env`` / ``llm_env`` fixtures.

Split out from ``packages/storage/tests/conftest.py`` in Phase 5 Wave 3
when the scope-specific storage modules (leads / proposals / dossier /
conversations) moved to ``apps/scope/product/backend/records/``.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List
from unittest.mock import MagicMock

import pytest

_LEAKY_ENV_VARS = (
    "SUPABASE_URL",
    "NEXT_PUBLIC_SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "NEXT_PUBLIC_SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_SERVICE_KEY",
    "LITELLM_BASE_URL",
    "LITELLM_API_KEY",
    "LLM_PROXY_URL",
    "LLM_PROXY_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
)


@pytest.fixture(autouse=True)
def env_isolated(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Strip env vars before each test."""

    for var in _LEAKY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    for key in list(os.environ):
        if key.startswith("AWS_ACCESS_KEY_ID") or key.startswith("AWS_SECRET_ACCESS_KEY"):
            monkeypatch.delenv(key, raising=False)
    yield


@pytest.fixture()
def supabase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Populate deterministic Supabase env vars for tests that hit REST."""

    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")


@pytest.fixture()
def llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Populate LiteLLM proxy vars so :mod:`llm.config` resolves."""

    monkeypatch.setenv("LITELLM_BASE_URL", "https://proxy.test")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test-proxy")


@pytest.fixture()
def fake_llm_chat(monkeypatch: pytest.MonkeyPatch):
    """Patch :func:`llm.chat` to return a deterministic summary text.

    Used by ``summarize_recent`` tests. The first call answer is
    ``"[summary 1]"``, the second ``"[summary 2]"``, etc.
    """

    calls: List[Dict[str, Any]] = []

    async def fake(*args, **kwargs):
        idx = len(calls)
        calls.append({"args": args, "kwargs": kwargs})

        class R:
            content = f"[summary {idx + 1}]"
            raw = {}

        return R()

    import llm as _llm

    monkeypatch.setattr(_llm, "chat", fake)
    fake.calls = calls  # type: ignore[attr-defined]
    return fake


@pytest.fixture()
def now_utc() -> datetime:
    """A fixed, timezone-aware 'now' for deterministic tests."""

    return datetime(2026, 4, 20, 12, 0, 0, tzinfo=timezone.utc)


def iso(dt: datetime) -> str:
    """ISO-8601 ``Z``-suffix format Supabase returns."""

    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@pytest.fixture()
def iso_ts() -> Any:
    return iso
