"""Shared fixtures for `documents` tests."""
from __future__ import annotations

from datetime import date

import pytest

from documents import (
    InvoicePayload,
    JobInfo,
    Milestone,
    Money,
    PartyInfo,
    QuotePayload,
    VariationPayload,
)


@pytest.fixture
def homeowner() -> PartyInfo:
    return PartyInfo(
        name="Ana García",
        email="ana@example.com",
        phone="+34 600 111 222",
    )


@pytest.fixture
def contractor() -> PartyInfo:
    return PartyInfo(
        name="Bob el Constructor",
        email="bob@build.com",
        trade="Albañilería",
        address="Calle del Pez 10, Madrid",
    )


@pytest.fixture
def job() -> JobInfo:
    return JobInfo(
        title="Reforma de cocina",
        address="Calle Mayor 1, Madrid",
        description="Renovación completa de la cocina.",
    )


@pytest.fixture
def milestones() -> list[Milestone]:
    return [
        Milestone(title="Demolición", amount=Money.from_euros("500")),
        Milestone(title="Obra principal", amount=Money.from_euros("1500")),
    ]


@pytest.fixture
def quote_payload(
    homeowner: PartyInfo,
    contractor: PartyInfo,
    job: JobInfo,
    milestones: list[Milestone],
) -> QuotePayload:
    return QuotePayload(
        quote_token="sample-quote",
        homeowner=homeowner,
        contractor=contractor,
        job=job,
        milestones=milestones,
        total=Money.from_euros("2000"),
        leo_fee=Money.from_euros("100"),
        materials_upfront=Money.from_euros("300"),
        iva_rate_pct=0,
        agreement_date=date(2026, 4, 18),
    )


@pytest.fixture
def invoice_payload(
    homeowner: PartyInfo,
    contractor: PartyInfo,
    job: JobInfo,
) -> InvoicePayload:
    return InvoicePayload(
        quote_token="sample-quote",
        homeowner=homeowner,
        contractor=contractor,
        job=job,
        milestones=[
            Milestone(
                title="Demolición",
                amount=Money.from_euros("500"),
                released_at=date(2026, 4, 10),
            ),
            Milestone(
                title="Obra principal",
                amount=Money.from_euros("1500"),
                released_at=date(2026, 4, 15),
            ),
        ],
        materials_upfront=Money.from_euros("300"),
        leo_fee=Money.from_euros("100"),
        iva_rate_pct=21,
        total=Money.from_euros("2420"),
        completion_date=date(2026, 4, 18),
        payment_intent_id="pi_test_abc",
    )


@pytest.fixture
def variation_payload(
    homeowner: PartyInfo,
    contractor: PartyInfo,
    job: JobInfo,
) -> VariationPayload:
    return VariationPayload(
        quote_token="sample-quote",
        variation_id="v_001",
        homeowner=homeowner,
        contractor=contractor,
        job=job,
        change_summary="Añadir 5 enchufes y nivelar suelo.",
        milestones_delta=[
            Milestone(title="Enchufes extra", amount=Money.from_euros("300")),
            Milestone(title="Nivelado de suelo", amount=Money.from_euros("200")),
        ],
        delta_total=Money.from_euros("500"),
        variation_date=date(2026, 4, 19),
    )
