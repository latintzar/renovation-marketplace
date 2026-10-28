"""VariationDoc — change-order artefact (stub template).

Template exists (placeholder legal copy); :meth:`content_hash` mirrors
:class:`AgreementDoc` because signed variations need consent-hash
parity with agreements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from .consent import DOCUMENT_VERSION_VARIATION, hash_document
from .contexts import build_variation_context
from .payloads import DocumentKind, Locale, VariationPayload
from .render import render_html, render_pdf

__all__ = ["VariationDoc"]


@dataclass
class VariationDoc:
    """Variation of Work / Change-Order (template stub today)."""

    payload: VariationPayload
    locale: Locale = Locale.ES
    kind: DocumentKind = field(default=DocumentKind.VARIATION, init=False)
    DOCUMENT_VERSION: str = field(default=DOCUMENT_VERSION_VARIATION, init=False)
    _cached_html: Optional[str] = field(default=None, init=False, repr=False)
    _cached_hash: Optional[str] = field(default=None, init=False, repr=False)

    def template_name(self) -> str:
        return f"variation.{self.locale.value}.html.j2"

    def render_html(self) -> str:
        if self._cached_html is None:
            ctx = build_variation_context(self.payload)
            self._cached_html = render_html(self.template_name(), ctx)
        return self._cached_html

    async def render_pdf(self, *, base_url: Optional[str] = None) -> bytes:
        return await render_pdf(self.render_html(), base_url=base_url)

    def content_hash(self) -> str:
        if self._cached_hash is None:
            self._cached_hash = hash_document(self.render_html())
        return self._cached_hash

    def filename(self, *, ext: Literal["pdf", "html"] = "pdf") -> str:
        slug = self.payload.quote_token[:12]
        vid = self.payload.variation_id
        return f"leo-variation-{slug}-{vid}.{ext}"
