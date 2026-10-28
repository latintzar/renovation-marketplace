"""Tests for :mod:`llm.providers.litellm_proxy`."""

from __future__ import annotations

import httpx
import pytest

from llm.errors import (
    InvalidResponseShape,
    ProviderError,
    ProviderUnavailable,
    RateLimitError,
)
from llm.providers import litellm_proxy
from llm.providers.base import Message, Tool


# ---------------------------------------------------------------------------
# Async tests
# ---------------------------------------------------------------------------


class TestCompleteAsync:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_async_client, mock_proxy_response):
        client = mock_async_client(payload=mock_proxy_response(content="sure"))
        resp = await litellm_proxy.complete(
            [Message(role="user", content="hi")],
            model="anthropic/claude-haiku-4.5",
            client=client,
        )
        assert resp.text == "sure"
        assert resp.finish_reason == "stop"
        assert resp.usage is not None
        assert resp.usage.total_tokens == 15

    @pytest.mark.asyncio
    async def test_429_maps_to_rate_limit(self, mock_async_client):
        client = mock_async_client(
            status_code=429,
            payload={"error": "rate limit"},
        )
        with pytest.raises(RateLimitError):
            await litellm_proxy.complete(
                [Message(role="user", content="hi")],
                model="anthropic/claude-haiku-4.5",
                client=client,
            )

    @pytest.mark.asyncio
    async def test_500_maps_to_provider_unavailable(self, mock_async_client):
        client = mock_async_client(status_code=500, payload={})
        with pytest.raises(ProviderUnavailable):
            await litellm_proxy.complete(
                [Message(role="user", content="hi")],
                model="anthropic/claude-haiku-4.5",
                client=client,
            )

    @pytest.mark.asyncio
    async def test_400_maps_to_provider_error(self, mock_async_client):
        client = mock_async_client(status_code=400, payload={})
        with pytest.raises(ProviderError) as exc_info:
            await litellm_proxy.complete(
                [Message(role="user", content="hi")],
                model="anthropic/claude-haiku-4.5",
                client=client,
            )
        assert not isinstance(exc_info.value, RateLimitError)
        assert not isinstance(exc_info.value, ProviderUnavailable)

    @pytest.mark.asyncio
    async def test_missing_content_raises_invalid_shape(self, mock_async_client):
        client = mock_async_client(payload={"choices": [{"finish_reason": "stop"}]})
        with pytest.raises(InvalidResponseShape):
            await litellm_proxy.complete(
                [Message(role="user", content="hi")],
                model="anthropic/claude-haiku-4.5",
                client=client,
            )

    @pytest.mark.asyncio
    async def test_connect_error_maps_to_unavailable(self):
        def handler(request):
            raise httpx.ConnectError("no route to host")

        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(transport=transport)
        try:
            with pytest.raises(ProviderUnavailable):
                await litellm_proxy.complete(
                    [Message(role="user", content="hi")],
                    model="anthropic/claude-haiku-4.5",
                    client=client,
                )
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_list_content_flattened(self, mock_async_client):
        payload = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": "part1 "},
                            {"type": "text", "text": "part2"},
                        ],
                    },
                    "finish_reason": "stop",
                }
            ]
        }
        client = mock_async_client(payload=payload)
        resp = await litellm_proxy.complete(
            [Message(role="user", content="hi")],
            model="anthropic/claude-haiku-4.5",
            client=client,
        )
        assert resp.text == "part1 part2"


# ---------------------------------------------------------------------------
# Sync tests
# ---------------------------------------------------------------------------


class TestCompleteSync:
    def test_happy_path(self, mock_sync_client, mock_proxy_response):
        client = mock_sync_client(payload=mock_proxy_response(content="sure"))
        resp = litellm_proxy.complete_sync(
            [Message(role="user", content="hi")],
            model="anthropic/claude-haiku-4.5",
            client=client,
        )
        assert resp.text == "sure"

    def test_429(self, mock_sync_client):
        client = mock_sync_client(status_code=429, payload={})
        with pytest.raises(RateLimitError):
            litellm_proxy.complete_sync(
                [Message(role="user", content="hi")],
                model="anthropic/claude-haiku-4.5",
                client=client,
            )

    def test_json_mode_body(self, mock_sync_client):
        captured = {}

        def handler(request):
            captured["body"] = request.read()
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "{}"}, "finish_reason": "stop"}
                    ]
                },
            )

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        try:
            litellm_proxy.complete_sync(
                [Message(role="user", content="hi")],
                model="anthropic/claude-haiku-4.5",
                response_format="json_object",
                client=client,
            )
        finally:
            client.close()

        import json

        body = json.loads(captured["body"])
        assert body["response_format"] == {"type": "json_object"}

    def test_tools_body(self, mock_sync_client):
        captured = {}

        def handler(request):
            captured["body"] = request.read()
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "ok"}, "finish_reason": "stop"}
                    ]
                },
            )

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        tool = Tool(
            name="lookup",
            description="Look stuff up",
            parameters={"type": "object", "properties": {}},
        )
        try:
            litellm_proxy.complete_sync(
                [Message(role="user", content="hi")],
                model="anthropic/claude-haiku-4.5",
                tools=[tool],
                client=client,
            )
        finally:
            client.close()

        import json

        body = json.loads(captured["body"])
        assert body["tools"][0]["type"] == "function"
        assert body["tools"][0]["function"]["name"] == "lookup"
