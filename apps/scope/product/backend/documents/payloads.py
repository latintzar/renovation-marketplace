"""Typed Pydantic payloads consumed by every `*Doc`.

Replaces the loose-dict ``_build_agreement_context(scope, contractor)``
at ``unmigrated/backend/routes/documents.py:105``. The single canonical
field is ``quote_token`` — the template-variable bug (``scope_token``
silent-blank) is structurally impossible now.

D1 — heavy money math delegates to :mod:`domain.money`
(:func:`domain.money.to_cents`, :func:`iva_amount`). This module owns
only the payload-level :class:`Money` model — a thin Pydantic wrapper
over ``cents: int`` that carries a canonical ``euros`` view and a
``"1.234,56 €"`` stringifier. All arithmetic funnels through
``domain.money`` via the ``+ - *`` operators below.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict

from core.money import format_eur, from_cents, to_cents

__all__ = [
    "Money",
    "Locale",
    "DocumentKind",
    "PartyInfo",
    "JobInfo",
    "Milestone",
    "QuotePayload",
    "InvoicePayload",
    "VariationPayload",
]


class Money(BaseModel):
    """Canonical EUR value for documents payloads.

    ``cents`` is the source of truth; :attr:`euros` and :meth:`__str__`
    derive from it (via :func:`domain.money.from_cents` and
    :func:`domain.money.format_eur`). Arithmetic operators delegate to
    :func:`domain.money.to_cents` so rounding is ``ROUND_HALF_UP`` (the
    Spanish legal convention) end-to-end.
    """

    model_config = ConfigDict(frozen=True)

    cents: int
    currency: Literal["EUR"] = "EUR"

    @classmethod
    def from_cents(cls, cents: int) -> "Money":
        """Alternate constructor: ``Money.from_cents(1234)``."""

        return cls(cents=int(cents))

    @classmethod
    def from_euros(cls, euros: Union[float, str, Decimal, int]) -> "Money":
        """Alternate constructor: ``Money.from_euros("12.34")``."""

        return cls(cents=to_cents(euros))

    @property
    def euros(self) -> Decimal:
        """EUR value as ``Decimal`` at 2 dp. Wraps :func:`domain.money.from_cents`."""

        return from_cents(self.cents)

    def __str__(self) -> str:
        """Human-readable ES-convention string, e.g. ``"1.234,56 €"``."""

        return format_eur(self.euros, convention="es")

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        return Money(cents=self.cents + other.cents)

    def __sub__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        return Money(cents=self.cents - other.cents)

    def __mul__(self, other: Union[int, float, Decimal]) -> "Money":
        return Money(cents=to_cents(self.euros * Decimal(str(other))))

    def __rmul__(self, other: Union[int, float, Decimal]) -> "Money":
        return self.__mul__(other)


_STRICT = ConfigDict(extra="forbid")


class Locale(str, Enum):
    """Template locale selector. Per-language templates are siblings
    (``agreement.es.html.j2``, ``agreement.en.html.j2`` — the latter
    is not present yet; :class:`AgreementDoc` will raise TemplateNotFound
    if the translation doesn't exist).
    """

    ES = "es"
    EN = "en"
    PT = "pt"


class DocumentKind(str, Enum):
    """Stable identifier used in S3 keys and ``documents`` table rows."""

    AGREEMENT = "agreement"
    INVOICE = "invoice"
    VARIATION = "variation"


class PartyInfo(BaseModel):
    """Homeowner or contractor descriptor. ``trade`` and ``address`` are
    contractor-only; left ``None`` for homeowners."""

    model_config = _STRICT

    name: str
    email: str
    trade: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None


class JobInfo(BaseModel):
    """Job descriptor — what the quote/invoice is for."""

    model_config = _STRICT

    title: str
    address: str
    description: Optional[str] = None


class Milestone(BaseModel):
    """Single payment milestone (``fase``).

    ``released_at`` is populated for invoice-context builds from
    ``milestone_updates`` rows; ``None`` for agreement-context builds.
    """

    model_config = _STRICT

    title: str
    amount: Money
    released_at: Optional[date] = None


class QuotePayload(BaseModel):
    """Typed input for :class:`AgreementDoc`.

    Replaces the ``scope``/``contractor`` dict pair at
    ``routes/documents.py:105``. The field is ``quote_token`` (D12).
    """

    model_config = _STRICT

    quote_token: str
    homeowner: PartyInfo
    contractor: PartyInfo
    job: JobInfo
    milestones: List[Milestone]
    total: Money
    leo_fee: Money
    materials_upfront: Money
    iva_rate_pct: int = 0
    agreement_date: date
    legal_review_tag: str = "v1-2026-04"


class InvoicePayload(BaseModel):
    """Typed input for :class:`InvoiceDoc`.

    The invoice is only rendered post-completion (``quote.status ==
    'complete'``) — the caller enforces the gate. ``completion_date`` is
    required; every ``Milestone.released_at`` should be populated.
    """

    model_config = _STRICT

    quote_token: str
    homeowner: PartyInfo
    contractor: PartyInfo
    job: JobInfo
    milestones: List[Milestone]
    materials_upfront: Money
    leo_fee: Money
    iva_rate_pct: int
    total: Money
    completion_date: date
    payment_intent_id: Optional[str] = None


class VariationPayload(BaseModel):
    """Typed input for :class:`VariationDoc`. Template is a stub today
    (D17 — legal copy pending). The payload shape is pre-committed so
    ``packages/messaging`` can import the symbol."""

    model_config = _STRICT

    quote_token: str
    variation_id: str
    homeowner: PartyInfo
    contractor: PartyInfo
    job: JobInfo
    change_summary: str
    milestones_delta: List[Milestone]
    delta_total: Money
    variation_date: date
    legal_review_tag: str = "v1-2026-04"
