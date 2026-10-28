"""Parametric + regional adjustments to base cost estimates.

Two orthogonal adjustments:

- :func:`apply_modifiers(base, modifiers)` — multiplies ``base`` by each
  recognised modifier in ``MODIFIERS`` (access difficult, peak season,
  etc.). Unknown keys are silently skipped (logged at DEBUG).
- :func:`regional_multiplier(city_or_province)` — looks up a Spanish
  city/province in ``REGIONAL_MULTIPLIERS`` (Madrid 1.15×, Ibiza 1.25×,
  rural default 0.95×). Falls back via ``domain.cities.province_for_city``.

The legacy ``"rural"`` modifier (dropped in D13) is accepted silently
for back-compat, emitting a :class:`DeprecationWarning` the first time
it's used per process.
"""

from __future__ import annotations

import logging
import warnings
from typing import List, Mapping, Optional, Tuple, Union

from core.text import strip_accents

from . import config
from .constants import MODIFIERS, REGIONAL_MULTIPLIERS

logger = logging.getLogger(__name__)

__all__ = [
    "apply_modifiers",
    "regional_multiplier",
    "normalise_modifiers",
]


_RURAL_WARNED = False


def normalise_modifiers(
    modifiers: Union[None, str, List[str]],
) -> List[str]:
    """Coerce the many shapes hermes may pass into a clean list of keys.

    Accepts:

    - ``None`` → ``[]``
    - ``str`` → comma/space split → trimmed list
    - ``list[str]`` → trimmed list (empty strings dropped)

    Returns always a list of lowercase, stripped modifier keys.
    """

    if modifiers is None:
        return []

    if isinstance(modifiers, str):
        parts = [p.strip().lower() for p in modifiers.replace(";", ",").split(",")]
        return [p for p in parts if p]

    if isinstance(modifiers, list):
        result: List[str] = []
        for m in modifiers:
            if not m:
                continue
            if isinstance(m, str):
                result.append(m.strip().lower())
            else:
                result.append(str(m).strip().lower())
        return [m for m in result if m]

    return []


def apply_modifiers(
    base_eur: float,
    modifiers: Union[None, str, List[str]],
) -> Tuple[float, List[str]]:
    """Multiply ``base_eur`` by every recognised modifier.

    Returns ``(adjusted_eur, applied_keys)`` where ``applied_keys`` is
    the subset of ``modifiers`` that matched :data:`MODIFIERS`. Unknown
    keys are silently dropped; the legacy ``"rural"`` key is dropped
    with a one-time :class:`DeprecationWarning`.
    """

    keys = normalise_modifiers(modifiers)

    total_mult = 1.0
    applied: List[str] = []
    for key in keys:
        if key == "rural":
            global _RURAL_WARNED
            if not _RURAL_WARNED:
                warnings.warn(
                    "modifier 'rural' is deprecated; pass city= to "
                    "estimate_cost for regional adjustment instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                _RURAL_WARNED = True
            continue

        mult = MODIFIERS.get(key)
        if mult is None:
            logger.debug("unknown modifier %r — skipping", key)
            continue

        total_mult *= mult
        applied.append(key)

    return round(base_eur * total_mult, 2), applied


def regional_multiplier(city_or_province: str) -> float:
    """Look up the regional cost multiplier for a Spanish city/province.

    Resolution order:

    1. Direct match (accent-stripped, lowercased, whitespace-collapsed)
       against ``REGIONAL_MULTIPLIERS`` (override merged via
       :func:`config.regional_multipliers_override`).
    2. Province match via ``domain.cities.province_for_city``.
    3. ``_rural_default`` if the city isn't in ``SPANISH_CANONICAL_CITIES``
       at all.
    4. ``_default`` (1.00) otherwise.
    """

    if not city_or_province:
        return 1.00

    table = _merged_regional_table()

    key = _normalise_city(city_or_province)
    if not key:
        return 1.00

    if key in table:
        return float(table[key])

    if not _is_known_spanish_city(city_or_province):
        return float(table.get("_rural_default", 0.95))

    return float(table.get("_default", 1.00))


def _merged_regional_table() -> Mapping[str, float]:
    """Return the merged regional multiplier table (override over default)."""

    override = config.regional_multipliers_override()
    if not override:
        return REGIONAL_MULTIPLIERS

    merged = dict(REGIONAL_MULTIPLIERS)
    merged.update({k.lower(): float(v) for k, v in override.items()})
    return merged


def _normalise_city(name: str) -> str:
    stripped = strip_accents((name or "").lower()).strip()
    return stripped.replace(" ", "").replace("-", "")


def _is_known_spanish_city(name: str) -> bool:
    """Return True if the caller's name resolves to a canonical Spanish city.

    Canonical city list isn't implemented in this repo yet (the previous
    home ``domain.cities`` was deleted in Phase 5 Wave 2 without ever
    holding data). Returns ``False`` so the caller falls back to the
    rural / default multiplier — matches the old ``ImportError`` path.
    """
    return False
