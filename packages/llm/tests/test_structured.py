"""Tests for :mod:`llm.structured`."""

from __future__ import annotations

import httpx
import pytest
from pydantic import BaseModel

from llm.errors import InvalidResponseShape
from llm.structured import complete_structured, complete_structured_sync


class Person(BaseModel):
    name: str
    age: int


class TestStructuredSync:
    def test_happy_path(self, monkeypatch):
        from llm.providers import litellm_proxy as _proxy

        def fake_complete_sync(messages, **kwargs):
            from llm.providers.base import ChatResponse

            return ChatResponse(
                text='{"name": "Peter", "age": 40}',
                model=kwargs.get("model", ""),
            )

        monkeypatch.setattr(_proxy, "complete_sync", fake_complete_sync)

        result = complete_structured_sync(
            "Extract",
            schema=Person,
            model="anthropic/claude-haiku-4.5",
        )
        assert isinstance(result, Person)
        assert result.name == "Peter"
        assert result.age == 40

    def test_invalid_json_raises(self, monkeypatch):
        from llm.providers import litellm_proxy as _proxy

        def fake_complete_sync(messages, **kwargs):
            from llm.providers.base import ChatResponse

            return ChatResponse(text="not json", model=kwargs.get("model", ""))

        monkeypatch.setattr(_proxy, "complete_sync", fake_complete_sync)

        with pytest.raises(InvalidResponseShape):
            complete_structured_sync(
                "Extract",
                schema=Person,
                model="anthropic/claude-haiku-4.5",
            )

    def test_validation_error_raises(self, monkeypatch):
        from llm.providers import litellm_proxy as _proxy

        def fake_complete_sync(messages, **kwargs):
            from llm.providers.base import ChatResponse

            return ChatResponse(
                text='{"name": "Peter"}', model=kwargs.get("model", "")
            )

        monkeypatch.setattr(_proxy, "complete_sync", fake_complete_sync)

        with pytest.raises(InvalidResponseShape):
            complete_structured_sync(
                "Extract",
                schema=Person,
                model="anthropic/claude-haiku-4.5",
            )


class TestStructuredAsync:
    @pytest.mark.asyncio
    async def test_happy_path(self, monkeypatch):
        from llm.providers import litellm_proxy as _proxy

        async def fake_complete(messages, **kwargs):
            from llm.providers.base import ChatResponse

            return ChatResponse(
                text='{"name": "Peter", "age": 40}',
                model=kwargs.get("model", ""),
            )

        monkeypatch.setattr(_proxy, "complete", fake_complete)

        result = await complete_structured(
            "Extract",
            schema=Person,
            model="anthropic/claude-haiku-4.5",
        )
        assert isinstance(result, Person)
        assert result.name == "Peter"


class TestStrictSchemaSupport:
    def test_strict_schema_model_uses_json_schema_mode(self, monkeypatch):
        """Gemini supports strict schema — response_format should be 'json_schema'."""
        from llm.providers import litellm_proxy as _proxy

        captured = {}

        def fake_complete_sync(messages, **kwargs):
            captured["response_format"] = kwargs.get("response_format")
            captured["response_schema"] = kwargs.get("response_schema")
            from llm.providers.base import ChatResponse

            return ChatResponse(
                text='{"name": "Peter", "age": 40}',
                model=kwargs.get("model", ""),
            )

        monkeypatch.setattr(_proxy, "complete_sync", fake_complete_sync)

        complete_structured_sync(
            "Extract",
            schema=Person,
            model="gemini-3.1-pro-preview",
        )
        assert captured["response_format"] == "json_schema"
        assert captured["response_schema"] is not None

    def test_non_strict_model_uses_json_object_mode(self, monkeypatch):
        from llm.providers import litellm_proxy as _proxy

        captured = {}

        def fake_complete_sync(messages, **kwargs):
            captured["response_format"] = kwargs.get("response_format")
            from llm.providers.base import ChatResponse

            return ChatResponse(
                text='{"name": "Peter", "age": 40}',
                model=kwargs.get("model", ""),
            )

        monkeypatch.setattr(_proxy, "complete_sync", fake_complete_sync)

        complete_structured_sync(
            "Extract",
            schema=Person,
            model="anthropic/claude-haiku-4.5",
        )
        assert captured["response_format"] == "json_object"
