"""Process-wide configuration for :mod:`pricing`.

One module-private settings object with `configure(...)` overrides. Mirrors
``core.http.http_client`` / ``core.db.get_supabase`` style — flat function
API, no class hierarchy.

Path resolution order for each artifact (cype_db, recipes, ine_index,
overhead model):

1. Argument passed to :func:`configure` (highest priority).
2. ``LEO_PRICING_*`` env var (e.g. ``LEO_PRICING_CYPE_DB``).
3. Bundled default at ``importlib.resources.files('pricing') / 'data' /
   <name>``.

For ``prices_db`` and ``products_db`` — NOT bundled (9 MB and 78 MB
respectively). Resolution order is (a) explicit path -> (b) env var ->
(c) None (callers get :class:`IndexNotFoundError` on first use).

Calling :func:`configure` clears memoised caches on the affected modules
so recipes reload, INE index re-reads, and SQLite connections reopen on
next use.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, replace
from importlib.resources import files
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    """Immutable pricing settings bag. Replaced wholesale on configure()."""

    cype_db: Optional[Path] = None
    prices_db: Optional[Path] = None
    products_db: Optional[Path] = None
    recipes_path: Optional[Path] = None
    ine_index_path: Optional[Path] = None
    overhead_model_path: Optional[Path] = None
    data_dir: Optional[Path] = None
    regional_multipliers_override: Optional[Dict[str, float]] = None
    markup_by_chapter_override: Optional[Dict[str, Any]] = None
    historical_lookback_months: int = 24
    default_service_fee_percent: float = 5.0
    default_iva_rate: float = 0.10


_settings: Settings = Settings()


# --------------------------------- bundled-data helpers -----------------------

def _bundled(name: str) -> Path:
    """Return the path to a bundled artifact under ``pricing/data/``.

    Uses :func:`importlib.resources.files` so it resolves against the
    ``pricing`` package's own install location. Post Wave 4 the package
    lives at ``apps/scope/product/backend/pricing/`` (on scope's ``PYTHONPATH``),
    and the resolver still works unchanged.
    """

    return Path(str(files("pricing").joinpath("data").joinpath(name)))


def _env_path(var: str) -> Optional[Path]:
    raw = os.environ.get(var)
    return Path(raw) if raw else None


# --------------------------------- public config API --------------------------

def configure(
    *,
    cype_db: Optional[Path] = None,
    prices_db: Optional[Path] = None,
    products_db: Optional[Path] = None,
    recipes_path: Optional[Path] = None,
    ine_index_path: Optional[Path] = None,
    overhead_model_path: Optional[Path] = None,
    data_dir: Optional[Path] = None,
    regional_multipliers: Optional[Mapping[str, float]] = None,
    markup_by_chapter: Optional[Mapping[str, Any]] = None,
    historical_lookback_months: Optional[int] = None,
    default_service_fee_percent: Optional[float] = None,
    default_iva_rate: Optional[float] = None,
) -> None:
    """Override the process-wide defaults.

    Clears memoised caches (recipes, INE index, autónomo overhead
    model) and closes any cached SQLite connections so the next call
    reopens against the new paths. Safe to call multiple times; last
    call wins.

    Kwargs passed as ``None`` are treated as "no change"; to reset a
    field, omit it from the call (which resets every unpassed field to
    the dataclass default) or pass the default explicitly.
    """

    global _settings

    current = _settings
    _settings = replace(
        current,
        cype_db=cype_db if cype_db is not None else current.cype_db,
        prices_db=prices_db if prices_db is not None else current.prices_db,
        products_db=products_db if products_db is not None else current.products_db,
        recipes_path=recipes_path if recipes_path is not None else current.recipes_path,
        ine_index_path=ine_index_path if ine_index_path is not None else current.ine_index_path,
        overhead_model_path=(
            overhead_model_path if overhead_model_path is not None
            else current.overhead_model_path
        ),
        data_dir=data_dir if data_dir is not None else current.data_dir,
        regional_multipliers_override=(
            dict(regional_multipliers)
            if regional_multipliers is not None
            else current.regional_multipliers_override
        ),
        markup_by_chapter_override=(
            dict(markup_by_chapter)
            if markup_by_chapter is not None
            else current.markup_by_chapter_override
        ),
        historical_lookback_months=(
            historical_lookback_months
            if historical_lookback_months is not None
            else current.historical_lookback_months
        ),
        default_service_fee_percent=(
            default_service_fee_percent
            if default_service_fee_percent is not None
            else current.default_service_fee_percent
        ),
        default_iva_rate=(
            default_iva_rate
            if default_iva_rate is not None
            else current.default_iva_rate
        ),
    )

    _invalidate_caches()


def close_connections() -> None:
    """Close module-held SQLite connections (CYPE, prices, products).

    Invoked by :func:`configure` and registered at process exit. Safe to
    call repeatedly. Public so tests can assert cleanup.
    """

    _invalidate_caches()


def _reset_for_tests() -> None:
    """Reset all settings to their dataclass defaults + drop caches.

    Intended for test isolation. Not part of the public API: do not use
    in production code.
    """

    global _settings
    _settings = Settings()
    _invalidate_caches()


def _invalidate_caches() -> None:
    """Clear memoised loaders + close SQLite connections."""

    for module_name, fn_name in (
        ("pricing.recipes", "_clear_cache"),
        ("pricing.ine_drift", "_clear_cache"),
        ("pricing.overhead", "_clear_cache"),
        ("pricing.cype_index", "close_connection"),
        ("pricing.price_lookup", "close_connection"),
        ("pricing.product_lookup", "close_connection"),
    ):
        try:
            import importlib

            mod = importlib.import_module(module_name)
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                fn()
        except Exception:
            pass


# --------------------------------- path resolvers -----------------------------

def _resolve_path(
    override: Optional[Path],
    env_var: str,
    bundled_name: Optional[str],
    default_dir_name: Optional[str] = None,
) -> Optional[Path]:
    """Resolve a data artifact path.

    Order: explicit override → env var → ``settings.data_dir`` (if set)
    → bundled artifact (if available).
    """

    if override is not None:
        return override

    env = _env_path(env_var)
    if env is not None:
        return env

    if _settings.data_dir is not None and default_dir_name:
        candidate = _settings.data_dir / default_dir_name
        if candidate.exists():
            return candidate

    if bundled_name:
        try:
            p = _bundled(bundled_name)
            if p.exists():
                return p
        except (FileNotFoundError, ModuleNotFoundError):
            return None

    return None


def cype_db_path() -> Optional[Path]:
    return _resolve_path(
        _settings.cype_db,
        "LEO_PRICING_CYPE_DB",
        "cype_prices.db",
        "cype_prices.db",
    )


def prices_db_path() -> Optional[Path]:
    """Resolve the Habitissimo+CronoShare prices DB. Not bundled."""

    return _resolve_path(
        _settings.prices_db,
        "LEO_PRICING_PRICES_DB",
        None,
        "prices.db",
    )


def products_db_path() -> Optional[Path]:
    """Resolve the Leroy Merlin products DB. Not bundled (78 MB)."""

    return _resolve_path(
        _settings.products_db,
        "LEO_PRICING_PRODUCTS_DB",
        None,
        "products.db",
    )


def recipes_path() -> Optional[Path]:
    return _resolve_path(
        _settings.recipes_path,
        "LEO_PRICING_RECIPES",
        "residential_recipes.json",
        "residential_recipes.json",
    )


def ine_index_path() -> Optional[Path]:
    return _resolve_path(
        _settings.ine_index_path,
        "LEO_PRICING_INE_INDEX",
        "ine_material_index.json",
        "ine_material_index.json",
    )


def overhead_model_path() -> Optional[Path]:
    return _resolve_path(
        _settings.overhead_model_path,
        "LEO_PRICING_OVERHEAD_MODEL",
        "autonomo_overhead_model.json",
        "autonomo_overhead_model.json",
    )


# --------------------------------- override accessors -------------------------

def regional_multipliers_override() -> Optional[Mapping[str, float]]:
    return _settings.regional_multipliers_override


def markup_by_chapter_override() -> Optional[Mapping[str, Any]]:
    return _settings.markup_by_chapter_override


def historical_lookback_months() -> int:
    return _settings.historical_lookback_months


def default_service_fee_percent() -> float:
    return _settings.default_service_fee_percent


def default_iva_rate() -> float:
    return _settings.default_iva_rate


__all__ = [
    "Settings",
    "configure",
    "close_connections",
    "cype_db_path",
    "prices_db_path",
    "products_db_path",
    "recipes_path",
    "ine_index_path",
    "overhead_model_path",
    "regional_multipliers_override",
    "markup_by_chapter_override",
    "historical_lookback_months",
    "default_service_fee_percent",
    "default_iva_rate",
]
