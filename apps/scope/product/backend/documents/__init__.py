"""apps/scope/product/backend/documents — legal & financial document lifecycle (scope-local).

Demoted from ``packages/documents`` in Phase 5 Wave 8: today only the
scope app renders Agreement/Invoice/Variation PDFs and submits them to
DocuSeal, so the engine is scope-policy, not a shared capability. The
public API is unchanged — ``from documents import ...`` still resolves
because ``apps/scope/product/backend/`` is on ``PYTHONPATH`` for the scope
backend. When a second app needs PDF/consent primitives, regraduate
``render.py`` + ``consent.py`` + ``dates.py`` + ``docuseal/`` + ``Money``
+ ``Locale`` + ``hash_document`` to ``packages/doc_engine/`` and leave
the Leo-specific payloads, templates, and context builders here.

Public API — ``from documents import X``:

- **Payloads / enums** (9): :class:`Money`, :class:`Milestone`,
  :class:`PartyInfo`, :class:`JobInfo`, :class:`QuotePayload`,
  :class:`InvoicePayload`, :class:`VariationPayload`, :class:`Locale`,
  :class:`DocumentKind`.
- **Docs** (4): :class:`AgreementDoc`, :class:`InvoiceDoc`,
  :class:`VariationDoc`, :func:`send_agreement_for_signature`.
- **Render** (4): :func:`render_html`, :func:`render_pdf`,
  :class:`PDFRenderError`, :func:`set_override_dir`.
- **Consent / versioning** (5):
  :data:`DOCUMENT_VERSION_AGREEMENT`, :data:`DOCUMENT_VERSION_INVOICE`,
  :data:`DOCUMENT_VERSION_VARIATION`, :func:`hash_document`,
  :func:`template_fingerprint`.
- **Storage** (3): :class:`DocumentStorage`, :func:`get_storage`,
  :class:`StoredDocument`.
- **docuSeal** (8): :class:`DocusealClient`, :func:`get_docuseal`,
  :class:`DocusealSubmission`, :class:`DocusealSubmitter`,
  :class:`DocusealAttachment`, :class:`DocusealWebhookEvent`,
  :func:`verify_docuseal_webhook`, :func:`parse_webhook_event`.
- **Dates** (2): :func:`format_date_es`, :func:`format_date`.

Total: 35 symbols.
"""

from .agreements import AgreementDoc, send_agreement_for_signature
from .consent import (
    DOCUMENT_VERSION_AGREEMENT,
    DOCUMENT_VERSION_INVOICE,
    DOCUMENT_VERSION_VARIATION,
    hash_document,
    template_fingerprint,
)
from .dates import format_date, format_date_es
from .docuseal import (
    DocusealAttachment,
    DocusealClient,
    DocusealSubmission,
    DocusealSubmitter,
    DocusealWebhookEvent,
    get_docuseal,
    parse_webhook_event,
    verify_docuseal_webhook,
)
from .invoices import InvoiceDoc
from .payloads import (
    DocumentKind,
    InvoicePayload,
    JobInfo,
    Locale,
    Milestone,
    Money,
    PartyInfo,
    QuotePayload,
    VariationPayload,
)
from .render import PDFRenderError, render_html, render_pdf, set_override_dir
from .storage import DocumentStorage, StoredDocument, get_storage
from .variations import VariationDoc

__all__ = [
    "AgreementDoc",
    "DOCUMENT_VERSION_AGREEMENT",
    "DOCUMENT_VERSION_INVOICE",
    "DOCUMENT_VERSION_VARIATION",
    "DocumentKind",
    "DocumentStorage",
    "DocusealAttachment",
    "DocusealClient",
    "DocusealSubmission",
    "DocusealSubmitter",
    "DocusealWebhookEvent",
    "InvoiceDoc",
    "InvoicePayload",
    "JobInfo",
    "Locale",
    "Milestone",
    "Money",
    "PDFRenderError",
    "PartyInfo",
    "QuotePayload",
    "StoredDocument",
    "VariationDoc",
    "VariationPayload",
    "format_date",
    "format_date_es",
    "get_docuseal",
    "get_storage",
    "hash_document",
    "parse_webhook_event",
    "render_html",
    "render_pdf",
    "send_agreement_for_signature",
    "set_override_dir",
    "template_fingerprint",
    "verify_docuseal_webhook",
]
