"""INE material-price drift — recency adjustment.

The INE Monthly Material Price Index (``Table 8381``) tracks Spanish
industrial material prices across 13 categories. CYPE data was scraped
in March 2026; INE tells us how much prices have moved since.

:func:`compute_ine_material_drift(category)` returns a multiplier
centred on 1.0, capped at ±15% to prevent runaway drift from noisy
data. Applied inside :func:`pricing.estimate_cost` to the *material*
fraction of the CYPE cost-of-inputs (labour rates are NOT in INE).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from . import config
from .errors import IndexNotFoundError

logger = logging.getLogger(__name__)

__all__ = [
    "load_ine_index",
    "compute_ine_material_drift",
]


_index_cache: Optional[Dict[str, Any]] = None


def _clear_cache() -> None:
    global _index_cache
    _index_cache = None


def load_ine_index() -> Dict[str, Any]:
    """Return the INE category dict, lazy-loaded.

    Returns the ``categories`` sub-object (mapping from slug to
    ``{history: [...]}``). Empty dict if the file is missing or
    malformed.
    """

    global _index_cache
    if _index_cache is not None:
        return _index_cache

    path = config.ine_index_path()
    if path is None or not path.exists():
        logger.warning("INE material index not found at %s", path)
        _index_cache = {}
        return _index_cache

    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise IndexNotFoundError(
            f"Could not load INE index from {path!s}: {exc}"
        ) from exc

    _index_cache = data.get("categories", {}) or {}
    logger.info("Loaded INE material index with %d categories", len(_index_cache))
    return _index_cache


def compute_ine_material_drift(ine_category_slug: str) -> float:
    """Return the material-price drift multiplier for an INE category.

    Uses the 3-period rolling window from INE Table 8381 (first vs last
    entry in ``history``). Capped at ±15%. Returns 1.0 if data is
    missing or if the category has fewer than 2 history entries.
    """

    if not ine_category_slug:
        return 1.0

    index = load_ine_index()
    cat = index.get(ine_category_slug)
    if not cat:
        return 1.0

    history = cat.get("history", [])
    if len(history) < 2:
        return 1.0

    current = history[0].get("index")
    reference = history[-1].get("index")

    if not reference or not current:
        return 1.0

    drift = current / reference
    drift = max(0.85, min(1.15, drift))
    return round(drift, 4)
