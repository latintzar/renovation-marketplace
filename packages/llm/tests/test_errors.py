"""Tests for :mod:`llm.errors`."""

from __future__ import annotations

import pytest

from llm.errors import (
    ContextWindowExceeded,
    InvalidResponseShape,
    LLMError,
    ModelNotFound,
    ProviderError,
    ProviderUnavailable,
    PromptNotFound,
    RateLimitError,
)


class TestHierarchy:
    def test_base_is_exception(self):
        assert issubclass(LLMError, Exception)

    def test_provider_error_extends_llm_error(self):
        assert issubclass(ProviderError, LLMError)

    def test_provider_unavailable_extends_provider_error(self):
        assert issubclass(ProviderUnavailable, ProviderError)

    def test_rate_limit_extends_provider_error(self):
        assert issubclass(RateLimitError, ProviderError)

    def test_context_window_extends_provider_error(self):
        assert issubclass(ContextWindowExceeded, ProviderError)

    def test_invalid_response_extends_llm_error_not_provider(self):
        assert issubclass(InvalidResponseShape, LLMError)
        assert not issubclass(InvalidResponseShape, ProviderError)

    def test_model_not_found_extends_llm_error_not_provider(self):
        assert issubclass(ModelNotFound, LLMError)
        assert not issubclass(ModelNotFound, ProviderError)

    def test_prompt_not_found_extends_llm_error(self):
        assert issubclass(PromptNotFound, LLMError)


class TestConstruction:
    def test_minimal_construct(self):
        e = LLMError("boom")
        assert str(e) == "boom"
        assert e.provider is None
        assert e.model is None
        assert e.raw is None

    def test_full_construct(self):
        cause = ValueError("underlying")
        e = ProviderUnavailable(
            "connect refused",
            provider="bedrock",
            model="test-model",
            raw=cause,
        )
        assert e.provider == "bedrock"
        assert e.model == "test-model"
        assert e.raw is cause

    def test_repr_includes_provider_and_model(self):
        e = RateLimitError(
            "throttled", provider="litellm_proxy", model="fake"
        )
        r = repr(e)
        assert "RateLimitError" in r
        assert "'throttled'" in r
        assert "litellm_proxy" in r
        assert "fake" in r


class TestRaiseAndCatch:
    def test_catch_by_base(self):
        with pytest.raises(LLMError):
            raise ProviderUnavailable("x")

    def test_catch_by_provider_base(self):
        with pytest.raises(ProviderError):
            raise RateLimitError("x")

    def test_invalid_response_not_caught_by_provider_error(self):
        with pytest.raises(LLMError) as exc_info:
            raise InvalidResponseShape("x")
        assert not isinstance(exc_info.value, ProviderError)
