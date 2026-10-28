"""HTTP client for docuSeal (api.docuseal.com).

One class, one API key, construct-time overridable for tests. Uses
:func:`core.http.http_client` for connection pooling;
:func:`core.resilience.async_retry` for transient failures.
"""

from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence

from core.http import http_client
from core.resilience import async_retry

from .types import (
    DocusealAttachment,
    DocusealSubmission,
    DocusealSubmitter,
)

__all__ = ["DocusealClient", "get_docuseal"]


class DocusealClient:
    """Thin async client for docuSeal.

    Constructor args:
      - ``api_key``: required at call time; constructor accepts
        ``None`` so :func:`get_docuseal` can hand out a client even
        when the env var isn't set yet (calls raise at use time).
      - ``base_url``: override for tests; defaults to ``api.docuseal.com``.
      - ``http``: ``async with …:`` factory for an httpx-like client;
        tests plug in a mock transport via ``core.http.http_client``.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: str = "https://api.docuseal.com",
        http: Any = None,
    ) -> None:
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._http = http or http_client

    def _headers(self) -> Dict[str, str]:
        if not self._api_key:
            raise RuntimeError("DOCUSEAL_API_KEY not set")
        return {
            "X-Auth-Token": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def create_submission(
        self,
        *,
        template_id: str,
        external_id: str,
        submitters: Sequence[DocusealSubmitter],
        fields: Optional[Dict[str, Any]] = None,
        attachments: Optional[Sequence[DocusealAttachment]] = None,
    ) -> DocusealSubmission:
        """Create a signature submission. Idempotent on ``external_id``.

        ``external_id`` convention:
        ``f"{quote_token}:{DOCUMENT_VERSION}"``.
        """

        body: Dict[str, Any] = {
            "template_id": template_id,
            "external_id": external_id,
            "submitters": [
                {
                    "role": s.role,
                    "email": s.email,
                    "name": s.name,
                    "phone": s.phone,
                }
                for s in submitters
            ],
        }
        if fields:
            body["fields"] = fields
        if attachments:
            body["attachments"] = [
                {
                    "filename": a.filename,
                    "content": base64.b64encode(a.content).decode("ascii"),
                    "media_type": a.media_type,
                }
                for a in attachments
            ]

        @async_retry(attempts=3)
        async def _send() -> Dict[str, Any]:
            async with self._http(timeout=30) as client:
                resp = await client.post(
                    f"{self.base_url}/submissions",
                    json=body,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return resp.json()

        payload = await _send()
        return _submission_from_payload(payload, submitters, template_id, external_id)

    async def get_submission(self, submission_id: str) -> DocusealSubmission:
        @async_retry(attempts=3)
        async def _send() -> Dict[str, Any]:
            async with self._http(timeout=30) as client:
                resp = await client.get(
                    f"{self.base_url}/submissions/{submission_id}",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return resp.json()

        payload = await _send()
        return _submission_from_payload(payload, [], "", "")

    async def get_document_urls(self, submission_id: str) -> List[str]:
        """Presigned URLs for the signed documents (post-completion)."""

        @async_retry(attempts=3)
        async def _send() -> Dict[str, Any]:
            async with self._http(timeout=30) as client:
                resp = await client.get(
                    f"{self.base_url}/submissions/{submission_id}/documents",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return resp.json()

        payload = await _send()
        docs = payload.get("documents") or []
        return [d.get("url") for d in docs if d.get("url")]

    async def cancel_submission(self, submission_id: str) -> None:
        @async_retry(attempts=3)
        async def _send() -> None:
            async with self._http(timeout=30) as client:
                resp = await client.delete(
                    f"{self.base_url}/submissions/{submission_id}",
                    headers=self._headers(),
                )
                resp.raise_for_status()

        await _send()


def _parse_iso(value: Optional[str]) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    normalised = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalised)


def _submission_from_payload(
    payload: Dict[str, Any],
    default_submitters: Sequence[DocusealSubmitter],
    default_template_id: str,
    default_external_id: str,
) -> DocusealSubmission:
    submitters_raw = payload.get("submitters") or [
        {"role": s.role, "email": s.email, "name": s.name, "phone": s.phone}
        for s in default_submitters
    ]
    submitters = [DocusealSubmitter(**s) for s in submitters_raw]
    signing_urls = payload.get("signing_urls") or {
        s.role: s_row.get("signing_url", "")
        for s, s_row in zip(default_submitters, submitters_raw)
        if s_row.get("signing_url")
    }
    return DocusealSubmission(
        id=str(payload.get("id", "")),
        external_id=str(payload.get("external_id") or default_external_id),
        template_id=str(payload.get("template_id") or default_template_id),
        status=payload.get("status", "pending"),
        submitters=submitters,
        signing_urls=signing_urls,
        created_at=_parse_iso(payload.get("created_at")),
        signed_document_url=payload.get("signed_document_url"),
    )


@lru_cache(maxsize=1)
def get_docuseal() -> DocusealClient:
    """Process-wide singleton. ``api_key`` read from ``DOCUSEAL_API_KEY``."""

    return DocusealClient(api_key=os.getenv("DOCUSEAL_API_KEY"))
