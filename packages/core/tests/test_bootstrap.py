"""Tests for :mod:`core.bootstrap`."""

from __future__ import annotations

from pathlib import Path

import pytest

from core import bootstrap, load_env_files, repo_root


def test_repo_root_resolves_to_leo() -> None:
    """The marker walk finds the /root/leo ancestor."""
    root = repo_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / ".git").exists()
    # The repo root is `/root/leo` in this environment.
    assert root == Path("/root/leo")


def test_repo_root_is_cached() -> None:
    """Repeated calls return the same Path instance (lru_cache)."""
    assert repo_root() is repo_root()


def test_scope_backend_dir_prefers_new_location_when_present() -> None:
    """If ``apps/scope-backend`` exists as a dir it wins; else fall back."""
    root = repo_root()
    new_loc = root / "apps" / "scope-backend"
    legacy = root / "unmigrated" / "backend"
    expected = new_loc if new_loc.is_dir() else legacy
    assert bootstrap.scope_backend_dir() == expected


def test_scope_backend_dir_falls_back_when_new_location_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With ``apps/scope-backend`` stubbed away, legacy path is returned."""
    fake_root = tmp_path
    (fake_root / "unmigrated" / "backend").mkdir(parents=True)
    # Ensure apps/scope-backend does NOT exist in the fake root.

    monkeypatch.setattr(bootstrap, "repo_root", lambda: fake_root)
    assert bootstrap.scope_backend_dir() == fake_root / "unmigrated" / "backend"


def test_backend_dir_is_alias_of_scope_backend_dir() -> None:
    assert bootstrap.backend_dir() == bootstrap.scope_backend_dir()


def test_load_env_files_skips_missing(tmp_path: Path) -> None:
    """Non-existent paths are silently skipped."""
    loaded = load_env_files([tmp_path / "missing.env"])
    assert loaded == []


def test_load_env_files_loads_and_returns_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real dotenv file is loaded and its path is returned."""
    env = tmp_path / "sample.env"
    env.write_text("LEO_TEST_BOOT_VAR=on\n", encoding="utf-8")
    monkeypatch.delenv("LEO_TEST_BOOT_VAR", raising=False)

    loaded = load_env_files([env])

    assert loaded == [env]
    import os

    assert os.environ["LEO_TEST_BOOT_VAR"] == "on"
    monkeypatch.delenv("LEO_TEST_BOOT_VAR", raising=False)


def test_load_env_files_override_false_preserves_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Existing env values aren't clobbered with ``override=False``."""
    env = tmp_path / "override.env"
    env.write_text("LEO_PREEXISTING=from_file\n", encoding="utf-8")
    monkeypatch.setenv("LEO_PREEXISTING", "from_env")

    load_env_files([env], override=False)

    import os

    assert os.environ["LEO_PREEXISTING"] == "from_env"


def test_load_env_files_override_true_clobbers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``override=True`` makes the file win over existing env."""
    env = tmp_path / "override.env"
    env.write_text("LEO_OVERRIDDEN=from_file\n", encoding="utf-8")
    monkeypatch.setenv("LEO_OVERRIDDEN", "from_env")

    load_env_files([env], override=True)

    import os

    assert os.environ["LEO_OVERRIDDEN"] == "from_file"


def test_init_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Calling :func:`init` twice only mutates ``sys.path`` once."""
    # Reset internal flag so we start fresh.
    monkeypatch.setattr(bootstrap, "_INITIALIZED", False)
    bootstrap.init(load_dotenv_local=False)
    bootstrap.init(load_dotenv_local=False)
    import sys

    bdir = str(bootstrap.scope_backend_dir())
    assert sys.path.count(bdir) == 1
