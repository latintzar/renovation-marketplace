"""
leo_agent/tools/pricing.py — Renovation pricing and product catalog tools.

Tools: lookup_price, lookup_product
"""

from __future__ import annotations

import json
import logging

from ..tool_utils import _record_activity, _send_indicator

logger = logging.getLogger(__name__)


# ── Handlers ─────────────────────────────────────────────────────────

def _handle_lookup_price(args: dict, **kw) -> str:
    """Look up renovation/construction prices from Habitissimo + CronoShare databases."""
    query = str(args.get("query", "")).strip()
    city = str(args.get("city", "")).strip()
    location_suffix = f" in {city}" if city else ""
    _record_activity("lookup_price", f"Checking pricing: {query}{location_suffix}…")
    _send_indicator("lookup_price", f"_Checking pricing data: {query}{location_suffix}…_")

    if not query:
        return json.dumps({"ok": False, "error": "query is required"})

    from pricing.price_lookup import search_prices
    result = search_prices(query, city=city)
    return json.dumps({"ok": True, "data": result}, ensure_ascii=False)


def _handle_estimate_cost(args: dict, **kw) -> str:
    """Multi-layer cost estimator: curated recipes → construction cost DB → market data."""
    query = str(args.get("query", "")).strip()
    city = str(args.get("city", "") or "").strip()
    quantity = args.get("quantity")
    unit = str(args.get("unit", "") or "").strip() or None
    modifiers = args.get("modifiers") or []
    if isinstance(modifiers, str):
        modifiers = [m.strip() for m in modifiers.split(",") if m.strip()]

    location_suffix = f" in {city}" if city else ""
    _record_activity("estimate_cost", f"Estimating cost: {query}{location_suffix}…")
    _send_indicator("estimate_cost", f"_Checking market prices: {query}{location_suffix}…_")

    if not query:
        return json.dumps({"ok": False, "error": "query is required"})

    try:
        from pricing.price_engine import estimate_cost
        result = estimate_cost(
            query=query,
            quantity=float(quantity) if quantity is not None else None,
            unit=unit or None,
            city=city,
            modifiers=list(modifiers),
        )
        return json.dumps({"ok": True, "data": result}, ensure_ascii=False)
    except Exception as exc:
        logger.warning("estimate_cost failed for %r: %s", query, exc, exc_info=True)
        # Graceful fallback to lookup_price
        from pricing.price_lookup import search_prices
        fallback = search_prices(query, city=city)
        return json.dumps({"ok": True, "data": fallback, "note": "estimate_cost unavailable, using lookup_price"}, ensure_ascii=False)


def _handle_lookup_product(args: dict, **kw) -> str:
    """Search 199K Spanish construction products by name, brand, or model."""
    query = str(args.get("query", "")).strip()
    category = str(args.get("category", "")).strip()
    cat_suffix = f" ({category})" if category else ""
    _record_activity("lookup_product", f"Searching product catalog: {query}{cat_suffix}…")
    _send_indicator("lookup_product", f"_Searching product catalog: {query}{cat_suffix}…_")

    if not query:
        return json.dumps({"ok": False, "error": "query is required"})

    from pricing.product_lookup import search_products
    result = search_products(query, category=category)
    return json.dumps({"ok": True, "data": result}, ensure_ascii=False)


# ── Schemas ───────────────────────────────────────────────────────────

LOOKUP_PRICE_SCHEMA = {
    "name": "lookup_price",
    "description": (
        "Look up renovation and construction prices from Spanish market databases "
        "(Habitissimo, CronoShare, residential recipe templates, Spanish construction cost index). "
        "Use for any pricing question — always call this before estimating costs. "
        "Returns market ranges with source attribution."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to price (e.g. 'bathroom renovation', 'replace boiler', 'paint living room 20m2')",
            },
            "city": {
                "type": "string",
                "description": "City or region for localised pricing (optional)",
            },
        },
        "required": ["query"],
    },
}

LOOKUP_PRODUCT_SCHEMA = {
    "name": "lookup_product",
    "description": (
        "Search ~199K Spanish construction and renovation products by name, brand, or model number. "
        "Use when a homeowner or tradesperson mentions a specific product, brand, or model "
        "and you need specs, typical price, or alternatives."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Product name, brand, or model (e.g. 'Roca Victoria', 'Vaillant ecoTEC', 'porcelain floor tile')",
            },
            "category": {
                "type": "string",
                "description": "Optional category filter (e.g. 'boiler', 'tile', 'pipe')",
            },
        },
        "required": ["query"],
    },
}


ESTIMATE_COST_SCHEMA = {
    "name": "estimate_cost",
    "description": (
        "Estimate the cost of a renovation or construction task using Spanish market data. "
        "Multi-layer resolution: curated recipe templates (fastest) → construction cost-of-inputs index "
        "(materials + labour breakdown) → Habitissimo/CronoShare real market prices. "
        "Call this to sanity-check contractor prices or suggest market rates. "
        "Prices are exclusive of IVA (10% for residential renovation)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Description of the work (e.g. 'bathroom renovation', 'replace shower tray', 'install electric boiler 80L')",
            },
            "city": {
                "type": "string",
                "description": "Spanish city for market-localised pricing (optional, e.g. 'Madrid', 'Marbella')",
            },
            "quantity": {
                "type": "number",
                "description": "Numeric quantity if known (e.g. 12 for 12 m², 1 for a single unit job)",
            },
            "unit": {
                "type": "string",
                "description": "Unit of measurement (e.g. 'm2', 'm', 'Ud')",
            },
            "modifiers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional price modifiers: access_difficult, peak_season, occupied_property, urgent, heritage_building, rural",
            },
        },
        "required": ["query"],
    },
}


# ── Registration ──────────────────────────────────────────────────────

def register(registry) -> None:
    registry.register(
        name="lookup_price",
        toolset="leo-quote",
        schema=LOOKUP_PRICE_SCHEMA,
        handler=_handle_lookup_price,
        check_fn=lambda: True,
    )
    registry.register(
        name="estimate_cost",
        toolset="leo-quote",
        schema=ESTIMATE_COST_SCHEMA,
        handler=_handle_estimate_cost,
        check_fn=lambda: True,
    )
    registry.register(
        name="lookup_product",
        toolset="leo-quote",
        schema=LOOKUP_PRODUCT_SCHEMA,
        handler=_handle_lookup_product,
        check_fn=lambda: True,
    )
    logger.debug("pricing tools registered (lookup_price, estimate_cost, lookup_product)")
