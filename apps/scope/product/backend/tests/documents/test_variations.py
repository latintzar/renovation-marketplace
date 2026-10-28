"""Unit tests for `documents.variations.VariationDoc` — currently a stub."""
from __future__ import annotations

import pytest

from documents import VariationDoc


class TestVariationDoc:
    def test_template_name(self, variation_payload) -> None:
        doc = VariationDoc(variation_payload)
        assert doc.template_name() == "variation.es.html.j2"

    def test_render_html_placeholder(self, variation_payload) -> None:
        """The current template is a legal placeholder; it must still render
        with all payload fields present. Once legal copy lands the assertions
        below can be hardened."""
        doc = VariationDoc(variation_payload)
        html = doc.render_html()
        assert variation_payload.quote_token in html
        assert variation_payload.variation_id in html

    def test_render_html_memoized(self, variation_payload) -> None:
        doc = VariationDoc(variation_payload)
        assert doc.render_html() is doc.render_html()

    def test_content_hash_deterministic(self, variation_payload) -> None:
        a = VariationDoc(variation_payload).content_hash()
        b = VariationDoc(variation_payload).content_hash()
        assert a == b
        assert len(a) == 64

    def test_filename_has_variation_id(self, variation_payload) -> None:
        doc = VariationDoc(variation_payload)
        assert variation_payload.variation_id in doc.filename()

    def test_filename_default_pdf(self, variation_payload) -> None:
        doc = VariationDoc(variation_payload)
        assert doc.filename().endswith(".pdf")
