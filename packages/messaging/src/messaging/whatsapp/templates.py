"""WhatsApp template routing.

Frozen template catalogue + routing helpers. :data:`TEMPLATES` is wrapped
in a :class:`MappingProxyType` so neither the outer ``purpose`` dict nor
the inner ``language`` dicts can be mutated in place (a pre-migration
footgun — the raw dict was occasionally monkeypatched at runtime by
callers).

The domain package (``domain.META_API_BASE``) pins the Meta Cloud API
version so every outbound caller agrees on it.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping


def _freeze_templates(raw: dict[str, dict[str, str]]) -> Mapping[str, Mapping[str, str]]:
    """Return a two-level read-only view of ``raw`` (purpose → lang → template name)."""
    return MappingProxyType({purpose: MappingProxyType(langs) for purpose, langs in raw.items()})


_RAW_TEMPLATES: dict[str, dict[str, str]] = {
    "outreach":       {"en_US": "contractor_intro_v1",       "es": "contractor_intro_v2"},
    "followup_1":     {"en_US": "contractor_followup_1",     "es": "contractor_followup1_v2"},
    "followup_final": {"en_US": "contractor_followup_final", "es": "contractor_final_v2"},
    "referral_pro":   {"en_US": "leo_contractor_referral_v1", "es": "leo_contractor_referral_v1"},
    "referral_ho":    {"en_US": "leo_homeowner_referral_v1",  "es": "leo_homeowner_referral_v1"},
    "onboarding":     {"en_US": "leo_received_v1",           "es": "leo_received_v1"},
    "handoff":        {"en_US": "web_chat_handoff",          "es": "web_chat_handoff"},
    "general":        {"en_US": "leo_message_v1",            "es": "leo_message_v1"},
    "milestone":      {"en_US": "leo_milestone_v1",          "es": "leo_milestone_v1"},
}

TEMPLATES: Mapping[str, Mapping[str, str]] = _freeze_templates(_RAW_TEMPLATES)
"""Frozen ``purpose → lang → template_name`` catalogue.

Use :func:`get_template_name` unless you specifically need the raw view.
"""


def detect_language(phone_digits: str) -> str:
    """Guess ``en_US`` vs ``es`` from the phone country code.

    Spanish-registered WhatsApp numbers start with ``34``; everything else
    defaults to English. Pre-migration behavior preserved 1:1.
    """
    if phone_digits.startswith("34"):
        return "es"
    return "en_US"


def get_template_name(purpose: str, language: str) -> str:
    """Look up a template name for a ``purpose`` + ``language`` combo.

    Falls back to ``en_US`` when the requested language is missing; returns
    an empty string when the purpose is unknown entirely.
    """
    row = TEMPLATES.get(purpose, {})
    return row.get(language, row.get("en_US", ""))


__all__ = ["TEMPLATES", "detect_language", "get_template_name"]
