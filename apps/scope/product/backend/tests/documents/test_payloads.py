"""Unit tests for `documents.payloads` — Money arithmetic + Pydantic validation."""
from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from documents import (
    DocumentKind,
    Locale,
    Milestone,
    Money,
    PartyInfo,
    QuotePayload,
)


# -------------------------------------------------------------------- Money --


class TestMoney:
    def test_from_cents(self) -> None:
        m = Money(cents=123456)
        assert m.cents == 123456
        assert m.euros == Decimal("1234.56")

    def test_from_euros_accepts_decimal(self) -> None:
        m = Money.from_euros(Decimal("1234.56"))
        assert m.cents == 123456

    def test_from_euros_accepts_float(self) -> None:
        m = Money.from_euros(1234.56)
        assert m.cents == 123456

    def test_from_euros_accepts_string(self) -> None:
        m = Money.from_euros("1234.56")
        assert m.cents == 123456

    def test_str_is_spanish_locale(self) -> None:
        m = Money(cents=123456)
        assert str(m) == "1.234,56 €"

    def test_zero(self) -> None:
        m = Money(cents=0)
        assert m.euros == Decimal("0.00")
        assert str(m) == "0,00 €"

    def test_frozen(self) -> None:
        m = Money(cents=100)
        with pytest.raises(ValidationError):
            m.cents = 200  # type: ignore[misc]

    def test_add(self) -> None:
        assert (Money(cents=100) + Money(cents=50)).cents == 150

    def test_sub(self) -> None:
        assert (Money(cents=100) - Money(cents=40)).cents == 60

    def test_multiply_by_int(self) -> None:
        assert (Money(cents=100) * 3).cents == 300

    def test_rmultiply_by_decimal(self) -> None:
        result = Decimal("0.21") * Money(cents=100000)
        assert result.cents == 21000

    def test_negative_cents_allowed(self) -> None:
        m = Money(cents=-500)
        assert m.euros == Decimal("-5.00")


# -------------------------------------------------------------- Milestone ----


class TestMilestone:
    def test_minimal(self) -> None:
        m = Milestone(title="Demolición", amount=Money.from_euros(500))
        assert m.title == "Demolición"
        assert m.amount.cents == 50000
        assert m.released_at is None

    def test_with_released_at(self) -> None:
        from datetime import date

        m = Milestone(
            title="Obra",
            amount=Money.from_euros(500),
            released_at=date(2026, 4, 10),
        )
        assert m.released_at == date(2026, 4, 10)

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            Milestone(
                title="X", amount=Money.from_euros(100), extra_field="boom"
            )  # type: ignore[call-arg]


# -------------------------------------------------------------- PartyInfo ----


class TestPartyInfo:
    def test_minimal(self) -> None:
        p = PartyInfo(name="Ana", email="a@b.com")
        assert p.phone is None
        assert p.address is None
        assert p.trade is None

    def test_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            PartyInfo(name="A", email="a@b.c", foo="bar")  # type: ignore[call-arg]


# ---------------------------------------------------------- QuotePayload ----


class TestQuotePayload:
    def test_all_fields_present(self, quote_payload: QuotePayload) -> None:
        assert quote_payload.quote_token == "sample-quote"
        assert quote_payload.total.cents == 200000
        assert len(quote_payload.milestones) == 2
        assert quote_payload.legal_review_tag == "v1-2026-04"


# ------------------------------------------------------------------- Enums ---


class TestEnums:
    def test_locale_values(self) -> None:
        assert Locale.ES.value == "es"

    def test_document_kind_values(self) -> None:
        assert DocumentKind.AGREEMENT.value == "agreement"
        assert DocumentKind.INVOICE.value == "invoice"
        assert DocumentKind.VARIATION.value == "variation"
