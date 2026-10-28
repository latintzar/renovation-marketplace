"""InvoiceDoc — post-completion factura.

Invoices are regenerable from inputs; no ``content_hash``. The caller
(``apps/scope-backend/routes/documents.py``) enforces the
``quote.status == 'complete'`` gate; this class does not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from .consent import DOCUMENT_VERSION_INVOICE
from .contexts import build_invoice_context
from .payloads import DocumentKind, InvoicePayload, Locale
from .render import render_html, render_pdf

__all__ = ["InvoiceDoc"]


@dataclass
class InvoiceDoc:
    """Post-completion Invoice (Factura de Obra)."""

    payload: InvoicePayload
    locale: Locale = Locale.ES
    kind: DocumentKind = field(default=DocumentKind.INVOICE, init=False)
    DOCUMENT_VERSION: str = field(default=DOCUMENT_VERSION_INVOICE, init=False)

    def template_name(self) -> str:
        return f"invoice.{self.locale.value}.html.j2"

    def render_html(self) -> str:
        ctx = build_invoice_context(self.payload)
        return render_html(self.template_name(), ctx)

    async def render_pdf(self, *, base_url: Optional[str] = None) -> bytes:
        return await render_pdf(self.render_html(), base_url=base_url)

    def filename(self, *, ext: Literal["pdf", "html"] = "pdf") -> str:
        slug = self.payload.quote_token[:12]
        return f"leo-invoice-{slug}.{ext}"
