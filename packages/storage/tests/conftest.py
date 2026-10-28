"""Shared fixtures for the :mod:`storage` package tests.

Every test is hermetic: no live Supabase, no live mem0, no live LiteLLM
proxy. We mock the three external surfaces memory depends on:

- **Supabase REST** via :mod:`respx` against ``sb_url()``.
- **mem0 SaaS** via :mod:`respx` against ``api.mem0.ai`` + ``unittest.mock``
  for the ``MemoryClient.add`` / ``MemoryClient.delete`` thread-pooled
  write calls.
- **LiteLLM proxy** via ``monkeypatch`` of :func:`llm.embed.embed` and
  :func:`llm.chat.chat` — memory only ever consumes these from the public
  ``llm`` surface so patching the top-level binding is sufficient.

The ``env_isolated`` autouse fixture strips all Supabase + mem0 + LiteLLM
env vars before each test so a leaky ``.env.local`` can't flip a test
result. Individual tests opt-in to the env they need via the
``supabase_env`` / ``mem0_env`` / ``llm_env`` fixtures.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List
from unittest.mock import AsyncMock, MagicMock

import pytest

_LEAKY_ENV_VARS = (
    "SUPABASE_URL",
    "NEXT_PUBLIC_SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "NEXT_PUBLIC_SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_SERVICE_KEY",
    "MEM0_API_KEY",
    "LITELLM_BASE_URL",
    "LITELLM_API_KEY",
    "LLM_PROXY_URL",
    "LLM_PROXY_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
)


@pytest.fixture(autouse=True)
def env_isolated(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Strip env vars + reset mem0 module state before each test."""

    for var in _LEAKY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    for key in list(os.environ):
        if key.startswith("AWS_ACCESS_KEY_ID") or key.startswith("AWS_SECRET_ACCESS_KEY"):
            monkeypatch.delenv(key, raising=False)

    import storage.semantic as _sem

    _sem._mem0_client = None
    _sem._mem0_init_failed = False
    yield
    _sem._mem0_client = None
    _sem._mem0_init_failed = False


@pytest.fixture()
def supabase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Populate deterministic Supabase env vars for tests that hit REST."""

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")


@pytest.fixture()
def mem0_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Populate a fake MEM0_API_KEY so ``is_mem0_configured`` returns True."""

    monkeypatch.setenv("MEM0_API_KEY", "mem0-test-key")


@pytest.fixture()
def llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Populate LiteLLM proxy vars so :mod:`llm.config` resolves."""

    monkeypatch.setenv("LITELLM_BASE_URL", "https://proxy.test")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test-proxy")


@pytest.fixture()
def fake_mem0_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace :func:`storage.semantic._get_client` with a stub.

    The stub records every ``add`` / ``delete`` call so tests can assert
    on invocation order, ``user_id`` passing, ``infer=False`` on migration,
    etc. Returns the :class:`MagicMock` instance so tests can inspect it.
    """

    import storage.semantic as _sem

    stub = MagicMock()
    stub.add = MagicMock()
    stub.delete = MagicMock()
    monkeypatch.setattr(_sem, "_get_client", lambda: stub)
    return stub


@pytest.fixture()
def fake_llm_embed(monkeypatch: pytest.MonkeyPatch):
    """Patch :func:`llm.embed` to return deterministic unit-length vectors.

    Returns a factory that records every call for assertions. Each call
    returns ``[[0.0] * EMBED_DIM, ...]`` by default, with the last element
    a 1.0 so vectors are non-zero.
    """

    from storage.embeddings import EMBED_DIM

    calls: List[List[str]] = []

    async def fake(texts, *, model=None, client=None):
        calls.append(list(texts))
        out: List[List[float]] = []
        for _ in texts:
            vec = [0.0] * EMBED_DIM
            vec[-1] = 1.0
            out.append(vec)
        return out

    import llm as _llm

    monkeypatch.setattr(_llm, "embed", fake)
    fake.calls = calls  # type: ignore[attr-defined]
    return fake


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
