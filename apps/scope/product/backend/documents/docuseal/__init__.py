"""docuSeal adapter — thin HTTP client + webhook helpers.

Subpackage layout:

- :mod:`documents.docuseal.types` — DTOs.
- :mod:`documents.docuseal.client` — :class:`DocusealClient` + singleton factory.
- :mod:`documents.docuseal.webhook` — signature verification + event parser.
"""

from .client import DocusealClient, get_docuseal
from .types import (
    DocusealAttachment,
    DocusealSubmission,
    DocusealSubmitter,
    DocusealWebhookEvent,
)
from .webhook import parse_webhook_event, verify_docuseal_webhook

__all__ = [
    "DocusealAttachment",
    "DocusealClient",
    "DocusealSubmission",
    "DocusealSubmitter",
    "DocusealWebhookEvent",
    "get_docuseal",
    "parse_webhook_event",
    "verify_docuseal_webhook",
]
