"""Unit tests for :mod:`scrapers.directories`."""
from __future__ import annotations

from typing import Sequence

import pytest

from scrapers import ContractorLead, search


def test_lead_defaults() -> None:
    lead = ContractorLead()
    assert lead.name == ""
    assert lead.phone == ""
    assert lead.raw_data == {}


def test_lead_phone_normalization_spanish() -> None:
    lead = ContractorLead(phone="+34 612 345 678")
    assert lead.phone_normalized == "612345678"
    assert lead.is_valid_phone


def test_lead_phone_normalization_invalid() -> None:
    """``normalize`` strips punctuation before deciding; validity check on
    the stripped form. ``abc`` has no digits → invalid."""

    lead = ContractorLead(phone="abc")
    assert not lead.is_valid_phone


def test_lead_phone_empty() -> None:
    lead = ContractorLead()
    assert lead.phone_normalized == ""
    assert not lead.is_valid_phone


@pytest.mark.asyncio
async def test_search_dispatches_to_adapters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Per-platform adapter is invoked exactly once per platform."""

    async def _fake_habitissimo(trade: str, city: str, *, limit: int = 50):
        return [
            ContractorLead(
                name="Fontaneros Madrid", phone="+34 612 345 678", platform="habitissimo"
            )
        ]

    async def _fake_instagram(trade: str, city: str, *, limit: int = 50):
        return [
            ContractorLead(
                name="garcia_fontaneros",
                phone="+34 612 345 678",
                platform="instagram",
            ),
            ContractorLead(
                name="other", phone="+34 700 100 200", platform="instagram"
            ),
        ]

    async def _fake_houzz(trade: str, city: str, *, limit: int = 50):
        return []

    monkeypatch.setattr("scrapers.habitissimo.search", _fake_habitissimo)
    monkeypatch.setattr("scrapers.instagram.search", _fake_instagram)
    monkeypatch.setattr("scrapers.houzz.search", _fake_houzz)

    out = await search("fontaneros", "madrid")

    phones = {lead.phone_normalized for lead in out}
    assert "612345678" in phones
    assert "700100200" in phones
    assert len(out) == 2


@pytest.mark.asyncio
async def test_search_respects_platforms_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_habitissimo(trade: str, city: str, *, limit: int = 50):
        return [ContractorLead(phone="+34 600 000 001", platform="habitissimo")]

    async def _fake_other(trade: str, city: str, *, limit: int = 50):
        raise AssertionError("should not be called")

    monkeypatch.setattr("scrapers.habitissimo.search", _fake_habitissimo)
    monkeypatch.setattr("scrapers.instagram.search", _fake_other)
    monkeypatch.setattr("scrapers.houzz.search", _fake_other)

    out = await search("x", "y", platforms=["habitissimo"])
    assert len(out) == 1


@pytest.mark.asyncio
async def test_search_isolates_adapter_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One adapter raising must not break the batch."""

    async def _good(trade: str, city: str, *, limit: int = 50):
        return [ContractorLead(phone="+34 600 000 001", platform="good")]

    async def _boom(trade: str, city: str, *, limit: int = 50):
        raise RuntimeError("upstream 500")

    monkeypatch.setattr("scrapers.habitissimo.search", _good)
    monkeypatch.setattr("scrapers.instagram.search", _boom)
    monkeypatch.setattr("scrapers.houzz.search", _good)

    out = await search("t", "c")
    assert len(out) == 1


@pytest.mark.asyncio
async def test_search_no_dedup_returns_duplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With ``dedup=False``, duplicates survive across adapters."""

    async def _dup(trade: str, city: str, *, limit: int = 50):
        return [ContractorLead(phone="+34 600 000 001")]

    monkeypatch.setattr("scrapers.habitissimo.search", _dup)
    monkeypatch.setattr("scrapers.instagram.search", _dup)
    monkeypatch.setattr("scrapers.houzz.search", _dup)

    out = await search("t", "c", dedup=False)
    assert len(out) == 3
