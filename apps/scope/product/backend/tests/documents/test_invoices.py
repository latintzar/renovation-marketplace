"""Unit tests for `documents.invoices.InvoiceDoc`."""
from __future__ import annotations

from documents import InvoiceDoc


class TestInvoiceDoc:
    def test_template_name(self, invoice_payload) -> None:
        doc = InvoiceDoc(invoice_payload)
        assert doc.template_name() == "invoice.es.html.j2"

    def test_document_version_matches_template(self, invoice_payload) -> None:
        from documents import DOCUMENT_VERSION_INVOICE

        doc = InvoiceDoc(invoice_payload)
        assert doc.DOCUMENT_VERSION == DOCUMENT_VERSION_INVOICE

    def test_render_html_contains_contractor_name(self, invoice_payload) -> None:
        doc = InvoiceDoc(invoice_payload)
        html = doc.render_html()
        assert "Bob el Constructor" in html

    def test_render_html_contains_homeowner_email(self, invoice_payload) -> None:
        doc = InvoiceDoc(invoice_payload)
        html = doc.render_html()
        assert "ana@example.com" in html

    def test_render_html_contains_quote_token(self, invoice_payload) -> None:
        doc = InvoiceDoc(invoice_payload)
        html = doc.render_html()
        assert invoice_payload.quote_token in html

    def test_no_scope_token_leak(self, invoice_payload) -> None:
        doc = InvoiceDoc(invoice_payload)
        html = doc.render_html()
        assert "scope_token" not in html

    def test_shows_payment_intent(self, invoice_payload) -> None:
        doc = InvoiceDoc(invoice_payload)
        html = doc.render_html()
        assert "pi_test_abc" in html

    def test_shows_pagado_marker(self, invoice_payload) -> None:
        doc = InvoiceDoc(invoice_payload)
        html = doc.render_html()
        assert "PAGADO" in html

    def test_iva_calculation_included(self, invoice_payload) -> None:
        doc = InvoiceDoc(invoice_payload)
        html = doc.render_html()
        assert "21%" in html

    def test_filename_has_quote_token(self, invoice_payload) -> None:
        doc = InvoiceDoc(invoice_payload)
        assert invoice_payload.quote_token[:12] in doc.filename()
