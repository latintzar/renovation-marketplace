"""Shared fixtures for :mod:`llm` tests.

Key design choice: LiteLLM-proxy tests run against a mocked
``httpx.MockTransport`` so we never hit a real proxy. Bedrock tests
use a stub client with ``.converse`` — no boto3 dependency at test time.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
import pytest


@pytest.fixture
def mock_proxy_response():
    """Factory: returns a fake LiteLLM proxy ``/v1/chat/completions`` JSON dict.

    Default shape mirrors OpenAI's response format — ``choices[0].message.content``
    and a ``usage`` block.
    """

    def _make(
        content: str = "hello",
        finish_reason: str = "stop",
        input_tokens: int = 10,
        output_tokens: int = 5,
    ) -> Dict[str, Any]:
        return {
            "id": "cmpl-test",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": finish_reason,
                }
            ],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        }

    return _make


@pytest.fixture
def mock_async_client(mock_proxy_response):
    """A :class:`httpx.AsyncClient` that returns a canned proxy response."""

    def _make(
        *,
        status_code: int = 200,
        payload: Optional[Dict[str, Any]] = None,
        handler=None,
    ) -> httpx.AsyncClient:
        if handler is None:

            def handler(request):
                return httpx.Response(
                    status_code,
                    json=payload or mock_proxy_response(),
                )

        transport = httpx.MockTransport(handler)
        return httpx.AsyncClient(transport=transport)

    return _make


@pytest.fixture
def mock_sync_client(mock_proxy_response):
    """A :class:`httpx.Client` that returns a canned proxy response."""

    def _make(
        *,
        status_code: int = 200,
        payload: Optional[Dict[str, Any]] = None,
        handler=None,
    ) -> httpx.Client:
        if handler is None:

            def handler(request):
                return httpx.Response(
                    status_code,
                    json=payload or mock_proxy_response(),
                )

        transport = httpx.MockTransport(handler)
        return httpx.Client(transport=transport)

    return _make


@pytest.fixture
def stub_bedrock_client():
    """A stub Bedrock client with a ``.converse`` method."""

    class StubBedrockClient:
        def __init__(self):
            self.calls: list[Dict[str, Any]] = []
            self.next_response: Dict[str, Any] = {
                "output": {
                    "message": {
                        "role": "assistant",
                        "content": [{"text": "Stub Bedrock reply."}],
                    }
                },
                "usage": {"inputTokens": 12, "outputTokens": 3, "totalTokens": 15},
                "stopReason": "end_turn",
            }
            self.next_exc: Optional[Exception] = None

        def converse(self, **kwargs):
            self.calls.append(kwargs)
            if self.next_exc:
                raise self.next_exc
            return self.next_response

    return StubBedrockClient
