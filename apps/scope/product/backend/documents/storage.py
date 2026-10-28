"""S3 persistence facade + ``documents`` table adapter.

D13 — single bucket ``leo-documents-{env}``, typed object keys, 7-day
presigned URLs. All objects are private.

D14 — ``DocumentStorage.put`` inserts a ``documents`` row via
:func:`core.db.get_supabase`; ``get_by_id`` / ``find`` read it back.

The package depends on ``core`` only — never on app code, never on
route handlers.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict

from core.db import get_supabase

from .agreements import AgreementDoc
from .invoices import InvoiceDoc
from .payloads import DocumentKind
from .variations import VariationDoc

__all__ = ["StoredDocument", "DocumentStorage", "get_storage"]


class StoredDocument(BaseModel):
    """Row in the ``documents`` table. ``id`` is a server-generated UUID."""

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: DocumentKind
    quote_token: str
    version: str
    filename: str
    media_type: str
    size_bytes: int
    s3_bucket: str
    s3_key: str
    created_at: datetime


AnyDoc = Union[AgreementDoc, InvoiceDoc, VariationDoc]


class DocumentStorage:
    """S3 persistence facade + ``documents`` table adapter.

    Constructor args:
      - ``bucket``: S3 bucket name (no ``s3://`` prefix).
      - ``region``: AWS region for the boto3 client; default
        ``"eu-west-1"`` (closest to Spain).
      - ``s3``: pre-built ``boto3.client("s3")``; if ``None``, built on
        first use via :func:`core.aws.leo_boto3_client`.
    """

    def __init__(
        self,
        *,
        bucket: str,
        region: str = "eu-west-1",
        s3: Any = None,
        sb: Any = None,
    ) -> None:
        self.bucket = bucket
        self.region = region
        self._s3 = s3
        self._sb = sb

    async def _supabase(self) -> Any:
        if self._sb is None:
            self._sb = await get_supabase()
        return self._sb

    def _client(self) -> Any:
        if self._s3 is None:
            from core.aws import leo_boto3_client
            self._s3 = leo_boto3_client("s3", region_name=self.region)
        return self._s3

    def _key(self, doc: AnyDoc) -> str:
        kind = doc.kind.value
        token = doc.payload.quote_token
        version = doc.DOCUMENT_VERSION
        filename = doc.filename(ext="pdf")
        return f"{kind}s/{token}/v{version}/{filename}"

    async def put(
        self,
        doc: AnyDoc,
        *,
        content: bytes,
        media_type: Literal["application/pdf", "text/html"] = "application/pdf",
    ) -> StoredDocument:
        """Upload document bytes to S3 + insert ``documents`` row.

        Idempotent on ``(kind, quote_token, version)`` — a second
        ``put`` with the same key replaces the S3 object but inserts a
        fresh row (audit trail).
        """

        key = self._key(doc)
        self._client().put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=media_type,
            ACL="private",
        )
        row_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        sb = await self._supabase()
        inserted = await sb.insert(
            "documents",
            {
                "id": row_id,
                "kind": doc.kind.value,
                "quote_token": doc.payload.quote_token,
                "version": doc.DOCUMENT_VERSION,
                "filename": doc.filename(ext="pdf" if media_type == "application/pdf" else "html"),
                "media_type": media_type,
                "size_bytes": len(content),
                "s3_bucket": self.bucket,
                "s3_key": key,
                "created_at": now.isoformat(),
            },
        )
        return StoredDocument.model_validate(inserted or {
            "id": row_id,
            "kind": doc.kind.value,
            "quote_token": doc.payload.quote_token,
            "version": doc.DOCUMENT_VERSION,
            "filename": doc.filename(ext="pdf" if media_type == "application/pdf" else "html"),
            "media_type": media_type,
            "size_bytes": len(content),
            "s3_bucket": self.bucket,
            "s3_key": key,
            "created_at": now.isoformat(),
        })

    async def get_by_id(self, id: str) -> Optional[StoredDocument]:
        sb = await self._supabase()
        rows = await sb.select("documents", filters={"id": f"eq.{id}"}, limit=1)
        if not rows:
            return None
        return StoredDocument.model_validate(rows[0])

    async def find(
        self,
        *,
        kind: DocumentKind,
        quote_token: str,
    ) -> Optional[StoredDocument]:
        """Most recent ``StoredDocument`` for the (kind, quote_token) pair."""

        sb = await self._supabase()
        rows = await sb.select(
            "documents",
            filters={
                "kind": f"eq.{kind.value}",
                "quote_token": f"eq.{quote_token}",
            },
            order="created_at.desc",
            limit=1,
        )
        if not rows:
            return None
        return StoredDocument.model_validate(rows[0])

    async def get_url(
        self,
        stored: Union[StoredDocument, str],
        *,
        expires_in_s: int = 604800,
    ) -> str:
        """Presigned GET URL. Accepts :class:`StoredDocument` or raw S3 key."""

        key = stored.s3_key if isinstance(stored, StoredDocument) else stored
        return self._client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in_s,
        )

    async def delete(self, stored: Union[StoredDocument, str]) -> None:
        key = stored.s3_key if isinstance(stored, StoredDocument) else stored
        self._client().delete_object(Bucket=self.bucket, Key=key)
        if isinstance(stored, StoredDocument):
            sb = await self._supabase()
            await sb.update(
                "documents",
                filters={"id": f"eq.{stored.id}"},
                patch={"deleted_at": datetime.now(timezone.utc).isoformat()},
            )


def get_storage() -> DocumentStorage:
    """Process-wide factory. Bucket name derived from ``LEO_ENV``."""

    env = os.getenv("LEO_ENV", "dev")
    return DocumentStorage(bucket=f"leo-documents-{env}")
