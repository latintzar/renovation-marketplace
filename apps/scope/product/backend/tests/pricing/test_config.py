"""Tests for :mod:`pricing.config`."""
from __future__ import annotations

from pathlib import Path

import pytest

from pricing import config


def test_bundled_data_paths_exist() -> None:
    """All bundled data files must resolve and exist on-disk."""

    assert config.cype_db_path().exists()
    assert config.ine_index_path().exists()
    assert config.recipes_path().exists()
    assert config.overhead_model_path().exists()


def test_configure_overrides_cype_db_path(tmp_path: Path) -> None:
    custom = tmp_path / "custom_cype.db"
    custom.write_text("")  # file must exist
    config.configure(cype_db=custom)
    assert config.cype_db_path() == custom


def test_configure_overrides_default_iva_rate() -> None:
    config.configure(default_iva_rate=0.21)
    assert config.default_iva_rate() == 0.21


def test_configure_overrides_default_service_fee_percent() -> None:
    config.configure(default_service_fee_percent=7.5)
    assert config.default_service_fee_percent() == 7.5


def test_prices_db_optional(tmp_path: Path) -> None:
    """prices_db is external; returns None if unconfigured + env var missing."""

    # When not set, returns None OR picks up env
    path = config.prices_db_path()
    # Accept either None (unconfigured) or a path that may or may not exist
    assert path is None or isinstance(path, Path)


def test_products_db_optional() -> None:
    path = config.products_db_path()
    assert path is None or isinstance(path, Path)


def test_close_connections_idempotent() -> None:
    """close_connections() must be safe to call even when nothing open."""

    config.close_connections()
    config.close_connections()  # second call must not explode
