"""Tests for :mod:`llm.providers.fallback`."""

from __future__ import annotations

import pytest

from llm.errors import (
    ContextWindowExceeded,
    InvalidResponseShape,
    ModelNotFound,
    ProviderUnavailable,
    RateLimitError,
)
from llm.providers.base import ChatResponse
from llm.providers.fallback import resolve_chain, run_with_fallback


class TestResolveChain:
    def test_named_balanced(self):
        chain = resolve_chain("chat.balanced")
        assert len(chain) == 3

    def test_named_reasoning(self):
        chain = resolve_chain("chat.reasoning")
        assert len(chain) == 2

    def test_named_vision(self):
        chain = resolve_chain("vision.primary")
        assert len(chain) >= 2

    def test_unknown_named_raises(self):
        with pytest.raises(ModelNotFound):
            resolve_chain("chat.totally-fake")

    def test_list_passthrough(self):
        chain = resolve_chain(
            [
                "anthropic/claude-haiku-4.5",
                "anthropic/claude-sonnet-4.6",
            ]
        )
        assert chain == [
            "anthropic/claude-haiku-4.5",
            "anthropic/claude-sonnet-4.6",
        ]

    def test_list_invalid_raises(self):
        with pytest.raises(ModelNotFound):
            resolve_chain(["bogus-model-id"])

    def test_list_alias_normalised(self):
        chain = resolve_chain(["claude-haiku"])
        assert chain == ["anthropic/claude-haiku-4.5"]


class TestRunWithFallback:
    @pytest.mark.asyncio
    async def test_primary_succeeds(self):
        calls = []

        async def invoke(model_id: str) -> ChatResponse:
            calls.append(model_id)
            return ChatResponse(text="ok", model=model_id)

        resp = await run_with_fallback(
            "anthropic/claude-haiku-4.5",
            ["anthropic/claude-sonnet-4.6"],
            invoke=invoke,
        )
        assert resp.text == "ok"
        assert not resp.used_fallback
        assert resp.attempt_count == 1
        assert calls == ["anthropic/claude-haiku-4.5"]

    @pytest.mark.asyncio
    async def test_fallback_on_unavailable(self):
        call_count = 0

        async def invoke(model_id: str) -> ChatResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ProviderUnavailable("down", model=model_id)
            return ChatResponse(text="rescued", model=model_id)

        resp = await run_with_fallback(
            "anthropic/claude-haiku-4.5",
            ["anthropic/claude-sonnet-4.6"],
            invoke=invoke,
        )
        assert resp.text == "rescued"
        assert resp.used_fallback
        assert resp.fallback_reason == "ProviderUnavailable"
        assert resp.attempt_count == 2

    @pytest.mark.asyncio
    async def test_fallback_on_rate_limit(self):
        call_count = 0

        async def invoke(model_id: str) -> ChatResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("429", model=model_id)
            return ChatResponse(text="ok", model=model_id)

        resp = await run_with_fallback(
            "anthropic/claude-haiku-4.5",
            ["anthropic/claude-sonnet-4.6"],
            invoke=invoke,
        )
        assert resp.text == "ok"
        assert resp.fallback_reason == "RateLimitError"

    @pytest.mark.asyncio
    async def test_invalid_shape_does_not_trigger_fallback(self):
        async def invoke(model_id: str) -> ChatResponse:
            raise InvalidResponseShape("bad response", model=model_id)

        with pytest.raises(InvalidResponseShape):
            await run_with_fallback(
                "anthropic/claude-haiku-4.5",
                ["anthropic/claude-sonnet-4.6"],
                invoke=invoke,
            )

    @pytest.mark.asyncio
    async def test_model_not_found_does_not_trigger_fallback(self):
        async def invoke(model_id: str) -> ChatResponse:
            raise ModelNotFound("caller bug", model=model_id)

        with pytest.raises(ModelNotFound):
            await run_with_fallback(
                "anthropic/claude-haiku-4.5",
                ["anthropic/claude-sonnet-4.6"],
                invoke=invoke,
            )

    @pytest.mark.asyncio
    async def test_all_exhausted_raises_last(self):
        async def invoke(model_id: str) -> ChatResponse:
            raise ProviderUnavailable("down", model=model_id)

        with pytest.raises(ProviderUnavailable):
            await run_with_fallback(
                "anthropic/claude-haiku-4.5",
                ["anthropic/claude-sonnet-4.6"],
                invoke=invoke,
            )

    @pytest.mark.asyncio
    async def test_context_exceeded_only_advances_to_larger(self):
        call_count = 0

        async def invoke(model_id: str) -> ChatResponse:
            nonlocal call_count
            call_count += 1
            # haiku-4.5 → 200k ctx; gemini-3.1-pro-preview → 2M ctx
            if call_count == 1:
                raise ContextWindowExceeded("too big", model=model_id)
            return ChatResponse(text="fit", model=model_id)

        resp = await run_with_fallback(
            "anthropic/claude-haiku-4.5",
            ["gemini-3.1-pro-preview"],
            invoke=invoke,
        )
        assert resp.text == "fit"

    @pytest.mark.asyncio
    async def test_context_exceeded_reraises_if_no_larger(self):
        async def invoke(model_id: str) -> ChatResponse:
            raise ContextWindowExceeded("too big", model=model_id)

        # gemini-3.1-pro-preview has 2M ctx; haiku-4.5 has 200k — falling back
        # from gemini to haiku would be pointless.
        with pytest.raises(ContextWindowExceeded):
            await run_with_fallback(
                "gemini-3.1-pro-preview",
                ["anthropic/claude-haiku-4.5"],
                invoke=invoke,
            )
