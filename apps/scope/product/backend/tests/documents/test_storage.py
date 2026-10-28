"""Unit tests for `documents.storage.DocumentStorage` — S3 + DB mocked.

The live :func:`core.db.get_supabase` returns an async Supabase adapter.
We patch it to return an ``AsyncMock`` with the two methods
:class:`DocumentStorage` actually uses: ``insert`` and ``update``.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_s3() -> MagicMock:
    client = MagicMock()
    client.put_object.return_value = {"ETag": '"abc"'}
    client.generate_presigned_url.return_value = "https://s3.fake/presigned"
    client.delete_object.return_value = {}
    return client


@pytest.fixture
def mock_supabase() -> MagicMock:
    sb = MagicMock()
    sb.insert = AsyncMock(return_value=None)
    sb.select = AsyncMock(return_value=[])
    sb.update = AsyncMock(return_value=None)
    return sb


@pytest.fixture
def storage(mock_s3: MagicMock, mock_supabase: MagicMock):
    from documents import DocumentStorage

    return DocumentStorage(bucket="leo-documents-test", s3=mock_s3, sb=mock_supabase)


class TestDocumentStorage:
    @pytest.mark.asyncio
    async def test_put_uploads_and_inserts_row(
        self, storage, mock_s3: MagicMock, mock_supabase: MagicMock, quote_payload
    ) -> None:
        from documents import AgreementDoc

        doc = AgreementDoc(quote_payload)
        stored = await storage.put(doc, content=b"%PDF-fake")

        assert mock_s3.put_object.called
        put_kwargs = mock_s3.put_object.call_args.kwargs
        assert put_kwargs["Bucket"] == "leo-documents-test"
        assert put_kwargs["ContentType"] == "application/pdf"
        assert put_kwargs["ACL"] == "private"

        assert mock_supabase.insert.awaited
        insert_args = mock_supabase.insert.call_args
        assert insert_args.args[0] == "documents"
        row = insert_args.args[1]
        assert row["kind"] == "agreement"
        assert row["quote_token"] == quote_payload.quote_token

        assert stored.kind.value == "agreement"
        assert stored.s3_bucket == "leo-documents-test"

    @pytest.mark.asyncio
    async def test_get_url_generates_presigned(
        self, storage, mock_s3: MagicMock
    ) -> None:
        from datetime import datetime, timezone

        from documents import DocumentKind, StoredDocument

        sd = StoredDocument(
            id="abc",
            kind=DocumentKind.AGREEMENT,
            quote_token="q_x",
            version="v1",
            filename="leo-agreement-q_x.pdf",
            media_type="application/pdf",
            size_bytes=1000,
            s3_bucket="leo-documents-test",
            s3_key="agreements/q_x/v1/leo-agreement-q_x.pdf",
            created_at=datetime.now(timezone.utc),
        )
        url = await storage.get_url(sd, expires_in_s=300)
        assert url == "https://s3.fake/presigned"
        assert mock_s3.generate_presigned_url.call_args.kwargs["ExpiresIn"] == 300

    @pytest.mark.asyncio
    async def test_delete_calls_s3_and_db_update(
        self, storage, mock_s3: MagicMock, mock_supabase: MagicMock
    ) -> None:
        from datetime import datetime, timezone

        from documents import DocumentKind, StoredDocument

        sd = StoredDocument(
            id="abc",
            kind=DocumentKind.AGREEMENT,
            quote_token="q_x",
            version="v1",
            filename="leo-agreement-q_x.pdf",
            media_type="application/pdf",
            size_bytes=1000,
            s3_bucket="leo-documents-test",
            s3_key="agreements/q_x/v1/leo-agreement-q_x.pdf",
            created_at=datetime.now(timezone.utc),
        )
        await storage.delete(sd)
        mock_s3.delete_object.assert_called_once()
        mock_supabase.update.assert_awaited_once()
