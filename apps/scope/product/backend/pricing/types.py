"""Typed dataclasses for the :mod:`pricing` package.

Every public entry point in ``pricing`` returns one of these frozen
dataclasses. The shape is stable — these types are the contract the
hermes tool wrapper, FastAPI routes, and the front-end TypeScript port
all rely on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Mapping, Optional, Tuple


# --------------------------------- quote math --------------------------------

@dataclass(frozen=True)
class Line:
    """A single quote line item (labour/milestone).

    Stored in the ``quotes`` table as JSON inside ``quote_data.line_items[]``.
    Canonical representation is (cents-ledger, ex-IVA euros).
    """

    description: str
    amount_eur: float
    amount_cents: int
    duration_label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "amount_eur": self.amount_eur,
            "amount_cents": self.amount_cents,
            "duration_label": self.duration_label,
        }


@dataclass(frozen=True)
class QuoteDraft:
    """Input to :func:`compute_quote`.

    IVA convention — at most ONE of ``iva_rate`` (fraction, 0..1) or
    ``iva_percent`` (integer-percent, 0..100) may be provided; passing
    both raises :class:`pricing.errors.IVAConventionError`. When
    **neither** is given, IVA is **zero** — mirroring the legacy
    ``quote_data.iva_rate is None`` convention ("prices already include
    IVA / prices are gross"). Pass ``iva_percent=10`` to apply 10% IVA
    on (milestones + materials), as in the TypeScript ``computeQuoteTotals``.
    """

    line_items: List[Dict[str, Any]]
    materials_upfront_eur: float = 0.0
    service_fee_percent: float = 5.0
    iva_rate: Optional[float] = None
    iva_percent: Optional[int] = None
    currency: Literal["EUR"] = "EUR"


@dataclass(frozen=True)
class Quote:
    """Output of :func:`compute_quote`.

    All cents are integers (no float drift); euros are rounded HALF_UP
    per ``domain.money`` convention. ``iva_rate`` is stored as
    integer-percent (10, 21) to preserve the ``quotes`` table schema.
    """

    milestones_subtotal_cents: int
    materials_upfront_cents: int
    fee_cents: int
    iva_cents: int
    amount_total_cents: int
    iva_rate: int
    milestones: List[Dict[str, Any]]
    currency: Literal["EUR"] = "EUR"

    def to_quote_row(self) -> Dict[str, Any]:
        """Shape ready for Supabase ``quotes`` row INSERT/PATCH.

        Emits ``amount_total_cents``, ``materials_upfront_cents``,
        ``stripe_fee_cents``, ``iva_rate`` (integer), ``milestones`` (jsonb).
        Preserves today's column-name convention.
        """

        return {
            "amount_total_cents":       self.amount_total_cents,
            "materials_upfront_cents":  self.materials_upfront_cents,
            "stripe_fee_cents":         self.fee_cents,
            "iva_rate":                 self.iva_rate,
            "milestones":               list(self.milestones),
        }

    def format_total_eur(self) -> str:
        """Spanish-locale total with the euro sign — ``core.money.format_eur``."""

        from core.money import format_eur, from_cents

        return format_eur(from_cents(self.amount_total_cents))


@dataclass(frozen=True)
class QuoteBreakdown:
    """Detailed breakdown of a stored ``quotes`` row.

    Produced by :func:`breakdown_from_quote_row`. Used by:

    - ``routes/documents.py::_build_invoice_context`` (replaces inline
      IVA re-derivation).
    - The contractor dashboard when showing finalized-quote summaries.
    """

    work_subtotal_cents:     int
    materials_upfront_cents: int
    fee_cents:               int
    iva_cents:               int
    iva_rate:                int
    total_cents:             int
    work_subtotal_eur:       float
    iva_eur:                 float
    fee_eur:                 float
    total_eur:               float
    currency:                Literal["EUR"] = "EUR"


# --------------------------------- estimate / reference ----------------------

@dataclass(frozen=True)
class Recipe:
    """A curated ``residential_recipes.json`` entry."""

    id: str
    slug: str
    title_en: str
    title_es: str
    tags: List[str]
    unit: str
    unit_cost_eur: float
    market_multiplier: float
    market_range_eur: Dict[str, float]
    key_variables: List[str]
    cype_codes: List[str]
    iva_rate: float
    chapter: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Recipe":
        """Factory that copes with optional / extra fields in the JSON."""

        return cls(
            id=str(data.get("id", "")),
            slug=str(data.get("slug", "")),
            title_en=str(data.get("title_en", "")),
            title_es=str(data.get("title_es", "")),
            tags=[str(t) for t in data.get("tags", [])],
            unit=str(data.get("unit", "Ud")),
            unit_cost_eur=float(data.get("unit_cost_eur", 0) or 0),
            market_multiplier=float(data.get("market_multiplier", 1.6)),
            market_range_eur=dict(data.get("market_range_eur", {})),
            key_variables=[str(v) for v in data.get("key_variables", [])],
            cype_codes=[str(c) for c in data.get("cype_codes", [])],
            iva_rate=float(data.get("iva_rate", 0.10)),
            chapter=str(data.get("chapter", "")),
            raw=dict(data),
        )


@dataclass(frozen=True)
class CypeItem:
    """One BM25-ranked CYPE index row."""

    id: str
    code: str
    title: str
    description: str
    unit: str
    total_price: Optional[float]
    chapter: str
    typology: Literal["rehabilitacion", "obra_nueva", "unknown"]
    url: str
    materials: List[Dict[str, Any]]
    labour: List[Dict[str, Any]]
    bm25_score: float


@dataclass(frozen=True)
class IneDriftInfo:
    """Material price drift applied to a CYPE-sourced estimate."""

    category: str
    drift_multiplier: float
    material_fraction_applied: float
    original_cost_eur: float
    adjusted_cost_eur: float
    note: str


@dataclass(frozen=True)
class EstimateLine:
    """Typed replacement for the free-form ``result['estimate']`` dict.

    All fields refer to POST-modifier, POST-regional-adjustment values;
    raw per-recipe costs live on :class:`Recipe` or :class:`CypeItem`.
    """

    unit_cost_eur: float
    unit: str
    quantity: Optional[float]
    total_eur: Optional[float]
    range_min_eur: float
    range_max_eur: float
    iva_rate: float
    iva_amount_eur: Optional[float]
    total_with_iva_eur: Optional[float]
    modifiers_applied: List[str]
    regional_multiplier_applied: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_cost_eur": self.unit_cost_eur,
            "unit": self.unit,
            "quantity": self.quantity,
            "total_eur": self.total_eur,
            "range": {"min": self.range_min_eur, "max": self.range_max_eur},
            "iva_rate": self.iva_rate,
            "iva_amount": self.iva_amount_eur,
            "total_with_iva": self.total_with_iva_eur,
            "modifiers_applied": list(self.modifiers_applied),
            "regional_multiplier": self.regional_multiplier_applied,
        }


@dataclass(frozen=True)
class HistoricalJob:
    """One matching finalized quote from the ``pricing_historical_jobs`` view."""

    quote_id: str
    contractor_id: str
    trade: str
    province: Optional[str]
    area_m2: Optional[float]
    total_cents: int
    iva_rate: int
    materials_upfront_cents: int
    fee_cents: int
    finalized_at: Optional[datetime]
    completed_at: Optional[datetime]


@dataclass(frozen=True)
class HistoricalSummary:
    """Aggregate across matching historical jobs — attached to Estimate."""

    sample_size: int
    median_total_eur: float
    p25_total_eur: float
    p75_total_eur: float
    iqr_ratio: float
    trades: List[str]
    provinces: List[str]
    lookback_months: int


@dataclass(frozen=True)
class Estimate:
    """Output of :func:`estimate_cost` — the hermes tool contract.

    ``source`` indicates which resolution layer produced the estimate:

    - ``"historical"`` (Layer 0): matched on contractor-facing past quotes.
    - ``"recipe"`` (Layer 1): matched curated ``residential_recipes.json``.
    - ``"construction_db"`` (Layer 2): matched CYPE FTS5 + INE drift.
    - ``"market"`` (Layer 3): matched Habitissimo/CronoShare FTS5.
    - ``"none"``: no data at any layer.
    """

    ok: bool
    source: Literal["historical", "recipe", "construction_db", "market", "none"]
    query: str
    recipe: Optional[Recipe]
    cype_items: List[CypeItem]
    market_data: str
    historical: Optional[HistoricalSummary]
    ine_drift: Optional[IneDriftInfo]
    estimate: Optional[EstimateLine]
    key_variables: List[str]
    note: str

    def to_dict(self) -> Dict[str, Any]:
        """JSON-safe dict for the hermes tool envelope."""

        return {
            "ok": self.ok,
            "source": self.source,
            "query": self.query,
            "recipe": self.recipe.raw if self.recipe else None,
            "cype_items": [
                {
                    "id": c.id,
                    "code": c.code,
                    "title": c.title,
                    "description": c.description,
                    "unit": c.unit,
                    "total_price": c.total_price,
                    "chapter": c.chapter,
                    "typology": c.typology,
                    "url": c.url,
                    "materials": list(c.materials),
                    "labour": list(c.labour),
                }
                for c in self.cype_items
            ],
            "market_data": self.market_data,
            "historical": (
                {
                    "sample_size": self.historical.sample_size,
                    "median_total_eur": self.historical.median_total_eur,
                    "p25_total_eur": self.historical.p25_total_eur,
                    "p75_total_eur": self.historical.p75_total_eur,
                    "iqr_ratio": self.historical.iqr_ratio,
                    "trades": list(self.historical.trades),
                    "provinces": list(self.historical.provinces),
                    "lookback_months": self.historical.lookback_months,
                }
                if self.historical
                else None
            ),
            "ine_drift": (
                {
                    "category": self.ine_drift.category,
                    "drift_multiplier": self.ine_drift.drift_multiplier,
                    "material_fraction_applied": self.ine_drift.material_fraction_applied,
                    "adjusted_cost": self.ine_drift.adjusted_cost_eur,
                    "original_cost": self.ine_drift.original_cost_eur,
                    "note": self.ine_drift.note,
                }
                if self.ine_drift
                else None
            ),
            "estimate": self.estimate.to_dict() if self.estimate else None,
            "key_variables": list(self.key_variables),
            "note": self.note,
        }


# --------------------------------- market / product --------------------------

@dataclass(frozen=True)
class MarketReport:
    """Output of :func:`lookup_market`.

    Wraps the formatted string today's ``search_prices`` returns, plus
    structured fields the front-end or future tools can use without
    parsing the text.
    """

    query: str
    city: str
    total_results: int
    sources_used: List[str]
    national_range_eur: Optional[Tuple[float, float]]
    city_prices_eur: List[float]
    items: List[Dict[str, Any]]
    text: str = ""  # pre-formatted via `as_llm_text`

    def as_llm_text(self) -> str:
        """Formatted string — the LLM-context shape today's ``search_prices`` returns."""

        return self.text


@dataclass(frozen=True)
class Product:
    """One product row from ``products.db`` (Leroy Merlin + manufacturer scrapes)."""

    name: str
    brand: str
    category: str
    sku: str
    url: str
    price_eur: Optional[float]
    currency: Literal["EUR"] = "EUR"
    source: str = ""  # 'leroy_merlin' | 'manufacturer' | ...


@dataclass(frozen=True)
class ProductList:
    """Output of :func:`lookup_product`."""

    query: str
    category: str
    items: List[Product]
    sources_used: List[str]
    text: str = ""  # pre-formatted via `as_llm_text`

    def as_llm_text(self) -> str:
        return self.text


@dataclass(frozen=True)
class LivePrice:
    """Live-scraped SKU price. Stub today (D12); wired with scraping.

    Signatures defined now so callers don't refactor when the stub flips.
    """

    sku: str
    price_eur: float
    currency: Literal["EUR"]
    vendor: str
    url: str
    scraped_at: datetime


@dataclass(frozen=True)
class MarkupEntry:
    """Per-chapter markup bracket. See :mod:`pricing.markup`."""

    min: float
    mid: float
    max: float


__all__ = [
    "Line",
    "QuoteDraft",
    "Quote",
    "QuoteBreakdown",
    "Recipe",
    "CypeItem",
    "IneDriftInfo",
    "EstimateLine",
    "HistoricalJob",
    "HistoricalSummary",
    "Estimate",
    "MarketReport",
    "Product",
    "ProductList",
    "LivePrice",
    "MarkupEntry",
]
