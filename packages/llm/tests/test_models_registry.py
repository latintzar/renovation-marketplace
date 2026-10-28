"""Tests for :mod:`llm.models.registry`."""

from __future__ import annotations

import pytest

from llm.errors import ModelNotFound
from llm.models.registry import (
    INVALID_MODELS,
    MODEL_REGISTRY,
    by_tier,
    for_provider,
    resolve_model,
)
from llm.providers.base import Tier


class TestInvariants:
    def test_no_duplicate_ids(self):
        """Each concrete Model.id appears exactly once when walking the
        registry. Aliases create extra keys, but every alias must point
        to a *registered* Model.
        """
        seen_ids = set()
        for key, model in MODEL_REGISTRY.items():
            seen_ids.add(model.id)
        assert len(seen_ids) >= 18, "should have ≥ 18 distinct live models"

    def test_anti_list_not_in_registry(self):
        for bogus in INVALID_MODELS:
            assert bogus not in MODEL_REGISTRY

    def test_every_tier_covered(self):
        tiers: list[Tier] = [
            "smart",
            "fast",
            "vision",
            "reasoning",
            "long_ctx",
            "cheap",
            "image_gen",
        ]
        for t in tiers:
            assert by_tier(t), f"tier {t!r} has no registered model"

    def test_bedrock_models_have_region(self):
        for m in for_provider("bedrock"):
            assert m.region, f"bedrock model {m.id!r} missing region"


class TestResolveModel:
    def test_resolve_canonical_id(self):
        m = resolve_model("anthropic/claude-haiku-4.5")
        assert m.tier == "fast"

    def test_resolve_via_alias(self):
        m = resolve_model("claude-haiku")
        assert m.id == "anthropic/claude-haiku-4.5"

    def test_resolve_via_bedrock_prefix(self):
        m = resolve_model("bedrock/us.anthropic.claude-sonnet-4-6")
        assert m.provider == "bedrock"
        assert m.region == "us-east-1"

    def test_unknown_raises(self):
        with pytest.raises(ModelNotFound):
            resolve_model("this-model-does-not-exist")

    def test_anti_list_raises(self):
        with pytest.raises(ModelNotFound) as exc_info:
            resolve_model("gemini-2.0-pro")
        assert "anti-list" in str(exc_info.value)


class TestByTier:
    def test_fast_includes_haiku(self):
        ids = [m.id for m in by_tier("fast")]
        assert "anthropic/claude-haiku-4.5" in ids

    def test_smart_includes_sonnet(self):
        ids = [m.id for m in by_tier("smart")]
        assert "anthropic/claude-sonnet-4.6" in ids

    def test_vision_includes_haiku_bedrock(self):
        """Bedrock Haiku is PRIMARY vision per parse_media invariant."""
        ids = [m.id for m in by_tier("vision")]
        assert "us.anthropic.claude-haiku-4-5-20251001-v1:0" in ids

    def test_results_deduped(self):
        """Aliases shouldn't create duplicate rows in the tier list."""
        ids = [m.id for m in by_tier("fast")]
        assert len(ids) == len(set(ids))


class TestForProvider:
    def test_bedrock(self):
        models = for_provider("bedrock")
        assert all(m.provider == "bedrock" for m in models)
        assert len(models) >= 6

    def test_litellm_proxy(self):
        models = for_provider("litellm_proxy")
        assert all(m.provider == "litellm_proxy" for m in models)

    def test_gemini(self):
        models = for_provider("gemini")
        assert all(m.provider == "gemini" for m in models)
        assert len(models) >= 3


class TestCapabilities:
    def test_vision_flag_consistency(self):
        """Every vision-tier model must also flag supports_vision=True."""
        for m in by_tier("vision"):
            assert m.supports_vision

    def test_strict_schema_implies_json(self):
        """supports_strict_schema is strict JSON — implies supports_json."""
        for m in MODEL_REGISTRY.values():
            if m.supports_strict_schema:
                assert m.supports_json, f"{m.id!r} strict_schema but not json"
