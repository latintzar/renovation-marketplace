"""Tests for :mod:`llm.models.pricing`."""

from __future__ import annotations

import pytest

from llm.models.pricing import PRICING, ModelPricing, estimate_cost
from llm.models.registry import MODEL_REGISTRY
from llm.providers.base import Usage


class TestPricingTable:
    def test_every_live_model_has_pricing(self):
        """Pricing table must cover every concrete id in the registry."""
        live_ids = {m.id for m in MODEL_REGISTRY.values()}
        for model_id in live_ids:
            assert model_id in PRICING, f"missing pricing for {model_id!r}"

    def test_pricing_values_positive(self):
        for model_id, p in PRICING.items():
            assert p.input_per_1k_usd >= 0
            assert p.output_per_1k_usd >= 0

    def test_pricing_as_of_set(self):
        for p in PRICING.values():
            assert p.as_of, "every pricing row needs an as_of date"


class TestEstimateCost:
    def test_known_model(self):
        u = Usage(
            input_tokens=1000,
            output_tokens=1000,
            total_tokens=2000,
            model="anthropic/claude-haiku-4.5",
        )
        # haiku-4.5: 0.0008 in / 0.004 out per 1k → 0.0048
        cost = estimate_cost(u, model="anthropic/claude-haiku-4.5")
        assert cost == pytest.approx(0.0048)

    def test_unknown_model_returns_zero(self):
        u = Usage(input_tokens=100, output_tokens=100, total_tokens=200, model="x")
        assert estimate_cost(u, model="nonexistent-model") == 0.0

    def test_zero_tokens(self):
        u = Usage(0, 0, 0, "x")
        assert estimate_cost(u, model="anthropic/claude-haiku-4.5") == 0.0

    def test_embedding_has_zero_output(self):
        """Embeddings have output_per_1k_usd=0; estimate uses input only."""
        u = Usage(
            input_tokens=10000,
            output_tokens=0,
            total_tokens=10000,
            model="openai/text-embedding-3-small",
        )
        cost = estimate_cost(u, model="openai/text-embedding-3-small")
        assert cost == pytest.approx(0.0002)  # 0.00002 * 10


class TestModelPricing:
    def test_frozen(self):
        p = ModelPricing(0.001, 0.002, as_of="2026-01-15")
        with pytest.raises(Exception):
            p.input_per_1k_usd = 0.999

    def test_default_currency(self):
        p = ModelPricing(0.001, 0.002)
        assert p.currency == "USD"
