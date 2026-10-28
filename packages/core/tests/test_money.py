"""Unit tests for ``core.money``."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pytest

from core.money import (
    Money,
    add_iva,
    add_iva_percent,
    format_eur,
    from_cents,
    iva_amount,
    iva_amount_percent,
    strip_iva,
    strip_iva_percent,
    to_cents,
)


class TestToCents:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (10, 1000),
            (10.0, 1000),
            ("10", 1000),
            (Decimal("10"), 1000),
            (10.5, 1050),
            ("10.50", 1050),
            (Decimal("10.5"), 1050),
            (0, 0),
            (0.01, 1),
            ("0.01", 1),
        ],
    )
    def test_round_trip_clean(self, value: Money, expected: int) -> None:
        assert to_cents(value) == expected

    def test_rounding_half_up_above_5(self) -> None:
        # 10.567 → 10.57 (half-up at 2dp) → 1057
        assert to_cents("10.567") == 1057

    def test_rounding_half_up_on_exact_5(self) -> None:
        # Spanish convention: ROUND_HALF_UP rounds .005 up.
        assert to_cents(Decimal("0.005")) == 1
        assert to_cents(Decimal("1.005")) == 101

    def test_negative_value(self) -> None:
        assert to_cents(-10) == -1000
        assert to_cents("-10.50") == -1050

    def test_float_noise_dodged(self) -> None:
        # 0.1 as a binary float is 0.1000…0005551. str() bridges cleanly.
        assert to_cents(0.1) == 10


class TestFromCents:
    def test_basic_conversion(self) -> None:
        assert from_cents(1057) == Decimal("10.57")

    def test_zero(self) -> None:
        assert from_cents(0) == Decimal("0.00")

    def test_negative(self) -> None:
        assert from_cents(-1057) == Decimal("-10.57")

    def test_always_two_places(self) -> None:
        result = from_cents(100)
        assert str(result) == "1.00"

    def test_rejects_non_int(self) -> None:
        with pytest.raises(TypeError, match="cents must be int"):
            from_cents(10.5)  # type: ignore[arg-type]

    def test_rejects_decimal(self) -> None:
        with pytest.raises(TypeError, match="cents must be int"):
            from_cents(Decimal("10"))  # type: ignore[arg-type]

    def test_rejects_string(self) -> None:
        with pytest.raises(TypeError, match="cents must be int"):
            from_cents("1057")  # type: ignore[arg-type]


class TestAddIVA:
    def test_general_rate(self) -> None:
        assert add_iva(100, 0.21) == Decimal("121.00")

    def test_reduced_rate(self) -> None:
        assert add_iva(100, 0.10) == Decimal("110.00")

    def test_returns_decimal(self) -> None:
        assert isinstance(add_iva(100, 0.21), Decimal)

    def test_accepts_string_rate(self) -> None:
        assert add_iva(100, "0.21") == Decimal("121.00")

    def test_accepts_string_amount(self) -> None:
        assert add_iva("100.00", Decimal("0.21")) == Decimal("121.00")

    def test_rounding(self) -> None:
        # 33.333 * 1.21 = 40.33293 → 40.33
        assert add_iva("33.333", "0.21") == Decimal("40.33")

    def test_zero_rate_is_identity(self) -> None:
        assert add_iva(100, 0) == Decimal("100.00")


class TestStripIVA:
    def test_inverse_of_add(self) -> None:
        assert strip_iva(121, 0.21) == Decimal("100.00")

    def test_reduced_rate(self) -> None:
        assert strip_iva(110, 0.10) == Decimal("100.00")

    def test_returns_decimal(self) -> None:
        assert isinstance(strip_iva(121, 0.21), Decimal)


class TestIVAAmount:
    def test_general_rate(self) -> None:
        assert iva_amount(100, 0.21) == Decimal("21.00")

    def test_reduced_rate(self) -> None:
        assert iva_amount(100, 0.10) == Decimal("10.00")

    def test_sum_matches_add_iva(self) -> None:
        net = Decimal("100")
        rate = Decimal("0.21")
        assert iva_amount(net, rate) + net == add_iva(net, rate)


class TestPercentWrappers:
    def test_add_iva_percent_21(self) -> None:
        assert add_iva_percent(100, 21) == Decimal("121.00")

    def test_strip_iva_percent_21(self) -> None:
        assert strip_iva_percent(121, 21) == Decimal("100.00")

    def test_iva_amount_percent_10(self) -> None:
        assert iva_amount_percent(100, 10) == Decimal("10.00")

    def test_percent_form_matches_fraction_form(self) -> None:
        """21 via *_percent == 0.21 via non-percent."""
        assert add_iva_percent(100, 21) == add_iva(100, 0.21)
        assert strip_iva_percent(121, 21) == strip_iva(121, 0.21)

    def test_percent_accepts_string(self) -> None:
        assert add_iva_percent(100, "21") == Decimal("121.00")


class TestFormatEur:
    def test_default_is_spanish(self) -> None:
        assert format_eur(1234.56) == "1.234,56 €"

    def test_english_convention(self) -> None:
        assert format_eur(1234.56, convention="en") == "€1,234.56"

    def test_always_two_decimal_places(self) -> None:
        # design D5: cents_always — 20 → "20,00 €", never "20 €".
        assert format_eur(20) == "20,00 €"
        assert format_eur(20, convention="en") == "€20.00"

    def test_rounding_half_up(self) -> None:
        # 0.005 rounds up to 0.01.
        assert format_eur(Decimal("0.005")) == "0,01 €"

    def test_negative_spanish(self) -> None:
        assert format_eur(-1234.56) == "-1.234,56 €"

    def test_negative_english(self) -> None:
        assert format_eur(-1234.56, convention="en") == "-€1,234.56"

    def test_large_numbers_spanish(self) -> None:
        assert format_eur(1_234_567.89) == "1.234.567,89 €"

    def test_large_numbers_english(self) -> None:
        assert format_eur(1_234_567.89, convention="en") == "€1,234,567.89"

    def test_zero_spanish(self) -> None:
        assert format_eur(0) == "0,00 €"

    def test_small_amount_spanish(self) -> None:
        assert format_eur(Decimal("0.01")) == "0,01 €"

    def test_accepts_string_input(self) -> None:
        assert format_eur("100.5") == "100,50 €"

    def test_rejects_cents_always_kwarg(self) -> None:
        """design D5: cents_always param dropped."""
        with pytest.raises(TypeError):
            format_eur(20, cents_always=False)  # type: ignore[call-arg]


class TestInvalidInput:
    def test_to_cents_bad_string(self) -> None:
        with pytest.raises(InvalidOperation):
            to_cents("not a number")

    def test_add_iva_bad_string(self) -> None:
        with pytest.raises(InvalidOperation):
            add_iva("abc", 0.21)
