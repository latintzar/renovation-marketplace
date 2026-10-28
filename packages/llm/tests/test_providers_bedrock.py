"""Tests for :mod:`llm.providers.bedrock` using a stub client."""

from __future__ import annotations

import pytest

from llm.errors import (
    InvalidResponseShape,
    ProviderError,
    ProviderUnavailable,
    RateLimitError,
)
from llm.providers import bedrock
from llm.providers.base import Message


class StubBotoError(Exception):
    """Mimics ``botocore.exceptions.ClientError`` — carries a ``.response``."""

    def __init__(self, code: str, message: str = "boom"):
        super().__init__(message)
        self.response = {"Error": {"Code": code, "Message": message}}


class TestCompleteSync:
    def test_happy_path(self, stub_bedrock_client):
        client = stub_bedrock_client()
        resp = bedrock.complete_sync(
            [Message(role="user", content="hello")],
            model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            client=client,
        )
        assert resp.text == "Stub Bedrock reply."
        assert resp.usage is not None
        assert resp.usage.total_tokens == 15

    def test_system_message_passed_as_system_block(self, stub_bedrock_client):
        client = stub_bedrock_client()
        bedrock.complete_sync(
            [
                Message(role="system", content="You are Leo."),
                Message(role="user", content="hi"),
            ],
            model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            client=client,
        )
        call = client.calls[0]
        assert call["system"] == [{"text": "You are Leo."}]
        assert all(m["role"] != "system" for m in call["messages"])

    def test_non_bedrock_model_raises(self, stub_bedrock_client):
        with pytest.raises(ProviderError):
            bedrock.complete_sync(
                [Message(role="user", content="hi")],
                model="anthropic/claude-haiku-4.5",  # proxy model
                client=stub_bedrock_client(),
            )

    def test_throttle_maps_to_rate_limit(self, stub_bedrock_client):
        client = stub_bedrock_client()
        client.next_exc = StubBotoError("ThrottlingException")
        with pytest.raises(RateLimitError):
            bedrock.complete_sync(
                [Message(role="user", content="hi")],
                model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
                client=client,
            )

    def test_5xx_maps_to_unavailable(self, stub_bedrock_client):
        client = stub_bedrock_client()
        client.next_exc = StubBotoError("ServiceUnavailableException")
        with pytest.raises(ProviderUnavailable):
            bedrock.complete_sync(
                [Message(role="user", content="hi")],
                model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
                client=client,
            )

    def test_other_errors_map_to_provider_error(self, stub_bedrock_client):
        client = stub_bedrock_client()
        client.next_exc = StubBotoError("AccessDeniedException")
        with pytest.raises(ProviderError):
            bedrock.complete_sync(
                [Message(role="user", content="hi")],
                model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
                client=client,
            )

    def test_missing_output_raises_invalid_shape(self, stub_bedrock_client):
        client = stub_bedrock_client()
        client.next_response = {"usage": {}}
        with pytest.raises(InvalidResponseShape):
            bedrock.complete_sync(
                [Message(role="user", content="hi")],
                model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
                client=client,
            )

    def test_temperature_propagated(self, stub_bedrock_client):
        client = stub_bedrock_client()
        bedrock.complete_sync(
            [Message(role="user", content="hi")],
            model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            temperature=0.7,
            max_tokens=100,
            client=client,
        )
        call = client.calls[0]
        assert call["inferenceConfig"]["temperature"] == 0.7
        assert call["inferenceConfig"]["maxTokens"] == 100


class TestCompleteAsync:
    @pytest.mark.asyncio
    async def test_async_wraps_sync(self, stub_bedrock_client):
        client = stub_bedrock_client()
        resp = await bedrock.complete(
            [Message(role="user", content="hi")],
            model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            client=client,
        )
        assert resp.text == "Stub Bedrock reply."
