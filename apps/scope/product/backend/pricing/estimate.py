"""Multi-layer cost estimate — the :func:`estimate_cost` orchestrator.

Resolution chain (first successful layer wins; market data attached as
cross-check to recipe/CYPE paths):

- **Layer 0 — Historical**: if ``contractor_id`` provided AND
  ``pricing_historical_jobs`` has 5+ matches with tight IQR, use
  contractor's past data.
- **Layer 1 — Recipe**: curated ``residential_recipes.json`` match.
- **Layer 2 — CYPE**: FTS5 cost-of-inputs + INE material-price drift
  + chapter markup.
- **Layer 3 — Market**: Habitissimo + CronoShare FTS5 fallback.

Modifier string coercion, regional-city adjustment, and the fallback
policy are all package-owned. Hermes wrapper degenerates to ~40 LOC.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

from . import config
from .cype_index import search_cype
from .errors import PricingError, QueryEmptyError
from .historical import estimate_from_history
from .ine_categories import ine_category_for_cype_code, ine_category_for_query
from .ine_drift import compute_ine_material_drift
from .markup import markup_for_chapter, material_fraction_for_chapter
from .modifiers import apply_modifiers, regional_multiplier
from .price_lookup import lookup_market
from .recipes import find_recipe
from .types import (
    CypeItem,
    Estimate,
    EstimateLine,
    IneDriftInfo,
    Recipe,
)

logger = logging.getLogger(__name__)

__all__ = ["estimate_cost"]


def _safe_lookup_market(query: str, city: str = "") -> str:
    """Best-effort market lookup for cross-check; return "" on any error."""

    try:
        report = lookup_market(query, city=city, max_results=3)
        return report.as_llm_text()
    except PricingError:
        return ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("market lookup failed: %s", exc)
        return ""


def _empty_estimate(query: str, note: str) -> Estimate:
    return Estimate(
        ok=False,
        source="none",
        query=query,
        recipe=None,
        cype_items=[],
        market_data="",
        historical=None,
        ine_drift=None,
        estimate=None,
        key_variables=[],
        note=note,
    )


def _apply_regional(
    base_eur: float,
    city: str,
) -> tuple[float, float]:
    """Apply the regional multiplier; return (adjusted, multiplier)."""

    if not city:
        return base_eur, 1.0
    mult = regional_multiplier(city)
    return round(base_eur * mult, 2), mult


# --------------------------------- layer 1: recipe ----------------------------

def _recipe_layer(
    recipe: Recipe,
    *,
    query: str,
    quantity: Optional[float],
    unit: Optional[str],
    city: str,
    modifiers: Union[None, str, List[str]],
) -> Estimate:
    iva_rate = recipe.iva_rate or 0.10
    market_range = recipe.market_range_eur or {}
    market_min = float(market_range.get("min", recipe.unit_cost_eur))
    market_max = float(market_range.get("max", recipe.unit_cost_eur * 2))

    market_mid = (market_min + market_max) / 2
    market_mid_mods, applied_mods = apply_modifiers(market_mid, modifiers)

    market_mid_adj, regional_mult = _apply_regional(market_mid_mods, city)

    mod_factor = market_mid_adj / market_mid if market_mid else 1.0
    adj_min = round(market_min * mod_factor, 2)
    adj_max = round(market_max * mod_factor, 2)

    recipe_unit = unit or recipe.unit or "Ud"

    total_eur = None
    iva_amount_eur = None
    total_with_iva = None
    if quantity is not None:
        total_eur = round(market_mid_adj * quantity, 2)
        iva_amount_eur = round(total_eur * iva_rate, 2)
        total_with_iva = round(total_eur + iva_amount_eur, 2)

    estimate_line = EstimateLine(
        unit_cost_eur=round(market_mid_adj, 2),
        unit=recipe_unit,
        quantity=quantity,
        total_eur=total_eur,
        range_min_eur=adj_min,
        range_max_eur=adj_max,
        iva_rate=iva_rate,
        iva_amount_eur=iva_amount_eur,
        total_with_iva_eur=total_with_iva,
        modifiers_applied=applied_mods,
        regional_multiplier_applied=regional_mult,
    )

    if quantity:
        note = (
            f"Matched recipe '{recipe.title_en}'. "
            f"Market estimate for {quantity} {recipe_unit}: "
            f"€{adj_min * quantity:.0f}-€{adj_max * quantity:.0f} "
            f"(+{iva_rate*100:.0f}% IVA). "
            f"Cost-of-inputs (materials + labour): "
            f"~€{recipe.unit_cost_eur}/{recipe_unit}; "
            f"market multiplier ~{recipe.market_multiplier}x."
        )
    else:
        note = (
            f"Matched recipe '{recipe.title_en}'. "
            f"Unit market price: €{adj_min}-€{adj_max}/{recipe_unit} "
            f"(+{iva_rate*100:.0f}% IVA). "
            f"Cost-of-inputs (materials + labour): "
            f"~€{recipe.unit_cost_eur}/{recipe_unit}. "
            f"Need: {', '.join(recipe.key_variables)} to give total estimate."
        )

    market_data = _safe_lookup_market(query, city=city)

    return Estimate(
        ok=True,
        source="recipe",
        query=query,
        recipe=recipe,
        cype_items=[],
        market_data=market_data,
        historical=None,
        ine_drift=None,
        estimate=estimate_line,
        key_variables=list(recipe.key_variables),
        note=note,
    )


# --------------------------------- layer 2: CYPE + INE ------------------------

def _find_ine_category(item: CypeItem, query: str) -> Optional[str]:
    """Map a CYPE item to an INE category slug, preferring material codes."""

    for material in item.materials:
        code = material.get("code") if isinstance(material, dict) else None
        if not code:
            continue
        slug = ine_category_for_cype_code(str(code))
        if slug:
            return slug

    return ine_category_for_query(query)


def _cype_layer(
    items: List[CypeItem],
    *,
    query: str,
    quantity: Optional[float],
    unit: Optional[str],
    city: str,
    modifiers: Union[None, str, List[str]],
) -> Estimate:
    best = items[0]
    base_cost = best.total_price or 0
    cype_unit = unit or best.unit or "Ud"

    ine_slug = _find_ine_category(best, query)
    ine_mult = compute_ine_material_drift(ine_slug) if ine_slug else 1.0
    material_fraction = material_fraction_for_chapter(best.chapter)

    drift_adjusted = base_cost * (
        (1 - material_fraction) + material_fraction * ine_mult
    )

    ine_drift_info: Optional[IneDriftInfo] = None
    if ine_slug and abs(ine_mult - 1.0) > 0.001:
        ine_drift_info = IneDriftInfo(
            category=ine_slug,
            drift_multiplier=ine_mult,
            material_fraction_applied=material_fraction,
            original_cost_eur=float(base_cost),
            adjusted_cost_eur=round(drift_adjusted, 2),
            note=(
                f"INE material index ({ine_slug}) shows "
                f"{(ine_mult-1)*100:+.1f}% change over the last 3 months. "
                f"Applied to {int(material_fraction*100)}% material fraction."
            ),
        )

    markup = markup_for_chapter(best.chapter)

    market_estimate = round(drift_adjusted * markup.mid, 2)
    market_estimate_mods, applied_mods = apply_modifiers(
        market_estimate, modifiers,
    )
    market_estimate_adj, regional_mult = _apply_regional(
        market_estimate_mods, city,
    )

    iva_rate = 0.10

    total_eur = None
    iva_amount_eur = None
    total_with_iva = None
    if quantity is not None:
        total_eur = round(market_estimate_adj * quantity, 2)
        iva_amount_eur = round(total_eur * iva_rate, 2)
        total_with_iva = round(total_eur + iva_amount_eur, 2)

    range_min = round(drift_adjusted * markup.min, 2)
    range_max = round(drift_adjusted * markup.max, 2)

    estimate_line = EstimateLine(
        unit_cost_eur=market_estimate_adj,
        unit=cype_unit,
        quantity=quantity,
        total_eur=total_eur,
        range_min_eur=range_min,
        range_max_eur=range_max,
        iva_rate=iva_rate,
        iva_amount_eur=iva_amount_eur,
        total_with_iva_eur=total_with_iva,
        modifiers_applied=applied_mods,
        regional_multiplier_applied=regional_mult,
    )

    ine_note = (
        f" Material prices ({ine_slug}) have moved "
        f"{(ine_mult-1)*100:+.1f}% recently (INE)."
        if ine_drift_info else ""
    )

    note = (
        f"Reference match: '{best.title}' ({best.code}). "
        f"Cost-of-inputs: €{base_cost}/{cype_unit} "
        "(materials + labour, based on Convenio rates and market tariffs). "
        f"Estimated contractor price (~{markup.mid}x markup): "
        f"€{market_estimate_adj}/{cype_unit}.{ine_note}"
    )

    market_data = _safe_lookup_market(query, city=city)

    return Estimate(
        ok=True,
        source="construction_db",
        query=query,
        recipe=None,
        cype_items=items[:3],
        market_data=market_data,
        historical=None,
        ine_drift=ine_drift_info,
        estimate=estimate_line,
        key_variables=["quantity", "area_m2"] if not quantity else [],
        note=note,
    )


# --------------------------------- layer 3: market ----------------------------

def _market_layer(query: str, city: str) -> Optional[Estimate]:
    market_data = _safe_lookup_market(query, city=city)
    if not market_data or "No pricing data found" in market_data:
        return None

    return Estimate(
        ok=True,
        source="market",
        query=query,
        recipe=None,
        cype_items=[],
        market_data=market_data,
        historical=None,
        ine_drift=None,
        estimate=None,
        key_variables=["quantity", "area_m2"],
        note=(
            f"No recipe match for '{query}'. "
            "Market data from Spanish renovation marketplaces below. "
            "Ask for area/quantity to give a total estimate."
        ),
    )


# --------------------------------- orchestrator -------------------------------

def _safe_historical(trade: str, contractor_id: Optional[str]) -> Optional[Estimate]:
    """Run Layer 0 synchronously — fires the async query on a private loop."""

    if not contractor_id:
        return None

    try:
        return asyncio.run(
            estimate_from_history(trade, contractor_id=contractor_id)
        )
    except RuntimeError:
        # already in a loop; skip rather than deadlock
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("historical layer skipped: %s", exc)
        return None


def estimate_cost(
    query: str,
    *,
    quantity: Optional[float] = None,
    unit: Optional[str] = None,
    city: str = "",
    modifiers: Union[None, str, List[str]] = None,
    fallback_to_market: bool = False,
    contractor_id: Optional[str] = None,
) -> Estimate:
    """Multi-layer estimate. See module docstring for resolution chain."""

    if not query or not query.strip():
        raise QueryEmptyError("estimate_cost called with empty query")

    historical = _safe_historical(query, contractor_id)
    if historical is not None:
        return historical

    recipe = find_recipe(query)
    if recipe is not None:
        return _recipe_layer(
            recipe,
            query=query,
            quantity=quantity,
            unit=unit,
            city=city,
            modifiers=modifiers,
        )

    cype_items: List[CypeItem] = []
    try:
        cype_items = search_cype(query, unit_filter=unit, limit=5)
    except PricingError as exc:
        logger.debug("CYPE search skipped: %s", exc)

    if cype_items:
        return _cype_layer(
            cype_items,
            query=query,
            quantity=quantity,
            unit=unit,
            city=city,
            modifiers=modifiers,
        )

    market = _market_layer(query, city)
    if market is not None:
        return market

    if fallback_to_market:
        return _empty_estimate(
            query,
            note=(
                f"No pricing data found for '{query}'. "
                "This may be a specialist trade or unusual scope item. "
                "Suggest the homeowner ask for itemised quotes from 2-3 contractors."
            ),
        )

    return _empty_estimate(
        query,
        note=(
            f"No pricing data found for '{query}'. "
            "This may be a specialist trade or unusual scope item."
        ),
    )
