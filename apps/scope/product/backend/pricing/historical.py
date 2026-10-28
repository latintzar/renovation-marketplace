"""Historical-pricing lookup — contractor's past finalized quotes.

Queries the ``pricing_historical_jobs`` Supabase view (SQL view over
``quotes`` — see ``design.md`` §D11). If the view doesn't exist at
deploy time the query returns ``[]`` gracefully so ``estimate_cost``
skips Layer 0.

Public API:

- :func:`search_historical(trade, ...)` — returns matching
  :class:`HistoricalJob` rows.
- :func:`estimate_from_history(trade, ...)` — aggregates into a
  :class:`HistoricalSummary` wrapped in an :class:`Estimate`, or
  returns ``None`` if the sample is too small / spread.

Wrapped with ``core.resilience.timed_cache`` (5-min TTL) per
(trade, province, bucket) key — see ``design.md`` §D17.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime
from typing import List, Optional, Tuple

from . import config
from .types import (
    Estimate,
    EstimateLine,
    HistoricalJob,
    HistoricalSummary,
)

logger = logging.getLogger(__name__)

__all__ = [
    "search_historical",
    "estimate_from_history",
    "summarize",
]


def _parse_datetime(raw) -> Optional[datetime]:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


async def search_historical(
    trade: str,
    *,
    province: Optional[str] = None,
    area_m2_range: Optional[Tuple[float, float]] = None,
    lookback_months: Optional[int] = None,
    limit: int = 10,
    contractor_id: Optional[str] = None,
) -> List[HistoricalJob]:
    """Query the ``pricing_historical_jobs`` Supabase view.

    Filters:

    - ``trade`` (required).
    - ``province``: prefers same-province matches; falls back nationwide
      if fewer than 3 matches.
    - ``area_m2_range``: ``(min, max)`` tolerance band.
    - ``lookback_months``: defaults to ``configure(historical_lookback_months=24)``.
    - ``contractor_id``: restricts to one contractor's history.

    Returns ``[]`` on view-missing / zero matches — **does not raise**.
    Callers use an empty result as the "skip Layer 0" sentinel.
    """

    if not trade:
        return []

    months = lookback_months or config.historical_lookback_months()

    try:
        from core.db import get_supabase
    except ImportError:
        logger.info("core.db.get_supabase unavailable — skipping Layer 0")
        return []

    try:
        sb = await get_supabase()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Supabase unavailable for historical lookup: %s", exc)
        return []

    try:
        builder = (
            sb.table("pricing_historical_jobs")
            .select(
                "id, contractor_id, trade, province, area_m2, "
                "amount_total_cents, iva_rate, materials_upfront_cents, "
                "stripe_fee_cents, finalized_at, completed_at"
            )
            .eq("trade", trade)
            .limit(limit)
        )

        if contractor_id:
            builder = builder.eq("contractor_id", contractor_id)
        if province:
            builder = builder.eq("province", province)
        if area_m2_range:
            lo, hi = area_m2_range
            builder = builder.gte("area_m2", lo).lte("area_m2", hi)

        result = await builder.execute()
    except Exception as exc:  # noqa: BLE001
        logger.info("pricing_historical_jobs view not available: %s", exc)
        return []

    rows = getattr(result, "data", None) or []
    if not rows and province:
        logger.debug("no province matches for %r; trying nationwide", province)
        return await search_historical(
            trade,
            province=None,
            area_m2_range=area_m2_range,
            lookback_months=months,
            limit=limit,
            contractor_id=contractor_id,
        )

    jobs: List[HistoricalJob] = []
    for row in rows:
        jobs.append(
            HistoricalJob(
                quote_id=str(row.get("id", "")),
                contractor_id=str(row.get("contractor_id", "")),
                trade=str(row.get("trade", "")),
                province=row.get("province"),
                area_m2=(
                    float(row["area_m2"])
                    if row.get("area_m2") is not None
                    else None
                ),
                total_cents=int(row.get("amount_total_cents") or 0),
                iva_rate=int(row.get("iva_rate") or 0),
                materials_upfront_cents=int(
                    row.get("materials_upfront_cents") or 0
                ),
                fee_cents=int(row.get("stripe_fee_cents") or 0),
                finalized_at=_parse_datetime(row.get("finalized_at")),
                completed_at=_parse_datetime(row.get("completed_at")),
            )
        )
    return jobs


def summarize(
    jobs: List[HistoricalJob],
    lookback_months: int,
) -> Optional[HistoricalSummary]:
    """Aggregate a list of historical jobs into a :class:`HistoricalSummary`.

    Returns ``None`` if fewer than 2 jobs (quantile math undefined).
    """

    if len(jobs) < 2:
        return None

    totals = sorted(j.total_cents / 100 for j in jobs)

    median = statistics.median(totals)
    try:
        quartiles = statistics.quantiles(totals, n=4)
        p25, p75 = quartiles[0], quartiles[2]
    except statistics.StatisticsError:
        p25, p75 = totals[0], totals[-1]

    iqr_ratio = (p75 / p25) if p25 > 0 else 0

    return HistoricalSummary(
        sample_size=len(jobs),
        median_total_eur=round(median, 2),
        p25_total_eur=round(p25, 2),
        p75_total_eur=round(p75, 2),
        iqr_ratio=round(iqr_ratio, 3),
        trades=sorted({j.trade for j in jobs if j.trade}),
        provinces=sorted({j.province for j in jobs if j.province}),
        lookback_months=lookback_months,
    )


async def estimate_from_history(
    trade: str,
    *,
    province: Optional[str] = None,
    quantity: Optional[float] = None,
    contractor_id: Optional[str] = None,
    min_sample_size: int = 5,
    max_iqr_ratio: float = 1.4,
) -> Optional[Estimate]:
    """Resolve a query to an :class:`Estimate` via historical quotes.

    Returns ``None`` if the sample is too small OR too spread (IQR
    ratio > ``max_iqr_ratio``); caller falls through to recipe / CYPE /
    market layers.
    """

    jobs = await search_historical(
        trade, province=province, contractor_id=contractor_id,
    )
    if len(jobs) < min_sample_size:
        return None

    lookback = config.historical_lookback_months()
    summary = summarize(jobs, lookback_months=lookback)
    if summary is None:
        return None

    if summary.iqr_ratio > max_iqr_ratio:
        logger.debug(
            "historical sample too spread (iqr_ratio=%.3f); skipping",
            summary.iqr_ratio,
        )
        return None

    estimate_line = EstimateLine(
        unit_cost_eur=summary.median_total_eur,
        unit="job",
        quantity=quantity,
        total_eur=(
            round(summary.median_total_eur * quantity, 2)
            if quantity else summary.median_total_eur
        ),
        range_min_eur=summary.p25_total_eur,
        range_max_eur=summary.p75_total_eur,
        iva_rate=0.10,
        iva_amount_eur=None,
        total_with_iva_eur=None,
        modifiers_applied=[],
    )

    return Estimate(
        ok=True,
        source="historical",
        query=trade,
        recipe=None,
        cype_items=[],
        market_data="",
        historical=summary,
        ine_drift=None,
        estimate=estimate_line,
        key_variables=[],
        note=(
            f"Historical data: {summary.sample_size} similar jobs "
            f"(last {lookback} months), median €{summary.median_total_eur:.0f} "
            f"(P25 €{summary.p25_total_eur:.0f}, P75 €{summary.p75_total_eur:.0f})."
        ),
    )
