"""Unit tests for `documents.consent` — template fingerprint + content hash."""
from __future__ import annotations

from documents import (
    DOCUMENT_VERSION_AGREEMENT,
    DOCUMENT_VERSION_INVOICE,
    DOCUMENT_VERSION_VARIATION,
    hash_document,
    template_fingerprint,
)


def test_fingerprint_deterministic() -> None:
    a = template_fingerprint("agreement.es.html.j2")
    b = template_fingerprint("agreement.es.html.j2")
    assert a == b
    assert len(a) == 12


def test_fingerprints_differ_per_kind() -> None:
    assert DOCUMENT_VERSION_AGREEMENT != DOCUMENT_VERSION_INVOICE
    assert DOCUMENT_VERSION_INVOICE != DOCUMENT_VERSION_VARIATION
    assert DOCUMENT_VERSION_AGREEMENT != DOCUMENT_VERSION_VARIATION


def test_fingerprint_constants_match_function() -> None:
    assert DOCUMENT_VERSION_AGREEMENT == template_fingerprint("agreement.es.html.j2")
    assert DOCUMENT_VERSION_INVOICE == template_fingerprint("invoice.es.html.j2")
    assert DOCUMENT_VERSION_VARIATION == template_fingerprint("variation.es.html.j2")


def test_hash_document_string() -> None:
    h = hash_document("<html>abc</html>")
    assert len(h) == 64


def test_hash_document_deterministic() -> None:
    assert hash_document("abc") == hash_document("abc")


def test_hash_document_content_sensitive() -> None:
    assert hash_document("abc") != hash_document("abd")
