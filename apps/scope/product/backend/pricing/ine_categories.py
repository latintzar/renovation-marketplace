"""CYPE → INE material-category mapping + query-keyword inference.

The INE Monthly Material Price Index (Table 8381) tracks Spanish
industrial material prices in 13 broad categories. CYPE entries expose
material codes (``mt19``, ``mt37``, …) we prefix-match to an INE slug.
When CYPE doesn't provide codes (or no prefix matches), we fall back to
keyword inference from the free-text query.

Public entry point:

- :func:`ine_category_for_query(query)` — returns the best INE slug for
  a free-text query or ``None`` if no keyword matches.

Both lookups are CASE-INSENSITIVE + accent-stripped via
``core.text.strip_accents``.
"""

from __future__ import annotations

from typing import Optional

from core.text import strip_accents

from .constants import CYPE_TO_INE_CATEGORY, KEYWORD_TO_INE_CATEGORY

__all__ = [
    "CYPE_TO_INE_CATEGORY",
    "KEYWORD_TO_INE_CATEGORY",
    "ine_category_for_cype_code",
    "ine_category_for_query",
]


def ine_category_for_cype_code(material_code: str) -> Optional[str]:
    """Return the INE slug for a single CYPE material code, or None.

    Prefix-match. Longer prefixes win (``mt37b`` beats ``mt37``) because
    we sort keys by length descending before matching.
    """

    if not material_code:
        return None

    lowered = material_code.strip().lower()
    for prefix in sorted(CYPE_TO_INE_CATEGORY.keys(), key=len, reverse=True):
        if lowered.startswith(prefix):
            return CYPE_TO_INE_CATEGORY[prefix]
    return None


def ine_category_for_query(query: str) -> Optional[str]:
    """Best-match INE category slug from a free-text query.

    Strategy: accent-strip + lowercase, iterate ``KEYWORD_TO_INE_CATEGORY``
    looking for a substring hit. First hit wins (deterministic order via
    the ``MappingProxyType`` wrapping the underlying dict).

    Returns ``None`` if no keyword matches; callers apply no INE drift.
    """

    if not query or not query.strip():
        return None

    normalized = strip_accents(query.strip().lower())
    for keyword, slug in KEYWORD_TO_INE_CATEGORY.items():
        if keyword in normalized:
            return slug
    return None
