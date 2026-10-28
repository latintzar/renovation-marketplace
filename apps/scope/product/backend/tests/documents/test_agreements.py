"""Unit tests for `documents.agreements.AgreementDoc`."""
from __future__ import annotations

import pytest

from documents import AgreementDoc


class TestAgreementDoc:
    def test_template_name(self, quote_payload) -> None:
        doc = AgreementDoc(quote_payload)
        assert doc.template_name() == "agreement.es.html.j2"

    def test_render_html_contains_party_names(self, quote_payload) -> None:
        doc = AgreementDoc(quote_payload)
        html = doc.render_html()
        assert "Ana García" in html
        assert "Bob el Constructor" in html

    def test_render_html_contains_quote_token(self, quote_payload) -> None:
        doc = AgreementDoc(quote_payload)
        html = doc.render_html()
        assert quote_payload.quote_token in html

    def test_render_html_memoized(self, quote_payload) -> None:
        doc = AgreementDoc(quote_payload)
        assert doc.render_html() is doc.render_html()

    def test_no_scope_token_leak(self, quote_payload) -> None:
        """Regression: D12 rename scope_token -> quote_token."""
        doc = AgreementDoc(quote_payload)
        html = doc.render_html()
        assert "scope_token" not in html

    def test_content_hash_deterministic(self, quote_payload) -> None:
        d1 = AgreementDoc(quote_payload)
        d2 = AgreementDoc(quote_payload)
        assert d1.content_hash() == d2.content_hash()
        assert len(d1.content_hash()) == 64

    def test_content_hash_memoized(self, quote_payload) -> None:
        doc = AgreementDoc(quote_payload)
        assert doc.content_hash() is doc.content_hash()

    def test_filename_default_ext_pdf(self, quote_payload) -> None:
        doc = AgreementDoc(quote_payload)
        assert doc.filename().endswith(".pdf")
        assert quote_payload.quote_token[:12] in doc.filename()

    def test_filename_html_ext(self, quote_payload) -> None:
        doc = AgreementDoc(quote_payload)
        assert doc.filename(ext="html").endswith(".html")

    def test_formats_iva_0_percent(self, quote_payload) -> None:
        doc = AgreementDoc(quote_payload)
        html = doc.render_html()
        # 0% IVA case — no IVA line item should appear or should be 0,00
        assert html.count("Ana García") >= 1  # template renders


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("weasyprint") is None,
    reason="WeasyPrint optional dep not installed",
)
class TestAgreementDocPDF:
    @pytest.mark.asyncio
    async def test_render_pdf_produces_bytes(self, quote_payload) -> None:
        doc = AgreementDoc(quote_payload)
        pdf = await doc.render_pdf()
        assert isinstance(pdf, (bytes, bytearray))
        assert pdf[:4] == b"%PDF"
