"""``pricing`` — scope app's single source of truth for every euro number.

Lives at ``apps/scope/product/backend/pricing/`` (demoted from ``packages/pricing``
in Phase 5 Wave 4 — Spanish CYPE/INE/Habitissimo data is scope-policy, not
a shared capability). Because ``apps/scope/product/backend/`` is on ``PYTHONPATH``
for the scope backend, ``from pricing import ...`` still resolves cleanly.

Two bright-line public entry points:

- :func:`compute_quote(draft)` — deterministic quote arithmetic (line
  items + materials + fee + IVA). Pure math, no I/O. Golden-vector
  tested against the TypeScript port in the canvas.
- :func:`estimate_cost(query, ...)` — multi-layer reference pricing
  (historical → recipe → CYPE + INE drift → market). Produces a typed
  :class:`Estimate` consumed by the hermes tool wrapper.

Everything else in the public surface is either a building block these
two call internally (``search_cype``, ``lookup_market``, ``markup_for_chapter``)
or a narrow-purpose helper (``lookup_product``, ``overhead_model``).

Top-level symbols are curated (~40); reach past this layer via
``from pricing.<submodule> import ...`` only when you really need granular
access.
"""
from __future__ import annotations

from .config import (
    close_connections,
    configure,
)
from .constants import (
    CYPE_TO_INE_CATEGORY,
    DEFAULT_IVA_RATE,
    DEFAULT_SERVICE_FEE_PERCENT,
    IVA_RATES,
    MODIFIERS,
    REGIONAL_MULTIPLIERS,
)
from .cype_index import search_cype
from .errors import (
    IVAConventionError,
    IndexNotFoundError,
    MarkupLookupError,
    PricingError,
    QueryEmptyError,
)
from .estimate import estimate_cost
from .historical import (
    estimate_from_history,
    search_historical,
)
from .ine_categories import ine_category_for_query
from .ine_drift import compute_ine_material_drift
from .markup import (
    DEFAULT_MARKUP_BY_CHAPTER,
    FALLBACK_MARKUP,
    markup_for_chapter,
)
from .materials import lookup_live_price
from .modifiers import (
    apply_modifiers,
    regional_multiplier,
)
from .overhead import overhead_model
from .price_lookup import lookup_market
from .product_lookup import lookup_product
from .quote import (
    breakdown_from_quote_row,
    compute_line,
    compute_quote,
)
from .recipes import find_recipe
from .types import (
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

__all__ = [
    # bright-line entry points
    "compute_quote",
    "estimate_cost",
    # quote math building blocks
    "compute_line",
    "breakdown_from_quote_row",
    # reference-pricing building blocks
    "lookup_market",
    "lookup_product",
    "search_cype",
    "search_historical",
    "estimate_from_history",
    "lookup_live_price",
    "overhead_model",
    # helpers
    "apply_modifiers",
    "regional_multiplier",
    "markup_for_chapter",
    "compute_ine_material_drift",
    "ine_category_for_query",
    "find_recipe",
    # types — quote
    "Quote",
    "QuoteDraft",
    "QuoteBreakdown",
    "Line",
    # types — estimate
    "Estimate",
    "EstimateLine",
    "HistoricalJob",
    "HistoricalSummary",
    "IneDriftInfo",
    # types — indices / catalogs
    "MarketReport",
    "Product",
    "ProductList",
    "CypeItem",
    "Recipe",
    "LivePrice",
    "MarkupEntry",
    # constants
    "MODIFIERS",
    "REGIONAL_MULTIPLIERS",
    "DEFAULT_SERVICE_FEE_PERCENT",
    "DEFAULT_IVA_RATE",
    "IVA_RATES",
    "DEFAULT_MARKUP_BY_CHAPTER",
    "FALLBACK_MARKUP",
    "CYPE_TO_INE_CATEGORY",
    # errors
    "PricingError",
    "IndexNotFoundError",
    "QueryEmptyError",
    "IVAConventionError",
    "MarkupLookupError",
    # config
    "configure",
    "close_connections",
]
