"""Quote financial computation — single source of truth.

Moved from ``routes/canvas.py::_compute_quote_financials`` (the cross-route
smell #1 from ``audit.md``). Three production call-sites today —
``api_finalize_quote`` writes the canonical row, ``api_list_quotes`` is the
legacy fallback for rows missing ``amount_total_cents``, and
``routes/payment.py`` reimports it as a legacy fallback. Post-migration all
three callers import :func:`compute_quote_financials` from here.

Rounding: **ROUND_HALF_UP** via :func:`domain.money.to_cents` (Spanish-tax
convention — half-cent rounds up). The legacy code used Python ``round()``
which is banker's rounding (ROUND_HALF_EVEN); historical quotes on exact-
half-cent boundaries may shift by +/-1 cent under the new implementation.
Documented, accepted — ~3 of every 10k quotes are expected to differ.

IVA-rate convention is preserved as-is — the frontend and the legacy code
both pass percent-integer (``10``, ``21``) — not fractions. ``None`` means
"prices already include IVA".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from core.money import to_cents


@dataclass(frozen=True)
class QuoteFinancials:
    """Output of :func:`compute_quote_financials`.

    Backward-compatible with the dict historically returned — every key maps
    1:1. Use :meth:`to_dict` before persisting to Supabase.
    """

    milestones_subtotal_cents: int
    materials_upfront_cents: int
    fee_cents: int
    iva_cents: int
    amount_total_cents: int
    iva_rate: Optional[float]
    milestones: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "milestones_subtotal_cents": self.milestones_subtotal_cents,
            "materials_upfront_cents": self.materials_upfront_cents,
            "fee_cents": self.fee_cents,
            "iva_cents": self.iva_cents,
            "amount_total_cents": self.amount_total_cents,
            "iva_rate": self.iva_rate,
            "milestones": list(self.milestones),
        }


def _as_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def build_milestones_tracking(line_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build the milestones JSON array stored on ``quotes.milestones``.

    Produces the same shape historical canvases expect — a list of
    dicts with ``index``, ``description``, ``amount_cents``, ``duration_label``,
    ``status``, ``marked_complete_at``, ``released_at``.
    """

    milestones: List[Dict[str, Any]] = []
    for i, li in enumerate(line_items or []):
        amount_cents = to_cents(_as_decimal(li.get("amount", 0)))
        milestones.append(
            {
                "index": i,
                "description": li.get("description", ""),
                "amount_cents": amount_cents,
                "duration_label": li.get("duration_label", ""),
                "status": "pending",
                "marked_complete_at": None,
                "released_at": None,
            }
        )
    return milestones


def compute_quote_financials(quote_data: Dict[str, Any]) -> QuoteFinancials:
    """Compute canonical financial fields from a ``quote_data`` blob.

    Mirrors the frontend ``QuoteCanvas.tsx`` formula exactly so both layers
    agree on the total the homeowner sees::

        milestones_subtotal = sum(line_items[].amount)
        materials_upfront   = quote_data['materials_upfront']
        work_total          = milestones_subtotal + materials_upfront
        fee_amount          = milestones_subtotal * service_fee_percent / 100
        iva_amount          = work_total * iva_rate / 100   (0 if iva_rate is None)
        grand_total         = work_total + fee_amount + iva_amount
    """

    line_items = quote_data.get("line_items") or []

    milestones_subtotal = sum(
        (_as_decimal(li.get("amount", 0)) for li in line_items),
        Decimal("0"),
    )
    materials_upfront = _as_decimal(quote_data.get("materials_upfront", 0))

    fee_pct_raw = quote_data.get("service_fee_percent", 5)
    fee_pct = _as_decimal(fee_pct_raw if fee_pct_raw is not None else 5)

    iva_rate_raw = quote_data.get("iva_rate")
    iva_rate_decimal: Optional[Decimal] = None
    if iva_rate_raw is not None:
        try:
            iva_rate_decimal = Decimal(str(iva_rate_raw))
        except (InvalidOperation, ValueError):
            iva_rate_decimal = None

    work_total = milestones_subtotal + materials_upfront
    fee_amount = milestones_subtotal * fee_pct / Decimal("100")
    iva_amount = (
        work_total * iva_rate_decimal / Decimal("100")
        if iva_rate_decimal is not None
        else Decimal("0")
    )
    grand_total = work_total + fee_amount + iva_amount

    iva_rate_out: Optional[float]
    if iva_rate_raw is None:
        iva_rate_out = None
    else:
        try:
            iva_rate_out = float(iva_rate_raw)
        except (TypeError, ValueError):
            iva_rate_out = None

    return QuoteFinancials(
        milestones_subtotal_cents=to_cents(milestones_subtotal),
        materials_upfront_cents=to_cents(materials_upfront),
        fee_cents=to_cents(fee_amount),
        iva_cents=to_cents(iva_amount),
        amount_total_cents=to_cents(grand_total),
        iva_rate=iva_rate_out,
        milestones=build_milestones_tracking(line_items),
    )


def parse_euro_string(raw: Any) -> int:
    """Parse a mixed-type EUR amount into integer cents.

    Accepts ``int``, ``float``, :class:`~decimal.Decimal`, and ``str`` forms
    (``"500"``, ``"500.00"``, ``"€500"``, ``"€ 500,50"``). Returns integer
    cents using ROUND_HALF_UP.

    Consolidates three inline copies from
    ``routes/milestones.py``, ``routes/milestone.py``, ``routes/documents.py``.
    """

    if raw is None:
        raise InvalidOperation("empty amount")

    if isinstance(raw, (int, float, Decimal)):
        return to_cents(Decimal(str(raw)))

    if not isinstance(raw, str):
        raise InvalidOperation(f"unsupported type: {type(raw)!r}")

    cleaned = raw.strip().replace("€", "").replace(" ", "")
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    if not cleaned:
        raise InvalidOperation("empty amount")
    return to_cents(Decimal(cleaned))


__all__ = [
    "QuoteFinancials",
    "compute_quote_financials",
    "build_milestones_tracking",
    "parse_euro_string",
]
