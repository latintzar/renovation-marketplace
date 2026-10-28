"""Smoke tests for :mod:`pricing.types` — frozen dataclass shapes."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from pricing import (
    CypeItem,
    Estimate,
    EstimateLine,
    HistoricalJob,
    HistoricalSummary,
    IneDriftInfo,
    Line,
    LivePrice,
    MarketReport,
    MarkupEntry,
    Product,
    ProductList,
    Quote,
    QuoteBreakdown,
    QuoteDraft,
    Recipe,
)


def test_line_frozen() -> None:
    line = Line(description="x", amount_eur=10.0, amount_cents=1000)
    with pytest.raises(FrozenInstanceError):
        line.amount_cents = 2000  # type: ignore[misc]


def test_quote_to_quote_row_all_fields() -> None:
    q = Quote(
        milestones_subtotal_cents=1000,
        materials_upfront_cents=200,
        fee_cents=50,
        iva_cents=100,
        amount_total_cents=1350,
        iva_rate=10,
        milestones=[{"index": 0}],
    )
    row = q.to_quote_row()
    assert set(row.keys()) == {
        "amount_total_cents",
        "materials_upfront_cents",
        "stripe_fee_cents",
        "iva_rate",
        "milestones",
    }


def test_quote_draft_default_fee_is_5_pct() -> None:
    d = QuoteDraft(line_items=[])
    assert d.service_fee_percent == 5.0
    assert d.materials_upfront_eur == 0.0
    assert d.iva_rate is None
    assert d.iva_percent is None
    assert d.currency == "EUR"


def test_recipe_from_dict_populates_required_fields() -> None:
    r = Recipe.from_dict({
        "id": "r1",
        "slug": "paint-flat",
        "title_en": "Paint flat",
        "title_es": "Pintar piso",
        "tags": ["paint"],
        "unit": "m2",
        "unit_cost_eur": 10.0,
        "market_range_eur": {"min": 8, "max": 12},
        "iva_rate": 0.10,
        "cype_codes": ["RPP010"],
        "key_variables": ["size"],
    })
    assert r.id == "r1"
    assert r.slug == "paint-flat"
    assert r.unit_cost_eur == 10.0
    assert r.market_multiplier == 1.6  # default
    assert r.iva_rate == 0.10
    assert "RPP010" in r.cype_codes


def test_recipe_from_dict_handles_missing() -> None:
    r = Recipe.from_dict({})
    assert r.id == ""
    assert r.unit_cost_eur == 0.0
    assert r.market_multiplier == 1.6
    assert r.iva_rate == 0.10


def test_estimate_to_dict_shape_recipe_source() -> None:
    line = EstimateLine(
        unit_cost_eur=10.0,
        unit="m2",
        quantity=50,
        total_eur=500.0,
        range_min_eur=400.0,
        range_max_eur=600.0,
        iva_rate=0.10,
        iva_amount_eur=50.0,
        total_with_iva_eur=550.0,
        modifiers_applied=[],
    )
    est = Estimate(
        ok=True,
        source="recipe",
        query="test",
        recipe=None,
        cype_items=[],
        market_data="",
        historical=None,
        ine_drift=None,
        estimate=line,
        key_variables=["size"],
        note="",
    )
    d = est.to_dict()
    assert d["source"] == "recipe"
    assert d["estimate"]["unit_cost_eur"] == 10.0
    assert d["estimate"]["range"] == {"min": 400.0, "max": 600.0}
    assert d["key_variables"] == ["size"]


def test_ine_drift_info_shape() -> None:
    info = IneDriftInfo(
        category="ceramica",
        drift_multiplier=1.02,
        material_fraction_applied=0.5,
        original_cost_eur=100.0,
        adjusted_cost_eur=101.0,
        note="test",
    )
    assert info.category == "ceramica"
    assert info.drift_multiplier == 1.02


def test_market_report_as_llm_text() -> None:
    mr = MarketReport(
        query="q",
        city="Madrid",
        total_results=3,
        sources_used=["habitissimo"],
        national_range_eur=(100, 200),
        city_prices_eur=[150],
        items=[],
        text="formatted text",
    )
    assert mr.as_llm_text() == "formatted text"


def test_product_list_as_llm_text() -> None:
    pl = ProductList(query="q", category="c", items=[], sources_used=[], text="txt")
    assert pl.as_llm_text() == "txt"


def test_product_defaults() -> None:
    p = Product(name="x", brand="b", category="c", sku="s", url="u", price_eur=None)
    assert p.currency == "EUR"
    assert p.source == ""


def test_live_price_shape() -> None:
    lp = LivePrice(
        sku="s", price_eur=9.99, currency="EUR", vendor="v",
        url="u", scraped_at=datetime(2026, 4, 1),
    )
    assert lp.sku == "s"


def test_markup_entry_shape() -> None:
    m = MarkupEntry(min=1.3, mid=1.6, max=2.2)
    assert m.min == 1.3
    assert m.mid == 1.6
    assert m.max == 2.2


def test_historical_job_shape() -> None:
    j = HistoricalJob(
        quote_id="q", contractor_id="c", trade="paint", province="Madrid",
        area_m2=80, total_cents=100_000, iva_rate=10,
        materials_upfront_cents=0, fee_cents=5000,
        finalized_at=None, completed_at=None,
    )
    assert j.total_cents == 100_000


def test_historical_summary_shape() -> None:
    s = HistoricalSummary(
        sample_size=5,
        median_total_eur=3000,
        p25_total_eur=2500,
        p75_total_eur=3500,
        iqr_ratio=0.3,
        trades=["paint"],
        provinces=["Madrid"],
        lookback_months=12,
    )
    assert s.sample_size == 5
    assert s.iqr_ratio == 0.3


def test_cype_item_shape() -> None:
    c = CypeItem(
        id="1", code="RPP010", title="t", description="d", unit="m2",
        total_price=10.0, chapter="Revestimientos", typology="rehabilitacion",
        url="", materials=[], labour=[], bm25_score=1.5,
    )
    assert c.code == "RPP010"


def test_quote_breakdown_shape() -> None:
    br = QuoteBreakdown(
        work_subtotal_cents=1000,
        materials_upfront_cents=200,
        fee_cents=50,
        iva_cents=100,
        iva_rate=10,
        total_cents=1350,
        work_subtotal_eur=10.0,
        iva_eur=1.0,
        fee_eur=0.5,
        total_eur=13.5,
    )
    assert br.currency == "EUR"
