"""AgreementDoc + send_agreement_for_signature (docuSeal helper).

The Construction Agreement is the canonical legal document and the
only one hashed for consent (D2). ``content_hash`` is memoised per
instance so ``record_consent`` + ``DocumentStorage.put`` don't render
twice.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal, Optional

from .consent import DOCUMENT_VERSION_AGREEMENT, hash_document
from .contexts import build_agreement_context
from .payloads import DocumentKind, Locale, QuotePayload
from .render import render_html, render_pdf

__all__ = ["AgreementDoc", "send_agreement_for_signature"]


@dataclass
class AgreementDoc:
    """Construction Agreement (Acuerdo de Obra).

    Hashed at consent time via :meth:`content_hash`. Byte-identical
    renders across processes given the same payload + template
    fingerprint. Ephemeral memoisation avoids rendering twice when the
    caller also stores the document.
    """

    payload: QuotePayload
    locale: Locale = Locale.ES
    kind: DocumentKind = field(default=DocumentKind.AGREEMENT, init=False)
    DOCUMENT_VERSION: str = field(default=DOCUMENT_VERSION_AGREEMENT, init=False)
    _cached_html: Optional[str] = field(default=None, init=False, repr=False)
    _cached_hash: Optional[str] = field(default=None, init=False, repr=False)

    def template_name(self) -> str:
        return f"agreement.{self.locale.value}.html.j2"

    def render_html(self) -> str:
        """Render the agreement HTML. Memoised for the instance lifetime."""

        if self._cached_html is None:
            ctx = build_agreement_context(self.payload)
            self._cached_html = render_html(self.template_name(), ctx)
        return self._cached_html

    async def render_pdf(self, *, base_url: Optional[str] = None) -> bytes:
        """Render the agreement PDF. Not memoised — callers rarely render
        the same PDF twice, and a 200-800 KB byte cache on every doc
        instance is noise."""

        return await render_pdf(self.render_html(), base_url=base_url)

    def content_hash(self) -> str:
        """sha256 hex digest of ``render_html()`` bytes. Memoised."""

        if self._cached_hash is None:
            self._cached_hash = hash_document(self.render_html())
        return self._cached_hash

    def filename(self, *, ext: Literal["pdf", "html"] = "pdf") -> str:
        """Canonical download filename: ``leo-agreement-<12-char-token>.<ext>``."""

        slug = self.payload.quote_token[:12]
        return f"leo-agreement-{slug}.{ext}"


async def send_agreement_for_signature(
    payload: QuotePayload,
    *,
    template_id: Optional[str] = None,
    docuseal: Optional["object"] = None,
    storage: Optional["object"] = None,
    base_url: Optional[str] = None,
) -> "object":
    """End-to-end: render agreement PDF, submit to docuSeal.

    Glue helper — delegates to :mod:`documents.docuseal` and
    :mod:`documents.storage`. Defaults:

    - ``template_id`` → ``DOCUSEAL_TEMPLATE_AGREEMENT`` env
    - ``docuseal`` → :func:`documents.docuseal.get_docuseal`
    - ``storage`` → :func:`documents.storage.get_storage` (optional;
      caller may pass ``None`` to skip the S3 write)

    Returns the :class:`DocusealSubmission` created on docuSeal's side.
    """

    from .docuseal import (
        DocusealAttachment,
        DocusealSubmitter,
        get_docuseal,
    )

    doc = AgreementDoc(payload)
    pdf = await doc.render_pdf(base_url=base_url)
    client = docuseal or get_docuseal()
    resolved_template_id = template_id or os.getenv("DOCUSEAL_TEMPLATE_AGREEMENT")
    if not resolved_template_id:
        raise RuntimeError("DOCUSEAL_TEMPLATE_AGREEMENT not set")
    submission = await client.create_submission(
        template_id=resolved_template_id,
        external_id=f"{payload.quote_token}:{doc.DOCUMENT_VERSION}",
        submitters=[
            DocusealSubmitter(role="homeowner", email=payload.homeowner.email, name=payload.homeowner.name),
            DocusealSubmitter(role="contractor", email=payload.contractor.email, name=payload.contractor.name),
        ],
        attachments=[
            DocusealAttachment(
                filename=doc.filename(ext="pdf"),
                content=pdf,
                media_type="application/pdf",
            )
        ],
        fields={
            "quote_token": payload.quote_token,
            "agreement_date": payload.agreement_date.isoformat(),
            "document_version": doc.DOCUMENT_VERSION,
        },
    )
    if storage is not None:
        await storage.put(doc, content=pdf, media_type="application/pdf")
    return submission
