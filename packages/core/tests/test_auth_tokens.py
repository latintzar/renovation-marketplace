"""Tests for :mod:`core.auth.tokens`.

Safety-critical: fail-closed in prod, dev-allow only under ``LEO_ENV=dev``.
Coverage target: 100%.
"""

from __future__ import annotations

import pytest

from core import Forbidden
from core.auth.tokens import require_ops_token, require_tracker_token


@pytest.mark.asyncio
async def test_ops_token_fail_closed_when_env_missing() -> None:
    """Invariant D8: no OPS_TOKEN + no LEO_ENV=dev → 403."""
    with pytest.raises(Forbidden) as info:
        await require_ops_token(x_ops_token="anything")
    assert info.value.code == "OPS_TOKEN_MISSING"


@pytest.mark.asyncio
async def test_ops_token_dev_fallback_opens_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invariant D8: LEO_ENV=dev with no OPS_TOKEN allows all."""
    monkeypatch.setenv("LEO_ENV", "dev")
    await require_ops_token(x_ops_token=None)  # must not raise


@pytest.mark.asyncio
async def test_ops_token_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPS_TOKEN", "secret")
    await require_ops_token(x_ops_token="secret")


@pytest.mark.asyncio
async def test_ops_token_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPS_TOKEN", "secret")
    with pytest.raises(Forbidden) as info:
        await require_ops_token(x_ops_token="wrong")
    assert info.value.code == "OPS_TOKEN_INVALID"


@pytest.mark.asyncio
async def test_ops_token_missing_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPS_TOKEN", "secret")
    with pytest.raises(Forbidden) as info:
        await require_ops_token(x_ops_token=None)
    assert info.value.code == "OPS_TOKEN_INVALID"


@pytest.mark.asyncio
async def test_tracker_token_fail_closed_when_env_missing() -> None:
    """Invariant D8: hardcoded ``leo-sales-dev-token-2026`` fallback is gone."""
    with pytest.raises(Forbidden) as info:
        await require_tracker_token(x_tracker_token="leo-sales-dev-token-2026")
    assert info.value.code == "TRACKER_TOKEN_MISSING"


@pytest.mark.asyncio
async def test_tracker_token_dev_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LEO_ENV", "dev")
    await require_tracker_token(x_tracker_token=None)


@pytest.mark.asyncio
async def test_tracker_token_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SALES_TRACKER_TOKEN", "tracker-secret")
    await require_tracker_token(x_tracker_token="tracker-secret")


@pytest.mark.asyncio
async def test_tracker_token_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SALES_TRACKER_TOKEN", "tracker-secret")
    with pytest.raises(Forbidden) as info:
        await require_tracker_token(x_tracker_token="nope")
    assert info.value.code == "TRACKER_TOKEN_INVALID"
