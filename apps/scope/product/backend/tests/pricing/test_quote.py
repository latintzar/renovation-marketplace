"""Golden-vector tests for :mod:`pricing.quote`.

These are the **deterministic parity tests** that guard the migration:
every vector below was cross-checked against

1. the legacy ``routes/canvas.py::_compute_quote_financials`` and
2. the TypeScript ``computeQuoteTotals`` in
   ``apps/scope/product/web/src/lib/utils.ts``.

If any of these break, the migration has a silent financial-parity bug.
"""
from __future__ import annotations

import pytest

from pricing import (
    IVAConventionError,
    Line,
    Quote,
    QuoteBreakdown,
    QuoteDraft,
    breakdown_from_quote_row,
    compute_line,
    compute_quote,
)


# ----------------------------- compute_line ----------------------------------

def test_compute_line_basic() -> None:
    line = compute_line("Demolition", 1234.56, duration_label="Week 1")
    assert isinstance(line, Line)
    assert line.description == "Demolition"
    assert line.amount_eur == 1234.56
    assert line.amount_cents == 123456
    assert line.duration_label == "Week 1"


def test_compute_line_half_up_rounding() -> None:
    # 12.345 rounds HALF_UP to 12.35 = 1235 cents (Decimal, not banker's)
    line = compute_line("Edge", 12.345)
    assert line.amount_cents == 1235


def test_compute_line_zero() -> None:
    line = compute_line("", 0)
    assert line.amount_cents == 0
    assert line.amount_eur == 0.0


# ----------------------------- compute_quote (parity) -------------------------

def _draft(
    *,
    line_items,
    materials=0.0,
    fee=5.0,
    iva_rate=None,
    iva_percent=None,
) -> QuoteDraft:
    return QuoteDraft(
        line_items=line_items,
        materials_upfront_eur=materials,
        service_fee_percent=fee,
        iva_rate=iva_rate,
        iva_percent=iva_percent,
    )


def test_single_milestone_no_iva() -> None:
    """No IVA (None + None) → zero IVA, matching the legacy convention."""

    q = compute_quote(_draft(line_items=[{"description": "a", "amount": 3000}]))
    # TS: labour=3000, mat=0, fee=150, iva=0, total=3150
    assert q.milestones_subtotal_cents == 300_000
    assert q.materials_upfront_cents == 0
    assert q.fee_cents == 15_000
    assert q.iva_cents == 0
    assert q.amount_total_cents == 315_000
    assert q.iva_rate == 0


def test_single_milestone_with_iva_10pct() -> None:
    q = compute_quote(
        _draft(line_items=[{"description": "a", "amount": 3000}], iva_percent=10)
    )
    # TS: labour=3000, mat=0, fee=150, iva=300, total=3450
    assert q.milestones_subtotal_cents == 300_000
    assert q.fee_cents == 15_000
    assert q.iva_cents == 30_000
    assert q.amount_total_cents == 345_000
    assert q.iva_rate == 10


def test_milestones_plus_materials_with_iva_10pct() -> None:
    """Fee on milestones only; IVA on (milestones + materials)."""

    q = compute_quote(
        _draft(
            line_items=[{"description": "a", "amount": 3000}],
            materials=500,
            fee=5,
            iva_percent=10,
        )
    )
    # TS: labour=3000, mat=500, fee=150, iva=(3000+500)*0.10=350, total=4000
    assert q.milestones_subtotal_cents == 300_000
    assert q.materials_upfront_cents == 50_000
    assert q.fee_cents == 15_000
    assert q.iva_cents == 35_000
    assert q.amount_total_cents == 400_000


def test_multi_milestone_custom_fee() -> None:
    q = compute_quote(
        _draft(
            line_items=[
                {"description": "P1", "amount": 1200},
                {"description": "P2", "amount": 2800},
            ],
            materials=1500,
            fee=7.5,
            iva_percent=10,
        )
    )
    # labour=4000, mat=1500, fee=300, iva=(4000+1500)*0.10=550, total=6350
    assert q.milestones_subtotal_cents == 400_000
    assert q.materials_upfront_cents == 150_000
    assert q.fee_cents == 30_000
    assert q.iva_cents == 55_000
    assert q.amount_total_cents == 635_000


def test_iva_21_pct() -> None:
    """21% IVA — commercial / industrial."""

    q = compute_quote(
        _draft(line_items=[{"description": "a", "amount": 1000}], iva_percent=21)
    )
    assert q.iva_cents == 21_000  # 1000 * 0.21 * 100
    assert q.iva_rate == 21


def test_iva_rate_as_fraction() -> None:
    """``iva_rate=0.21`` must produce the same result as ``iva_percent=21``."""

    q = compute_quote(
        _draft(line_items=[{"description": "a", "amount": 1000}], iva_rate=0.21)
    )
    assert q.iva_cents == 21_000
    assert q.iva_rate == 21


def test_iva_rate_zero_equiv_to_none() -> None:
    q = compute_quote(
        _draft(line_items=[{"description": "a", "amount": 1000}], iva_percent=0)
    )
    assert q.iva_cents == 0
    assert q.iva_rate == 0


def test_zero_line_items() -> None:
    """Empty milestones → everything zero. Edge case — draft saving."""

    q = compute_quote(_draft(line_items=[]))
    assert q.milestones_subtotal_cents == 0
    assert q.fee_cents == 0
    assert q.iva_cents == 0
    assert q.amount_total_cents == 0


def test_milestones_tracking_shape() -> None:
    q = compute_quote(
        _draft(
            line_items=[
                {"description": "Phase 1", "amount": 1000, "duration_label": "Week 1"},
                {"description": "Phase 2", "amount": 2000},
            ]
        )
    )
    assert len(q.milestones) == 2
    assert q.milestones[0] == {
        "index": 0,
        "description": "Phase 1",
        "amount_cents": 100_000,
        "duration_label": "Week 1",
        "status": "pending",
        "marked_complete_at": None,
        "released_at": None,
    }
    assert q.milestones[1]["index"] == 1
    assert q.milestones[1]["amount_cents"] == 200_000


def test_amount_aliases_eur_and_total() -> None:
    """Legacy line-items sometimes use ``amount_eur`` or ``total`` instead."""

    q = compute_quote(_draft(line_items=[{"description": "", "amount_eur": 1500}]))
    assert q.milestones_subtotal_cents == 150_000

    q = compute_quote(_draft(line_items=[{"description": "", "total": 750}]))
    assert q.milestones_subtotal_cents == 75_000


def test_amount_coerced_string_ok() -> None:
    """Legacy quote_data may carry strings (from form inputs)."""

    q = compute_quote(_draft(line_items=[{"description": "", "amount": "500.50"}]))
    assert q.milestones_subtotal_cents == 50_050


def test_amount_coerced_invalid_is_zero() -> None:
    q = compute_quote(_draft(line_items=[{"description": "", "amount": "junk"}]))
    assert q.milestones_subtotal_cents == 0


# ----------------------------- validation ------------------------------------

def test_both_iva_rate_and_iva_percent_raises() -> None:
    with pytest.raises(IVAConventionError, match="only one of iva_rate or iva_percent"):
        compute_quote(_draft(line_items=[], iva_rate=0.10, iva_percent=10))


def test_iva_rate_out_of_range_raises() -> None:
    with pytest.raises(IVAConventionError, match=r"iva_rate must be in \[0, 1\]"):
        compute_quote(_draft(line_items=[], iva_rate=21))


def test_iva_percent_out_of_range_raises() -> None:
    with pytest.raises(IVAConventionError, match=r"iva_percent must be in \[0, 100\]"):
        compute_quote(_draft(line_items=[], iva_percent=150))


# ----------------------------- to_quote_row ----------------------------------

def test_to_quote_row_shape() -> None:
    q = compute_quote(
        _draft(
            line_items=[{"description": "a", "amount": 1000}],
            materials=200,
            fee=5,
            iva_percent=10,
        )
    )
    row = q.to_quote_row()
    assert row == {
        "amount_total_cents":      q.amount_total_cents,
        "materials_upfront_cents": q.materials_upfront_cents,
        "stripe_fee_cents":        q.fee_cents,
        "iva_rate":                q.iva_rate,
        "milestones":              q.milestones,
    }


def test_format_total_eur() -> None:
    q = compute_quote(_draft(line_items=[{"description": "", "amount": 1234.56}]))
    total_str = q.format_total_eur()
    # format_eur shape; just assert it contains a euro sign and the number
    assert "€" in total_str or "EUR" in total_str


# ----------------------------- breakdown_from_quote_row ---------------------

def test_breakdown_from_row_with_iva() -> None:
    """Round-trip: compute → to_quote_row → breakdown_from_quote_row."""

    q = compute_quote(
        _draft(
            line_items=[{"description": "a", "amount": 1000}],
            materials=200,
            fee=5,
            iva_percent=10,
        )
    )
    row = q.to_quote_row()
    br = breakdown_from_quote_row(row)

    assert isinstance(br, QuoteBreakdown)
    assert br.fee_cents == q.fee_cents
    assert br.total_cents == q.amount_total_cents
    assert br.materials_upfront_cents == q.materials_upfront_cents
    assert br.iva_rate == 10
    # The work subtotal should decode back roughly to milestones+materials
    # (ex-IVA), and IVA should be non-zero.
    assert br.iva_cents > 0
    assert br.work_subtotal_cents + br.iva_cents + br.fee_cents == br.total_cents


def test_breakdown_from_row_without_iva() -> None:
    q = compute_quote(_draft(line_items=[{"description": "a", "amount": 1000}]))
    br = breakdown_from_quote_row(q.to_quote_row())
    assert br.iva_cents == 0
    assert br.iva_rate == 0
    assert br.work_subtotal_cents + br.fee_cents == br.total_cents


def test_breakdown_handles_missing_fields() -> None:
    br = breakdown_from_quote_row({})
    assert br.total_cents == 0
    assert br.work_subtotal_cents == 0
    assert br.iva_cents == 0


def test_breakdown_handles_none_iva_rate() -> None:
    br = breakdown_from_quote_row({
        "amount_total_cents": 121_000,
        "stripe_fee_cents": 0,
        "iva_rate": None,
    })
    assert br.iva_cents == 0
    assert br.work_subtotal_cents == 121_000
