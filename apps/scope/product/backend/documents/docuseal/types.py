"""docuSeal DTOs (Pydantic models)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict

__all__ = [
    "DocusealSubmitter",
    "DocusealAttachment",
    "DocusealSubmission",
    "DocusealWebhookEvent",
]


_STRICT = ConfigDict(extra="forbid")


class DocusealSubmitter(BaseModel):
    """One signer in a submission."""

    model_config = _STRICT

    role: Literal["homeowner", "contractor", "witness"]
    email: str
    name: Optional[str] = None
    phone: Optional[str] = None


class DocusealAttachment(BaseModel):
    """File attached to a docuSeal submission."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    filename: str
    content: bytes
    media_type: Literal["application/pdf"] = "application/pdf"


class DocusealSubmission(BaseModel):
    """Response shape from :meth:`DocusealClient.create_submission`."""

    model_config = _STRICT

    id: str
    external_id: str
    template_id: str
    status: Literal["pending", "completed", "declined", "expired"]
    submitters: List[DocusealSubmitter]
    signing_urls: Dict[str, str]
    created_at: datetime
    signed_document_url: Optional[str] = None


class DocusealWebhookEvent(BaseModel):
    """Parsed webhook body from docuSeal.

    ``extra="allow"`` because docuSeal occasionally ships additional
    fields with new event types; we don't want a payload-shape regression
    to 500 a webhook.
    """

    model_config = ConfigDict(extra="allow")

    event_type: str
    submission_id: str
    external_id: str
    status: str
    occurred_at: datetime
    data: Dict[str, Any]
