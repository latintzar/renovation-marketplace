"""Tests for the public :func:`llm.chat` and :func:`llm.chat_sync` entry points."""

from __future__ import annotations

import pytest

from llm import chat, chat_sync
from llm.errors import ModelNotFound
from llm.providers.base import ChatResponse, Message


class TestNormalisation:
    def test_str_prompt_wrapped(self, monkeypatch, mock_sync_client):
        """A bare string prompt must be converted to a single user message."""
        client = mock_sync_client()
        captured: dict = {}

        from llm.providers import litellm_proxy as _proxy

        orig = _proxy.complete_sync

        def patched(messages, **kwargs):
            captured["messages"] = messages
            return orig(messages, client=client, **kwargs)

        monkeypatch.setattr(_proxy, "complete_sync", patched)

        chat_sync("hola", model="anthropic/claude-haiku-4.5")

        assert len(captured["messages"]) == 1
        assert captured["messages"][0].role == "user"
        assert captured["messages"][0].content == "hola"


class TestDispatch:
    def test_model_xor_tier(self):
        with pytest.raises(ModelNotFound):
            chat_sync(
                "hi",
                model="anthropic/claude-haiku-4.5",
                tier="smart",
            )

    def test_defaults_to_fast_tier(self, monkeypatch, mock_sync_client):
        client = mock_sync_client()
        called_model = {}

        from llm.providers import litellm_proxy as _proxy

        orig = _proxy.complete_sync

        def patched(messages, *, model, **kwargs):
            called_model["id"] = model
            return orig(messages, model=model, client=client, **kwargs)

        monkeypatch.setattr(_proxy, "complete_sync", patched)

        chat_sync("hi")
        assert called_model["id"] == "anthropic/claude-haiku-4.5"

    def test_tier_resolution(self, monkeypatch, mock_sync_client):
        client = mock_sync_client()
        called_model = {}

        from llm.providers import litellm_proxy as _proxy

        orig = _proxy.complete_sync

        def patched(messages, *, model, **kwargs):
            called_model["id"] = model
            return orig(messages, model=model, client=client, **kwargs)

        monkeypatch.setattr(_proxy, "complete_sync", patched)

        chat_sync("hi", tier="smart")
        assert called_model["id"] == "anthropic/claude-sonnet-4.6"

    def test_bedrock_provider_routed(self, monkeypatch, stub_bedrock_client):
        client = stub_bedrock_client()
        routed = {"provider": None}

        from llm.providers import bedrock as _bedrock

        orig = _bedrock.complete_sync

        def patched(messages, **kwargs):
            routed["provider"] = "bedrock"
            return orig(messages, client=client, **kwargs)

        monkeypatch.setattr(_bedrock, "complete_sync", patched)

        resp = chat_sync(
            "hi",
            model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        )
        assert routed["provider"] == "bedrock"
        assert resp.text == "Stub Bedrock reply."

    def test_messages_passthrough(self, monkeypatch, mock_sync_client):
        client = mock_sync_client()
        captured = {}

        from llm.providers import litellm_proxy as _proxy

        orig = _proxy.complete_sync

        def patched(messages, **kwargs):
            captured["messages"] = messages
            return orig(messages, client=client, **kwargs)

        monkeypatch.setattr(_proxy, "complete_sync", patched)

        chat_sync(
            [
                Message(role="system", content="You are Leo."),
                Message(role="user", content="hi"),
            ],
            model="anthropic/claude-haiku-4.5",
        )
        assert len(captured["messages"]) == 2
        assert captured["messages"][0].role == "system"


class TestUsageEmission:
    def test_chat_sync_records_usage(self, monkeypatch, mock_sync_client):
        client = mock_sync_client()

        from llm.providers import litellm_proxy as _proxy
        from llm import usage as _usage

        orig = _proxy.complete_sync

        def patched(messages, **kwargs):
            return orig(messages, client=client, **kwargs)

        monkeypatch.setattr(_proxy, "complete_sync", patched)

        events = []

        def obs(resp):
            events.append(resp)

        _usage.register_observer(obs)
        try:
            chat_sync("hi", model="anthropic/claude-haiku-4.5")
        finally:
            _usage.unregister_observer(obs)

        assert len(events) == 1
        assert events[0].usage is not None


class TestChatAsync:
    @pytest.mark.asyncio
    async def test_async_happy_path(self, monkeypatch, mock_async_client):
        client = mock_async_client()

        from llm.providers import litellm_proxy as _proxy

        orig = _proxy.complete

        async def patched(messages, **kwargs):
            return await orig(messages, client=client, **kwargs)

        monkeypatch.setattr(_proxy, "complete", patched)

        resp = await chat("hi", model="anthropic/claude-haiku-4.5")
        assert resp.text == "hello"

    @pytest.mark.asyncio
    async def test_fallback_chain_triggers(self, monkeypatch):
        from llm.errors import ProviderUnavailable
        from llm.providers import litellm_proxy as _proxy

        call_count = 0

        async def patched(messages, *, model, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ProviderUnavailable("down", model=model)
            return ChatResponse(text="rescued", model=model, usage=None)

        monkeypatch.setattr(_proxy, "complete", patched)

        resp = await chat(
            "hi",
            model="anthropic/claude-haiku-4.5",
            fallback=["anthropic/claude-sonnet-4.6"],
        )
        assert resp.used_fallback
        assert resp.text == "rescued"
