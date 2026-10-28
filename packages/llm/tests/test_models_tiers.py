"""Tests for :mod:`llm.models.tiers`."""

from __future__ import annotations

import importlib

import pytest

from llm.errors import ModelNotFound


class TestPick:
    def test_smart(self):
        from llm.models.tiers import pick

        assert pick("smart") == "anthropic/claude-sonnet-4.6"

    def test_fast(self):
        from llm.models.tiers import pick

        assert pick("fast") == "anthropic/claude-haiku-4.5"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv(
            "LEO_LLM_DEFAULT_FAST", "anthropic/claude-haiku-4.5"
        )
        import llm.models.tiers as tiers

        importlib.reload(tiers)
        try:
            assert tiers.pick("fast") == "anthropic/claude-haiku-4.5"
        finally:
            monkeypatch.delenv("LEO_LLM_DEFAULT_FAST", raising=False)
            importlib.reload(tiers)

    def test_env_override_invalid_raises(self, monkeypatch):
        monkeypatch.setenv("LEO_LLM_DEFAULT_FAST", "bogus-model")
        import llm.models.tiers as tiers

        # Reload triggers module-level evaluation of pick() for each tier.
        with pytest.raises(ModelNotFound):
            importlib.reload(tiers)
        monkeypatch.delenv("LEO_LLM_DEFAULT_FAST", raising=False)
        importlib.reload(tiers)


class TestModuleDefaults:
    def test_all_defaults_set(self):
        from llm.models.tiers import (
            DEFAULT_CHEAP,
            DEFAULT_FAST,
            DEFAULT_IMAGE_GEN,
            DEFAULT_LONG_CTX,
            DEFAULT_REASONING,
            DEFAULT_SMART,
            DEFAULT_VISION,
        )

        assert isinstance(DEFAULT_SMART, str)
        assert isinstance(DEFAULT_FAST, str)
        assert isinstance(DEFAULT_VISION, str)
        assert isinstance(DEFAULT_REASONING, str)
        assert isinstance(DEFAULT_LONG_CTX, str)
        assert isinstance(DEFAULT_CHEAP, str)
        assert isinstance(DEFAULT_IMAGE_GEN, str)

    def test_defaults_match_pick(self):
        from llm.models.tiers import DEFAULT_FAST, DEFAULT_SMART, pick

        assert DEFAULT_FAST == pick("fast")
        assert DEFAULT_SMART == pick("smart")
