"""
apps/scope/product/backend/constants — scope-specific canonical values
================================================================

Every scope-app-specific hardcoded value lives here. These are policy
decisions baked into the Spanish renovations-marketplace product:
Spanish VAT rates, the list of canonical trades (``fontanero``,
``electricista``, ...), and the founder WhatsApp inbox used for Hermes
auto-escalation.

Moved from ``packages/domain/constants.py`` in Phase 5 Wave 2 because
these are **scope concerns, not shared capabilities**. Other apps (a
cleaning-biz landing page, an internal sales tool) have different
trades, different VAT regimes, and different founder contacts.

Non-scope constants from the former ``packages/domain/constants.py``:

* ``BEDROCK_REGION``, ``BEDROCK_CLAUDE_HAIKU``, ``BEDROCK_CLAUDE_SONNET``
  moved to :mod:`llm.providers.bedrock`.
* ``LITELLM_BASE_URL``, ``LITELLM_API_KEY`` already lived in
  :mod:`llm.config`; the duplicate in ``domain.constants`` was removed.
* ``META_API_VERSION``, ``META_API_BASE`` moved to
  :mod:`messaging.constants`.
* ``STRIPE_API_VERSION`` deleted — the ``stripe`` SDK now account-pins
  its own version (see ``packages/payments/README.md``); we never read
  the constant at runtime.
* Pure helpers (``text.py``, ``money.py``, ``phone.py``) moved to
  ``packages/core``.
* State machines (``states.py``) moved to
  ``apps/scope/product/backend/state_machine.py``.

Tier: leaf. Depends on stdlib only.
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Founder phone numbers (E.164 digits, no leading '+')
# ---------------------------------------------------------------------------
# Stored WITHOUT '+' per Meta Graph WhatsApp API convention. The +
# would break a raw POST to `/PHONE/messages` so the canonical form is
# prefix-less. Every caller concatenates '+' or drops it as needed.

PETER_WHATSAPP_UK = "00000000000"
"""Peter's UK WhatsApp. Founder inbox."""

PETER_PERSONAL_ES = "34627506263"
"""Peter's Spanish personal number. Founder inbox."""

LEO_WA_NUMBER = "34607590602"
"""Leo's business WA number — receives homeowner messages. OUTBOUND identity.

Deliberately NOT in ``FOUNDER_PHONES`` — adding it would cause Hermes to
reply-loop against its own outbound messages.
"""

FOUNDER_PHONES: "frozenset[str]" = frozenset({
    PETER_WHATSAPP_UK,
    PETER_PERSONAL_ES,
})
"""Founder-inbox set for Hermes auto-response gating. Two members.

Locked as ``frozenset`` (not ``set``) for immutability. ``in`` membership
works identically either way; caller redefinitions using plain ``set``
get rewritten during the codemod pass.
"""


def peter_whatsapp() -> str:
    """Return ``PETER_WHATSAPP`` env var or the UK default.

    Zero callers today — kept for tools that want a single override knob
    without reaching into ``os.getenv`` directly.
    """
    return os.getenv("PETER_WHATSAPP", PETER_WHATSAPP_UK)


# ---------------------------------------------------------------------------
# Spanish VAT
# ---------------------------------------------------------------------------
# Fraction form throughout (0.21 not 21). Integer-percent callers use
# ``core.money.add_iva_percent`` / ``strip_iva_percent`` /
# ``iva_amount_percent`` wrappers with the raw integer rate.

IVA_GENERAL = 0.21
"""21% general Spanish VAT."""

IVA_RESIDENTIAL_RENOVATION = 0.10
"""10% reduced IVA for residential-renovation services in Spain."""

IVA_REDUCED = 0.10
"""Alias of ``IVA_RESIDENTIAL_RENOVATION``. Both names retained for discoverability."""


# ---------------------------------------------------------------------------
# Trade labels (Spanish, canonical spelling — UTF-8 per PEP 3120)
# ---------------------------------------------------------------------------

TRADE_PLUMBER = "fontanero"
TRADE_ELECTRICIAN = "electricista"
TRADE_LOCKSMITH = "cerrajero"
TRADE_PAINTER = "pintor"
TRADE_CARPENTER = "carpintero"
TRADE_TILER = "alicatador"
TRADE_MASON = "albañil"
TRADE_GLAZIER = "cristalero"
TRADE_AC_TECH = "climatización"
TRADE_HEATING = "calefacción"

CANONICAL_TRADES: "tuple[str, ...]" = (
    TRADE_PLUMBER,
    TRADE_ELECTRICIAN,
    TRADE_LOCKSMITH,
    TRADE_PAINTER,
    TRADE_CARPENTER,
    TRADE_TILER,
    TRADE_MASON,
    TRADE_GLAZIER,
    TRADE_AC_TECH,
    TRADE_HEATING,
)
"""10 canonical Spanish trade slugs. Used by validators, dropdowns, LLM prompts."""


# ---------------------------------------------------------------------------
# Supabase table name pins (scope schema)
# ---------------------------------------------------------------------------
# Zero callers today — every route uses raw string literals. Kept for a
# future SQL-table-rename sweep.

TABLE_CONTRACTORS = "contractors"
TABLE_HOMEOWNERS = "homeowners"
TABLE_JOBS = "jobs"
TABLE_QUOTES = "quotes"
TABLE_MEMOS = "memos"
TABLE_EPHEMERAL_CONTEXT = "ephemeral_context"
TABLE_MESSAGES = "wa_messages"
TABLE_SALES_TRACKER = "sales_tracker"


__all__ = [
    # Identity
    "PETER_WHATSAPP_UK",
    "PETER_PERSONAL_ES",
    "LEO_WA_NUMBER",
    "FOUNDER_PHONES",
    "peter_whatsapp",
    # VAT
    "IVA_GENERAL",
    "IVA_RESIDENTIAL_RENOVATION",
    "IVA_REDUCED",
    # Trades
    "TRADE_PLUMBER",
    "TRADE_ELECTRICIAN",
    "TRADE_LOCKSMITH",
    "TRADE_PAINTER",
    "TRADE_CARPENTER",
    "TRADE_TILER",
    "TRADE_MASON",
    "TRADE_GLAZIER",
    "TRADE_AC_TECH",
    "TRADE_HEATING",
    "CANONICAL_TRADES",
    # Supabase tables
    "TABLE_CONTRACTORS",
    "TABLE_HOMEOWNERS",
    "TABLE_JOBS",
    "TABLE_QUOTES",
    "TABLE_MEMOS",
    "TABLE_EPHEMERAL_CONTEXT",
    "TABLE_MESSAGES",
    "TABLE_SALES_TRACKER",
]
