"""Verify the :mod:`llm` package's public API surface — 53 symbols."""

from __future__ import annotations

import llm


EXPECTED = {
    # chat
    "chat",
    "chat_sync",
    # structured
    "complete_structured",
    "complete_structured_sync",
    # vision
    "complete_vision",
    "complete_vision_sync",
    # stream
    "stream",
    # embed
    "embed",
    "embed_sync",
    # images
    "generate_image",
    "generate_image_async",
    # types
    "Message",
    "Tool",
    "ToolCall",
    "ChatResponse",
    "StreamChunk",
    "ResponseFormat",
    "Usage",
    # models
    "Model",
    "MODEL_REGISTRY",
    "INVALID_MODELS",
    "pick",
    "by_tier",
    "for_provider",
    "resolve_model",
    "DEFAULT_SMART",
    "DEFAULT_FAST",
    "DEFAULT_VISION",
    "DEFAULT_REASONING",
    "DEFAULT_LONG_CTX",
    "DEFAULT_CHEAP",
    "DEFAULT_IMAGE_GEN",
    # pricing
    "ModelPricing",
    "PRICING",
    "estimate_cost",
    # prompts
    "Prompt",
    "render_prompt",
    "get_prompt",
    # tokens
    "count_tokens",
    "count_message_tokens",
    # usage
    "record_usage",
    "register_observer",
    "unregister_observer",
    # errors
    "LLMError",
    "ProviderError",
    "ProviderUnavailable",
    "RateLimitError",
    "ContextWindowExceeded",
    "InvalidResponseShape",
    "ModelNotFound",
    "PromptNotFound",
    # config
    "LITELLM_BASE_URL",
    "LITELLM_API_KEY",
    "proxy_base_url",
    "proxy_api_key",
    # provider constants (from packages/domain Wave 2)
    "BEDROCK_REGION",
    "BEDROCK_CLAUDE_HAIKU",
    "BEDROCK_CLAUDE_SONNET",
}


class TestApiSurface:
    def test_expected_count(self):
        assert len(EXPECTED) == 58

    def test_all_matches_expected(self):
        assert set(llm.__all__) == EXPECTED

    def test_all_symbols_importable(self):
        for name in EXPECTED:
            assert hasattr(llm, name), f"missing symbol: {name}"

    def test_no_private_symbols_leaked(self):
        for name in llm.__all__:
            assert not name.startswith("_"), f"private symbol exported: {name}"

    def test_errors_all_subclass_llm_error(self):
        for name in (
            "ProviderError",
            "ProviderUnavailable",
            "RateLimitError",
            "ContextWindowExceeded",
            "InvalidResponseShape",
            "ModelNotFound",
            "PromptNotFound",
        ):
            err_cls = getattr(llm, name)
            assert issubclass(err_cls, llm.LLMError)

    def test_tier_defaults_are_registered_model_ids(self):
        for name in (
            "DEFAULT_SMART",
            "DEFAULT_FAST",
            "DEFAULT_VISION",
            "DEFAULT_REASONING",
            "DEFAULT_LONG_CTX",
            "DEFAULT_CHEAP",
            "DEFAULT_IMAGE_GEN",
        ):
            model_id = getattr(llm, name)
            assert model_id in llm.MODEL_REGISTRY, (
                f"{name}={model_id} not in MODEL_REGISTRY"
            )
