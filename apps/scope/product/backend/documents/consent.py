"""Consent hashing + content-addressed template versioning.

D3 — the hard-coded ``"v1"`` literal at ``routes/documents.py:140,255``
is replaced by ``sha256(_base.html.j2 + <kind>.es.html.j2)[:12]``. Any
byte change to the templates self-announces as a new
``DOCUMENT_VERSION_*`` value; consent rows naturally track the version
in force at the moment of capture.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from importlib import resources

__all__ = [
    "DOCUMENT_VERSION_AGREEMENT",
    "DOCUMENT_VERSION_INVOICE",
    "DOCUMENT_VERSION_VARIATION",
    "hash_document",
    "template_fingerprint",
]


@lru_cache(maxsize=None)
def _read_template_bytes(name: str) -> bytes:
    return (resources.files("documents.templates") / name).read_bytes()


def template_fingerprint(template_name: str) -> str:
    """sha256 fingerprint ``(_base + <template_name>)[:12]``.

    Cached for the process lifetime; templates are static files loaded
    from the installed package.
    """

    base = _read_template_bytes("_base.html.j2")
    body = _read_template_bytes(template_name)
    return hashlib.sha256(base + body).hexdigest()[:12]


def hash_document(html: str) -> str:
    """Canonical consent-hash function. ``sha256(html.encode("utf-8")).hexdigest()``.

    Wrapper exists so a future HMAC-based variant has one home without
    rewriting :meth:`AgreementDoc.content_hash`.
    """

    return hashlib.sha256(html.encode("utf-8")).hexdigest()


DOCUMENT_VERSION_AGREEMENT: str = template_fingerprint("agreement.es.html.j2")
DOCUMENT_VERSION_INVOICE: str = template_fingerprint("invoice.es.html.j2")
DOCUMENT_VERSION_VARIATION: str = template_fingerprint("variation.es.html.j2")
