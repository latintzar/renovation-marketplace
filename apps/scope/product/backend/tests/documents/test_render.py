"""Unit tests for `documents.render` — Jinja2 env + WeasyPrint isolation."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from jinja2 import UndefinedError

from documents import render_html, set_override_dir
from documents.contexts import build_agreement_context


@pytest.fixture(autouse=True)
def _clear_overrides():
    set_override_dir(None)
    yield
    set_override_dir(None)


def test_render_html_agreement(quote_payload) -> None:
    ctx = build_agreement_context(quote_payload)
    html = render_html("agreement.es.html.j2", ctx)
    assert "Ana García" in html
    assert "Bob el Constructor" in html
    assert quote_payload.quote_token in html


def test_render_html_strict_undefined() -> None:
    """Missing variables raise, not silently render blank (D4)."""

    with pytest.raises(UndefinedError):
        render_html(
            "agreement.es.html.j2",
            {"quote_token": "x"},
        )


def test_override_dir_roundtrip(tmp_path: Path, quote_payload) -> None:
    override = tmp_path / "overrides"
    override.mkdir()
    set_override_dir(override)

    (override / "agreement.es.html.j2").write_text(
        "<html><body>OVERRIDE {{ quote_token }}</body></html>"
    )

    ctx = build_agreement_context(quote_payload)
    html = render_html("agreement.es.html.j2", ctx)
    assert "OVERRIDE" in html
    assert quote_payload.quote_token in html


def test_override_dir_reset_via_none(quote_payload) -> None:
    set_override_dir(None)
    ctx = build_agreement_context(quote_payload)
    html = render_html("agreement.es.html.j2", ctx)
    assert "<!doctype html>" in html.lower() or "<!DOCTYPE html>" in html


def test_pdf_render_error_is_exported() -> None:
    from documents import PDFRenderError  # noqa: F401


@pytest.mark.skipif(
    importlib.util.find_spec("weasyprint") is None,
    reason="WeasyPrint optional dep not installed",
)
@pytest.mark.asyncio
async def test_render_pdf_produces_bytes(quote_payload) -> None:
    from documents import render_pdf

    ctx = build_agreement_context(quote_payload)
    html = render_html("agreement.es.html.j2", ctx)
    pdf = await render_pdf(html)
    assert isinstance(pdf, (bytes, bytearray))
    assert pdf[:4] == b"%PDF"
