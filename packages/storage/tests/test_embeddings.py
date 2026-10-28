"""Tests for :mod:`storage.embeddings` — the pgvector-backed knowledge index.

Verifies:
- Public surface: ``EMBED_DIM == 1536``, ``EMBED_MODEL`` constant present.
- Hash-skip idempotency on :func:`index_text` when content is unchanged.
- Dimension enforcement — providers returning a wrong-length vector
  raise :class:`core.errors.ValidationError`.
- Input guards (empty chunk_id, empty text) raise
  :class:`ValidationError`.
- :func:`index_batch` dispatches one embed call per batch and skips
  individual chunks whose content hash already matches.
- :func:`search_similar` threads ``filters`` + ``min_score`` through to
  the RPC payload.
- :func:`delete_chunk` returns True / False on 200/204 / other.
- :func:`prune_embeddings` parses the ``Content-Range`` header into a
  row count.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
import pytest
import respx

from core.errors import ValidationError
from storage.embeddings import (
    EMBED_DIM,
    EMBED_MODEL,
    _content_hash,
    _validate_vector,
    delete_chunk,
    index_batch,
    index_text,
    prune_embeddings,
    search_similar,
)


SB_BASE = "https://example.supabase.co"
TABLE_URL = f"{SB_BASE}/rest/v1/knowledge_embeddings"
RPC_URL = f"{SB_BASE}/rest/v1/rpc/match_knowledge_embeddings"


def _vec() -> List[float]:
    v = [0.0] * EMBED_DIM
    v[-1] = 1.0
    return v


# --------------------------------- constants ----------------------------------


class TestConstants:
    def test_dim_is_1536(self) -> None:
        assert EMBED_DIM == 1536

    def test_model_is_openai_small(self) -> None:
        assert "text-embedding-3-small" in EMBED_MODEL


# --------------------------------- helpers ------------------------------------


class TestValidateVector:
    def test_correct_dim_does_not_raise(self) -> None:
        _validate_vector(_vec())

    def test_wrong_dim_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _validate_vector([0.0, 1.0])
        assert "dim mismatch" in str(exc.value)
        assert exc.value.status == 422


class TestContentHash:
    def test_stable_sha256(self) -> None:
        import hashlib

        expected = hashlib.sha256(b"hello").hexdigest()
        assert _content_hash("hello") == expected

    def test_different_text_different_hash(self) -> None:
        assert _content_hash("a") != _content_hash("b")


# --------------------------------- index_text ---------------------------------


class TestIndexText:
    @pytest.mark.asyncio
    async def test_empty_chunk_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            await index_text("", "some text")

    @pytest.mark.asyncio
    async def test_empty_text_raises(self) -> None:
        with pytest.raises(ValidationError):
            await index_text("chunk-1", "")

    @pytest.mark.asyncio
    @respx.mock
    async def test_hash_skip_when_row_exists_with_same_hash(
        self, supabase_env, llm_env, fake_llm_embed
    ) -> None:
        text = "User lives in Madrid"
        existing = {
            "id": "uuid-1",
            "chunk_id": "chunk-1",
            "content": text,
            "content_hash": _content_hash(text),
            "metadata": {},
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }
        respx.get(TABLE_URL).mock(return_value=httpx.Response(200, json=[existing]))
        # If the embed call happens, fake_llm_embed records it; we assert
        # it doesn't.
        result = await index_text("chunk-1", text)
        assert result.chunk_id == "chunk-1"
        assert result.content_hash == _content_hash(text)
        assert fake_llm_embed.calls == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_indexes_new_chunk(
        self, supabase_env, llm_env, fake_llm_embed
    ) -> None:
        respx.get(TABLE_URL).mock(return_value=httpx.Response(200, json=[]))
        post = respx.post(TABLE_URL).mock(
            return_value=httpx.Response(
                201,
                json=[
                    {
                        "id": "uuid-2",
                        "chunk_id": "chunk-new",
                        "content": "Fresh content",
                        "content_hash": _content_hash("Fresh content"),
                        "metadata": {"source": "test"},
                        "created_at": "2026-04-20T12:00:00Z",
                        "updated_at": "2026-04-20T12:00:00Z",
                    }
                ],
            )
        )
        result = await index_text("chunk-new", "Fresh content", metadata={"source": "test"})
        assert result.chunk_id == "chunk-new"
        assert fake_llm_embed.calls == [["Fresh content"]]
        assert post.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_hash_mismatch_triggers_re_embed(
        self, supabase_env, llm_env, fake_llm_embed
    ) -> None:
        existing = {
            "id": "uuid-1",
            "chunk_id": "chunk-1",
            "content": "old text",
            "content_hash": _content_hash("old text"),
            "metadata": {},
        }
        respx.get(TABLE_URL).mock(return_value=httpx.Response(200, json=[existing]))
        respx.post(TABLE_URL).mock(
            return_value=httpx.Response(
                201,
                json=[
                    {
                        "id": "uuid-1",
                        "chunk_id": "chunk-1",
                        "content": "new text",
                        "content_hash": _content_hash("new text"),
                        "metadata": {},
                    }
                ],
            )
        )
        await index_text("chunk-1", "new text")
        assert fake_llm_embed.calls == [["new text"]]

    @pytest.mark.asyncio
    @respx.mock
    async def test_provider_wrong_dim_raises_validation_error(
        self, supabase_env, llm_env, monkeypatch
    ) -> None:
        respx.get(TABLE_URL).mock(return_value=httpx.Response(200, json=[]))

        async def bad_embed(texts, *, model=None, client=None):
            return [[0.1, 0.2]]  # wrong dim

        import llm as _llm

        monkeypatch.setattr(_llm, "embed", bad_embed)

        with pytest.raises(ValidationError) as exc:
            await index_text("chunk-1", "text")
        assert "dim mismatch" in str(exc.value)

    @pytest.mark.asyncio
    @respx.mock
    async def test_provider_empty_response_raises(
        self, supabase_env, llm_env, monkeypatch
    ) -> None:
        respx.get(TABLE_URL).mock(return_value=httpx.Response(200, json=[]))

        async def empty_embed(texts, *, model=None, client=None):
            return []

        import llm as _llm

        monkeypatch.setattr(_llm, "embed", empty_embed)

        with pytest.raises(ValidationError):
            await index_text("chunk-1", "text")


# --------------------------------- index_batch --------------------------------


class TestIndexBatch:
    @pytest.mark.asyncio
    async def test_empty_returns_empty(self) -> None:
        assert await index_batch([]) == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_mixed_cache_hit_and_miss(
        self, supabase_env, llm_env, fake_llm_embed
    ) -> None:
        # chunk-A already exists with matching hash (skip embed).
        # chunk-B doesn't exist (embed + upsert).
        cached_text = "cached text"

        def fetch_handler(request):
            # respx routes by query parameter — both lookups hit this
            # route; respond to each based on chunk_id filter.
            qs = dict(httpx.QueryParams(request.url.query))
            target = qs.get("chunk_id", "").replace("eq.", "")
            if target == "chunk-A":
                return httpx.Response(
                    200,
                    json=[
                        {
                            "id": "uuid-a",
                            "chunk_id": "chunk-A",
                            "content": cached_text,
                            "content_hash": _content_hash(cached_text),
                            "metadata": {},
                        }
                    ],
                )
            return httpx.Response(200, json=[])

        respx.get(TABLE_URL).mock(side_effect=fetch_handler)
        respx.post(TABLE_URL).mock(
            return_value=httpx.Response(
                201,
                json=[
                    {
                        "id": "uuid-b",
                        "chunk_id": "chunk-B",
                        "content": "new text",
                        "content_hash": _content_hash("new text"),
                        "metadata": {},
                    }
                ],
            )
        )

        results = await index_batch(
            [
                ("chunk-A", cached_text, None),
                ("chunk-B", "new text", {"topic": "fresh"}),
            ]
        )
        assert len(results) == 2
        # Only one embed call — for the miss.
        assert fake_llm_embed.calls == [["new text"]]

    @pytest.mark.asyncio
    async def test_empty_chunk_id_or_text_skipped(
        self, supabase_env, llm_env, fake_llm_embed
    ) -> None:
        results = await index_batch([("", "text", None), ("id-1", "", None)])
        # Both skipped; no embed call.
        assert fake_llm_embed.calls == []
        assert results == []


# --------------------------------- search_similar -----------------------------


class TestSearchSimilar:
    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self) -> None:
        assert await search_similar("") == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_happy_path(
        self, supabase_env, llm_env, fake_llm_embed
    ) -> None:
        rx = respx.post(RPC_URL).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "id": "uuid-1",
                        "chunk_id": "c-1",
                        "content": "Madrid property",
                        "content_hash": "x",
                        "metadata": {"city": "madrid"},
                        "score": 0.91,
                    }
                ],
            )
        )
        matches = await search_similar("where in madrid?")
        assert len(matches) == 1
        assert matches[0].score == pytest.approx(0.91)
        assert matches[0].embedding.chunk_id == "c-1"
        assert fake_llm_embed.calls == [["where in madrid?"]]
        assert rx.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_filters_and_min_score_passed_through(
        self, supabase_env, llm_env, fake_llm_embed
    ) -> None:
        rx = respx.post(RPC_URL).mock(
            return_value=httpx.Response(200, json=[])
        )
        await search_similar(
            "q", filters={"contractor_id": "hc-1"}, min_score=0.75, limit=5
        )
        body = rx.calls.last.request.content.decode()
        assert "\"contractor_id\":\"hc-1\"" in body
        assert "\"min_score\":0.75" in body
        assert "\"match_limit\":5" in body

    @pytest.mark.asyncio
    @respx.mock
    async def test_rpc_404_returns_empty(
        self, supabase_env, llm_env, fake_llm_embed
    ) -> None:
        respx.post(RPC_URL).mock(return_value=httpx.Response(404, json={}))
        assert await search_similar("q") == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_non_numeric_score_filtered(
        self, supabase_env, llm_env, fake_llm_embed
    ) -> None:
        respx.post(RPC_URL).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"id": "1", "chunk_id": "c-1", "content": "", "content_hash": "", "score": "NaN"},
                    {"id": "2", "chunk_id": "c-2", "content": "", "content_hash": "", "score": 0.8},
                ],
            )
        )
        matches = await search_similar("q")
        assert len(matches) == 1
        assert matches[0].embedding.chunk_id == "c-2"


# --------------------------------- delete_chunk -------------------------------


class TestDeleteChunk:
    @pytest.mark.asyncio
    async def test_empty_id_returns_false(self) -> None:
        assert await delete_chunk("") is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_204_returns_true(self, supabase_env) -> None:
        respx.delete(TABLE_URL).mock(return_value=httpx.Response(204))
        assert await delete_chunk("chunk-1") is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_404_returns_false(self, supabase_env) -> None:
        respx.delete(TABLE_URL).mock(return_value=httpx.Response(404))
        assert await delete_chunk("chunk-gone") is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_network_error_returns_false(self, supabase_env) -> None:
        respx.delete(TABLE_URL).mock(side_effect=httpx.ConnectError("boom"))
        assert await delete_chunk("chunk-1") is False


# --------------------------------- prune_embeddings ---------------------------


class TestPruneEmbeddings:
    @pytest.mark.asyncio
    @respx.mock
    async def test_parses_content_range_count(self, supabase_env) -> None:
        respx.delete(TABLE_URL).mock(
            return_value=httpx.Response(
                204, headers={"content-range": "0-11/12"}
            )
        )
        deleted = await prune_embeddings(datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert deleted == 12

    @pytest.mark.asyncio
    @respx.mock
    async def test_missing_content_range_returns_zero(
        self, supabase_env
    ) -> None:
        respx.delete(TABLE_URL).mock(return_value=httpx.Response(204))
        deleted = await prune_embeddings(datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert deleted == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_filters_applied_to_url_params(
        self, supabase_env
    ) -> None:
        rx = respx.delete(TABLE_URL).mock(
            return_value=httpx.Response(
                204, headers={"content-range": "0-0/3"}
            )
        )
        deleted = await prune_embeddings(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            filters={"contractor_id": "hc-1"},
        )
        assert deleted == 3
        call = rx.calls.last
        assert "metadata-%3E%3Econtractor_id=eq.hc-1" in str(call.request.url) or \
               "metadata->>contractor_id=eq.hc-1" in str(call.request.url)
