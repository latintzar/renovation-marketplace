"""Shared fixtures for `packages/core` unit tests.

Every test runs in an isolated environment:

- ``env_isolated``: autouse fixture that strips Leo-specific env vars,
  neutralises ``.env.local`` reload, and clears every cached module in
  :mod:`core` so tests don't leak state.
- ``supabase_env``: populates a deterministic Supabase URL/key so
  :mod:`core.db` returns predictable values.
- ``respx_mock``: convenience alias for :mod:`respx` routing.
"""

from __future__ import annotations

import os
from typing import Iterator

import pytest

# Env vars core reads; stripped before each test and restored after.
_LEO_ENV_VARS = (
    "SUPABASE_URL",
    "NEXT_PUBLIC_SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "NEXT_PUBLIC_SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_SERVICE_KEY",
    "OPS_TOKEN",
    "SALES_TRACKER_TOKEN",
    "LEO_ENV",
    "LEO_AWS_ACCOUNT",
    "LEO_DISABLE_JWT_CACHE",
    "LEO_JWT_CACHE_TTL",
    "LEO_JWT_CACHE_SIZE",
)


@pytest.fixture(autouse=True)
def env_isolated(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Strip Leo env vars + clear caches + neutralise .env.local reload.

    Without this fixture, tests pick up real ``.env.local`` values every
    time ``core.aws._load_env_local()`` runs. By patching that helper to
    a no-op for the test, we guarantee env isolation.
    """
    for var in _LEO_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    # Strip any AWS suffixed creds present in the shell/.env.local —
    # tests either set their own or expect absence.
    for key in list(os.environ):
        if key.startswith("AWS_ACCESS_KEY_ID") or key.startswith("AWS_SECRET_ACCESS_KEY"):
            monkeypatch.delenv(key, raising=False)

    # Patch the ``.env.local`` reloader so tests stay hermetic.
    import core.aws as _aws

    monkeypatch.setattr(_aws, "_load_env_local", lambda: None)

    # Clear cached resources that read env at module load or first call.
    from core.auth.jwt import clear_jwt_cache

    _aws.clear_leo_aws_credential_cache()
    clear_jwt_cache()
    yield


@pytest.fixture()
def supabase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Populate deterministic Supabase env vars."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
