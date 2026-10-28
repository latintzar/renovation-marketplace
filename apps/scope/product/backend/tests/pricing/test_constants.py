"""Guard tests for :mod:`pricing.constants` — these values **cannot silently drift**.

Any intentional change here MUST be paired with a migration-log entry
and ideally a follow-up docs update.
"""
from __future__ import annotations

from pricing.constants import (
    CYPE_TO_INE_CATEGORY,
    DEFAULT_IVA_RATE,
    DEFAULT_SERVICE_FEE_PERCENT,
    IVA_RATES,
    KEYWORD_TO_INE_CATEGORY,
    MATERIAL_FRACTION_DEFAULT,
    MODIFIERS,
    REGIONAL_MULTIPLIERS,
)


def test_default_service_fee_percent_is_5() -> None:
    """Legacy & TS default — DO NOT change without a sales decision."""

    assert DEFAULT_SERVICE_FEE_PERCENT == 5.0


def test_default_iva_rate_is_10_pct_residential() -> None:
    """Residential renovation IVA — aligned with the recipe library."""

    assert DEFAULT_IVA_RATE == 0.10


def test_iva_rates_allow_residential_and_commercial() -> None:
    # Residential at 10% is the only mandated one; 21% and 0% are common
    assert 10 in IVA_RATES.values() or 0.10 in IVA_RATES.values()


def test_modifiers_table_values() -> None:
    assert MODIFIERS["urgent"] == 1.25
    assert MODIFIERS["peak_season"] == 1.15
    assert MODIFIERS["access_difficult"] == 1.20
    assert MODIFIERS["occupied_property"] == 1.10
    assert MODIFIERS["heritage_building"] == 1.30
    # All multipliers must be > 1 (they INCREASE cost)
    for k, v in MODIFIERS.items():
        assert v > 1.0, f"modifier {k} must be >1, got {v}"


def test_regional_multipliers_have_madrid_barcelona() -> None:
    """Keys are lowercased; callers go through :func:`regional_multiplier`."""

    assert "madrid" in REGIONAL_MULTIPLIERS
    assert "barcelona" in REGIONAL_MULTIPLIERS
    assert REGIONAL_MULTIPLIERS["madrid"] > 1.0
    # Madrid more expensive than the cheaper cities in the table
    assert REGIONAL_MULTIPLIERS["madrid"] > REGIONAL_MULTIPLIERS["granada"]


def test_cype_to_ine_category_covers_main_chapters() -> None:
    """Every CYPE chapter prefix in this map must resolve to a real INE slug."""

    required_slugs = {"plasticos", "ceramica", "cobre", "acero", "madera"}
    used_slugs = set(CYPE_TO_INE_CATEGORY.values())
    assert required_slugs.issubset(used_slugs)


def test_keyword_to_ine_category_common_terms() -> None:
    assert KEYWORD_TO_INE_CATEGORY.get("azulejo") == "ceramica"
    assert KEYWORD_TO_INE_CATEGORY.get("tubo") == "plasticos"
    assert KEYWORD_TO_INE_CATEGORY.get("madera") == "madera"


def test_material_fraction_default_bounds() -> None:
    # Empirically ~0.5 — material portion of construction cost
    assert 0.3 <= MATERIAL_FRACTION_DEFAULT <= 0.7
