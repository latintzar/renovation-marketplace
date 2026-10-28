"""Tests for :mod:`llm.embed`."""

from __future__ import annotations

import httpx
import pytest

from llm.embed import embed, embed_sync
from llm.errors import InvalidResponseShape, ProviderError


def _make_embedding_response(vectors):
    return {
        "data": [{"embedding": v, "index": i} for i, v in enumerate(vectors)],
        "model": "openai/text-embedding-3-small",
    }


class TestEmbedSync:
    def test_happy_path(self):
        def handler(request):
            return httpx.Response(200, json=_make_embedding_response([[0.1, 0.2]]))

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        try:
            vecs = embed_sync(["hi"], client=client)
        finally:
            client.close()

        assert len(vecs) == 1
        assert vecs[0] == [0.1, 0.2]

    def test_empty_list_returns_empty(self):
        assert embed_sync([]) == []

    def test_invalid_shape_raises(self):
        def handler(request):
            return httpx.Response(200, json={"model": "x"})

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        try:
            with pytest.raises(InvalidResponseShape):
                embed_sync(["hi"], client=client)
        finally:
            client.close()

    def test_http_error_wrapped(self):
        def handler(request):
            return httpx.Response(500, json={})

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        try:
            with pytest.raises(ProviderError):
                embed_sync(["hi"], client=client)
        finally:
            client.close()


class TestEmbedAsync:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        def handler(request):
            return httpx.Response(
                200, json=_make_embedding_response([[0.3, 0.4], [0.5, 0.6]])
            )

        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(transport=transport)
        try:
            vecs = await embed(["a", "b"], client=client)
        finally:
            await client.aclose()

        assert len(vecs) == 2
        assert vecs[1] == [0.5, 0.6]

    @pytest.mark.asyncio
    async def test_empty_returns_empty(self):
        assert await embed([]) == []
