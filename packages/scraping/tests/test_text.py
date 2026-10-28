"""Unit tests for :func:`scraping.html_to_text` (D9 three-tier fallback)."""
from __future__ import annotations

import sys
import types

import pytest

from scraping import html_to_text


def test_empty_returns_empty_string() -> None:
    assert html_to_text("") == ""


def test_simple_extract_returns_text(simple_html: str) -> None:
    out = html_to_text(simple_html)
    assert "Cocina integral en Madrid" in out
    assert "var x = 1" not in out


def test_regex_fallback_when_trafilatura_and_bs4_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If both trafilatura and bs4 are unimportable, the regex tier
    should still strip tags and return text."""

    original = dict(sys.modules)

    def _strip_module(name: str) -> None:
        sys.modules.pop(name, None)

    real_import = __builtins__["__import__"] if isinstance(
        __builtins__, dict
    ) else __builtins__.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {"trafilatura", "bs4"}:
            raise ImportError(f"blocked: {name}")
        return real_import(name, globals, locals, fromlist, level)

    _strip_module("trafilatura")
    _strip_module("bs4")

    monkeypatch.setattr("builtins.__import__", fake_import)
    try:
        out = html_to_text("<p>hi <b>there</b></p>")
        assert "hi" in out
        assert "there" in out
        assert "<" not in out
    finally:
        sys.modules.clear()
        sys.modules.update(original)


def test_bs4_fallback_when_trafilatura_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When trafilatura is unavailable but bs4 is, bs4 does the work."""

    real_import = __builtins__["__import__"] if isinstance(
        __builtins__, dict
    ) else __builtins__.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "trafilatura":
            raise ImportError("blocked: trafilatura")
        return real_import(name, globals, locals, fromlist, level)

    sys.modules.pop("trafilatura", None)
    monkeypatch.setattr("builtins.__import__", fake_import)

    out = html_to_text(
        "<html><body><script>secret()</script><p>visible</p></body></html>"
    )
    assert "visible" in out
    assert "secret" not in out
