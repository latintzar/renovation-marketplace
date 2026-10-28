"""Deterministic quote arithmetic — the canonical :func:`compute_quote`.

Pure functions. No I/O. No side effects. Replaces three duplicate inline
computations that historically lived in:

- ``routes/canvas.py::_compute_quote_financials`` — finalized-quote insert.
- ``routes/payment.py`` legacy fallback — re-derivation from scope_data.
- ``routes/documents.py::_build_invoice_context`` — IVA re-derivation for
  invoice PDFs.

All three diverged on rounding convention (banker's vs HALF_UP) and
cents ledger representation (float-math vs int-cents). :func:`compute_quote`
uses ``domain.money`` (Decimal, ROUND_HALF_UP) end-to-end, so the app,
the TypeScript front-end port, and the invoice PDF all agree to the cent.

:func:`breakdown_from_quote_row` is the read-time inverse: given a
stored ``quotes`` row, return a typed :class:`QuoteBreakdown`.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from core.money import (
    add_iva,
    format_eur,
    from_cents,
    iva_amount,
    to_cents,
)

from .errors import IVAConventionError
from .types import Line, Quote, QuoteBreakdown, QuoteDraft

__all__ = [
    "compute_line",
    "compute_quote",
    "breakdown_from_quote_row",
]


# --------------------------------- helpers ------------------------------------

def _normalise_iva(
    iva_rate: Optional[float],
    iva_percent: Optional[int],
) -> tuple[Optional[Decimal], Optional[int]]:
    """Return ``(fraction, integer_percent)`` after validation.

    ``None, None`` is allowed — callers treat it as "IVA already embedded"
    (compute_quote then computes no IVA). The return shape mirrors that:
    ``(None, None)``.

    Both given → :class:`IVAConventionError`. Out-of-range → same.
    """

    if iva_rate is not None and iva_percent is not None:
        raise IVAConventionError(
            "Pass only one of iva_rate or iva_percent, not both."
        )

    if iva_rate is None and iva_percent is None:
        return None, None

    if iva_rate is not None:
        if not (0 <= float(iva_rate) <= 1):
            raise IVAConventionError(
                f"iva_rate must be in [0, 1]; got {iva_rate!r} "
                "(hint: for 21% IVA pass 0.21 or use iva_percent=21)."
            )
        frac = Decimal(str(iva_rate))
        integer_percent = int(round(float(iva_rate) * 100))
        return frac, integer_percent

    if not (0 <= int(iva_percent) <= 100):  # type: ignore[arg-type]
        raise IVAConventionError(
            f"iva_percent must be in [0, 100]; got {iva_percent!r}."
        )
    integer_percent = int(iva_percent)  # type: ignore[arg-type]
    frac = Decimal(integer_percent) / Decimal(100)
    return frac, integer_percent


def _line_amount_eur(item: Dict[str, Any]) -> float:
    """Extract the numeric ``amount`` field from a ``line_items[]`` entry."""

    raw = item.get("amount")
    if raw is None:
        raw = item.get("amount_eur")
    if raw is None:
        raw = item.get("total")
    if raw is None:
        raw = 0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


# --------------------------------- public API ---------------------------------

def compute_line(
    description: str,
    amount_eur: Union[float, int],
    *,
    duration_label: str = "",
) -> Line:
    """Build a :class:`Line` from raw values.

    Uses ``domain.money.to_cents`` for the cents conversion (Decimal +
    HALF_UP) so front-end and back-end agree.
    """

    amount_cents = to_cents(amount_eur)
    return Line(
        description=description,
        amount_eur=float(amount_eur),
        amount_cents=amount_cents,
        duration_label=duration_label,
    )


def compute_quote(draft: QuoteDraft) -> Quote:
    """Compute quote financials deterministically from a :class:`QuoteDraft`.

    Arithmetic:

    - ``milestones_subtotal`` = sum(line_items.amount)  -> cents
    - ``materials_upfront``   = draft.materials_upfront_eur  -> cents
    - ``work_subtotal``       = milestones + materials
    - ``fee``                 = milestones * service_fee%   (fee applies
                                to work only, not materials)
    - ``iva``                 = work_subtotal * iva_rate   (IVA applies to
                                work + materials)
    - ``total``               = work_subtotal + fee + iva

    Every intermediate conversion uses ``domain.money.to_cents`` /
    ``iva_amount`` so HALF_UP is enforced end-to-end. The returned
    :class:`Quote` stores ``iva_rate`` as integer-percent (10, 21) to
    preserve the ``quotes`` table schema.
    """

    iva_frac, iva_int = _normalise_iva(draft.iva_rate, draft.iva_percent)

    milestones: List[Dict[str, Any]] = []
    milestones_subtotal_cents = 0

    for index, item in enumerate(draft.line_items):
        amount_eur = _line_amount_eur(item)
        amount_cents = to_cents(amount_eur)
        milestones_subtotal_cents += amount_cents

        milestones.append({
            "index": index,
            "description": str(item.get("description", "")),
            "amount_cents": amount_cents,
            "duration_label": str(item.get("duration_label", "")),
            "status": "pending",
            "marked_complete_at": None,
            "released_at": None,
        })

    materials_upfront_cents = to_cents(draft.materials_upfront_eur or 0)

    fee_pct = Decimal(str(draft.service_fee_percent))
    fee_eur = (
        from_cents(milestones_subtotal_cents)
        * fee_pct
        / Decimal(100)
    )
    fee_cents = to_cents(fee_eur)

    work_subtotal_cents = milestones_subtotal_cents + materials_upfront_cents
    work_subtotal_eur = from_cents(work_subtotal_cents)

    if iva_frac is None or iva_frac == 0:
        iva_cents = 0
    else:
        iva_eur = iva_amount(work_subtotal_eur, iva_frac)
        iva_cents = to_cents(iva_eur)

    total_cents = work_subtotal_cents + fee_cents + iva_cents

    return Quote(
        milestones_subtotal_cents=milestones_subtotal_cents,
        materials_upfront_cents=materials_upfront_cents,
        fee_cents=fee_cents,
        iva_cents=iva_cents,
        amount_total_cents=total_cents,
        iva_rate=iva_int if iva_int is not None else 0,
        milestones=milestones,
        currency=draft.currency,
    )


def breakdown_from_quote_row(row: Dict[str, Any]) -> QuoteBreakdown:
    """Decode a stored ``quotes`` row into a typed :class:`QuoteBreakdown`.

    Used by:

    - ``routes/documents.py::_build_invoice_context`` (replaces the inline
      ``iva_eur = work_subtotal * iva_rate / 100`` re-derivation).
    - Contractor dashboard summaries of finalized quotes.

    Robust to missing fields — if ``iva_rate`` is absent, we treat the
    row as IVA-inclusive (iva = 0, same as the draft convention).
    """

    total_cents = int(row.get("amount_total_cents") or 0)
    materials_cents = int(row.get("materials_upfront_cents") or 0)
    fee_cents = int(row.get("stripe_fee_cents") or 0)

    iva_rate_raw = row.get("iva_rate")
    iva_int = int(iva_rate_raw) if iva_rate_raw else 0

    work_subtotal_cents = total_cents - fee_cents
    iva_cents = 0

    if iva_int > 0 and work_subtotal_cents > 0:
        base_cents = int(round(work_subtotal_cents / (1 + iva_int / 100)))
        iva_cents = work_subtotal_cents - base_cents
        work_subtotal_cents = base_cents

    return QuoteBreakdown(
        work_subtotal_cents=work_subtotal_cents,
        materials_upfront_cents=materials_cents,
        fee_cents=fee_cents,
        iva_cents=iva_cents,
        iva_rate=iva_int,
        total_cents=total_cents,
        work_subtotal_eur=float(from_cents(work_subtotal_cents)),
        iva_eur=float(from_cents(iva_cents)),
        fee_eur=float(from_cents(fee_cents)),
        total_eur=float(from_cents(total_cents)),
        currency="EUR",
    )
