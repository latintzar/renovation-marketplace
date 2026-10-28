"""Tests for :mod:`llm.stream`."""

from __future__ import annotations

import pytest

from llm.stream import stream


class TestStreamSkeleton:
    @pytest.mark.asyncio
    async def test_single_terminal_chunk(self, monkeypatch, mock_async_client):
        from llm.providers import litellm_proxy as _proxy

        orig = _proxy.complete

        async def patched(messages, **kwargs):
            return await orig(messages, client=mock_async_client(), **kwargs)

        monkeypatch.setattr(_proxy, "complete", patched)

        chunks = []
        async for c in stream("hi", model="anthropic/claude-haiku-4.5"):
            chunks.append(c)

        assert len(chunks) == 1
        assert chunks[0].done
        assert chunks[0].delta == "hello"
        assert chunks[0].finish_reason == "stop"
