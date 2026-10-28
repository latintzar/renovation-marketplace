"""Unit tests for ``payments.finance`` — the quote math."""

from __future__ import annotations

import pytest
from decimal import InvalidOperation

from payments import (
    QuoteFinancials,
    build_milestones_tracking,
    compute_quote_financials,
    parse_euro_string,
)


class TestComputeQuoteFinancials:
    def test_basic_computation(self) -> None:
        result = compute_quote_financials(
            {
                "line_items": [
                    {"description": "Demo", "amount": 500},
                    {"description": "Tiles", "amount": 500},
                ],
                "service_fee_percent": 5,
                "iva_rate": 21,
            }
        )
        assert result.milestones_subtotal_cents == 100_000
        assert result.materials_upfront_cents == 0
        assert result.fee_cents == 5_000
        assert result.iva_cents == 21_000
        assert result.amount_total_cents == 126_000
        assert result.iva_rate == 21.0
        assert len(result.milestones) == 2

    def test_with_materials_upfront(self) -> None:
        result = compute_quote_financials(
            {
                "line_items": [{"description": "Labour", "amount": 1000}],
                "materials_upfront": 200,
                "service_fee_percent": 5,
                "iva_rate": 10,
            }
        )
        assert result.milestones_subtotal_cents == 100_000
        assert result.materials_upfront_cents == 20_000
        assert result.fee_cents == 5_000
        assert result.iva_cents == 12_000
        assert result.amount_total_cents == 137_000

    def test_iva_rate_none_means_included(self) -> None:
        result = compute_quote_financials(
            {
                "line_items": [{"description": "Work", "amount": 1000}],
                "service_fee_percent": 5,
                "iva_rate": None,
            }
        )
        assert result.iva_cents == 0
        assert result.iva_rate is None
        assert result.amount_total_cents == 105_000

    def test_default_service_fee_percent(self) -> None:
        result = compute_quote_financials(
            {"line_items": [{"description": "X", "amount": 1000}]}
        )
        assert result.fee_cents == 5_000

    def test_empty_line_items(self) -> None:
        result = compute_quote_financials({"line_items": [], "iva_rate": 21})
        assert result.milestones_subtotal_cents == 0
        assert result.amount_total_cents == 0
        assert result.milestones == []

    def test_fractional_amounts_round_half_up(self) -> None:
        result = compute_quote_financials(
            {
                "line_items": [{"description": "Half", "amount": 10.005}],
                "service_fee_percent": 0,
                "iva_rate": None,
            }
        )
        assert result.milestones_subtotal_cents == 1001

    def test_to_dict_shape_is_backward_compatible(self) -> None:
        result = compute_quote_financials(
            {
                "line_items": [{"description": "D", "amount": 100}],
                "iva_rate": 21,
            }
        )
        d = result.to_dict()
        assert set(d.keys()) == {
            "milestones_subtotal_cents",
            "materials_upfront_cents",
            "fee_cents",
            "iva_cents",
            "amount_total_cents",
            "iva_rate",
            "milestones",
        }


class TestBuildMilestonesTracking:
    def test_status_is_pending_by_default(self) -> None:
        ms = build_milestones_tracking(
            [{"description": "A", "amount": 100, "duration_label": "1 day"}]
        )
        assert ms[0]["status"] == "pending"
        assert ms[0]["marked_complete_at"] is None
        assert ms[0]["released_at"] is None

    def test_preserves_order_and_indices(self) -> None:
        ms = build_milestones_tracking(
            [
                {"description": "A", "amount": 100},
                {"description": "B", "amount": 200},
                {"description": "C", "amount": 300},
            ]
        )
        assert [m["index"] for m in ms] == [0, 1, 2]
        assert [m["description"] for m in ms] == ["A", "B", "C"]
        assert [m["amount_cents"] for m in ms] == [10_000, 20_000, 30_000]

    def test_empty_input(self) -> None:
        assert build_milestones_tracking([]) == []


class TestParseEuroString:
    @pytest.mark.parametrize("raw,expected", [
        (500, 50_000),
        (500.5, 50_050),
        ("500", 50_000),
        ("500.00", 50_000),
        ("€500", 50_000),
        ("€ 500,50", 50_050),
        ("500,50", 50_050),
        ("1,500.00", 150_000),
    ])
    def test_parses_variants(self, raw, expected) -> None:
        assert parse_euro_string(raw) == expected

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidOperation):
            parse_euro_string(None)

    def test_empty_string_raises(self) -> None:
        with pytest.raises(InvalidOperation):
            parse_euro_string("")

    def test_garbage_raises(self) -> None:
        with pytest.raises(InvalidOperation):
            parse_euro_string("not a number")
