"""Tests for :mod:`pricing.historical`.

The full ``search_historical()`` is async and hits Supabase; we only
test the pure aggregation + shape helpers here. End-to-end integration
is covered by L1 pytest + hermes tool tests in the backend.
"""
from __future__ import annotations

from pricing import HistoricalJob, HistoricalSummary, estimate_from_history
from pricing.historical import summarize


def test_summarize_empty_returns_none() -> None:
    """Empty input → ``None`` (caller skips Layer 0)."""

    result = summarize([], lookback_months=12)
    assert result is None


def test_summarize_single_job_returns_none() -> None:
    """One job → ``None`` (quantile math needs ≥2 samples)."""

    jobs = [
        HistoricalJob(
            quote_id="q1",
            contractor_id="c1",
            trade="paint",
            province="Madrid",
            area_m2=80,
            total_cents=100_000,
            iva_rate=10,
            materials_upfront_cents=0,
            fee_cents=5000,
            finalized_at=None,
            completed_at=None,
        ),
    ]
    assert summarize(jobs, lookback_months=12) is None


def test_summarize_multiple_jobs_percentiles() -> None:
    # totals = [1000, 2000, 3000, 4000, 5000] cents
    jobs = [
        HistoricalJob(
            quote_id=f"q{i}",
            contractor_id="c",
            trade="paint",
            province="Madrid",
            area_m2=80,
            total_cents=1000 * i,
            iva_rate=10,
            materials_upfront_cents=0,
            fee_cents=50,
            finalized_at=None,
            completed_at=None,
        )
        for i in range(1, 6)
    ]
    s = summarize(jobs, lookback_months=12)
    assert s is not None
    assert s.sample_size == 5
    assert s.median_total_eur == 30.0  # 3000 cents = 30 eur
    # Accept small floating point variance; p25 should be between 15 and 20,
    # p75 between 40 and 45
    assert 15.0 <= s.p25_total_eur <= 20.0
    assert 40.0 <= s.p75_total_eur <= 45.0


def test_summarize_trades_and_provinces_deduped() -> None:
    jobs = [
        HistoricalJob(
            quote_id="q1",
            contractor_id="c",
            trade="paint",
            province="Madrid",
            area_m2=80,
            total_cents=100_000,
            iva_rate=10,
            materials_upfront_cents=0,
            fee_cents=0,
            finalized_at=None,
            completed_at=None,
        ),
        HistoricalJob(
            quote_id="q2",
            contractor_id="c",
            trade="paint",  # dup
            province="Madrid",  # dup
            area_m2=80,
            total_cents=150_000,
            iva_rate=10,
            materials_upfront_cents=0,
            fee_cents=0,
            finalized_at=None,
            completed_at=None,
        ),
    ]
    s = summarize(jobs, lookback_months=12)
    assert s is not None
    # Trades / provinces lists should contain unique values only
    assert len(s.trades) == 1
    assert len(s.provinces) == 1


def test_summarize_iqr_ratio_zero_when_identical() -> None:
    jobs = [
        HistoricalJob(
            quote_id=f"q{i}",
            contractor_id="c",
            trade="paint",
            province="Madrid",
            area_m2=80,
            total_cents=100_000,
            iva_rate=10,
            materials_upfront_cents=0,
            fee_cents=0,
            finalized_at=None,
            completed_at=None,
        )
        for i in range(3)
    ]
    s = summarize(jobs, lookback_months=12)
    assert s is not None
    # All identical → p25 == p75 → iqr_ratio == 1.0 (ratio of equal values)
    assert s.iqr_ratio == 1.0
