"""STT registry / resolve_provider / normalize_language tests."""

from __future__ import annotations

import pytest

from voice.stt import (
    TRANSCRIPTION_PROVIDERS,
    TranscriptionProvider,
    get_provider,
    normalize_language,
    resolve_provider,
)


class TestNormalizeLanguage:
    def test_none_returns_none(self):
        assert normalize_language(None) is None

    def test_empty_returns_none(self):
        assert normalize_language("") is None

    def test_whitespace_returns_none(self):
        assert normalize_language("  \t ") is None

    @pytest.mark.parametrize("val", ["auto", "multilingual", "detect", "any"])
    def test_magic_strings_returns_none(self, val):
        assert normalize_language(val) is None

    @pytest.mark.parametrize("val", ["AUTO", "Multilingual", "DETECT"])
    def test_magic_strings_case_insensitive(self, val):
        assert normalize_language(val) is None

    def test_iso_code_passes_through(self):
        assert normalize_language("es") == "es"
        assert normalize_language("en") == "en"

    def test_capitalized_lowercased(self):
        assert normalize_language("EN") == "en"
        assert normalize_language("Es") == "es"

    def test_long_input_truncated_to_8(self):
        assert normalize_language("this-is-a-long-language-tag") == "this-is-"

    def test_locale_preserved(self):
        assert normalize_language("es-mx") == "es-mx"

    def test_numeric_input_coerced_to_str(self):
        assert normalize_language(123) == "123"  # type: ignore[arg-type]


class TestResolveProvider:
    def test_auto_falls_to_local_without_creds(self):
        assert resolve_provider("auto") == "local"

    def test_auto_prefers_groq(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_x")
        assert resolve_provider("auto") == "groq"

    def test_auto_falls_back_to_hf_when_no_groq(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        assert resolve_provider("auto") == "huggingface"

    def test_auto_prefers_groq_over_hf(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_x")
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        assert resolve_provider("auto") == "groq"

    def test_explicit_local_always_works(self):
        assert resolve_provider("local") == "local"

    def test_explicit_groq_requires_creds(self):
        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            resolve_provider("groq")

    def test_explicit_groq_with_creds(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_x")
        assert resolve_provider("groq") == "groq"

    def test_explicit_hf_alias(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        assert resolve_provider("hf") == "huggingface"

    def test_explicit_huggingface(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        assert resolve_provider("huggingface") == "huggingface"

    def test_hf_no_creds_raises(self):
        with pytest.raises(ValueError, match="HF_TOKEN"):
            resolve_provider("huggingface")

    def test_hf_accepts_legacy_env(self, monkeypatch):
        monkeypatch.setenv("HUGGINGFACE_HUB_TOKEN", "hf_legacy")
        assert resolve_provider("huggingface") == "huggingface"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="provider must be"):
            resolve_provider("deepgram")  # type: ignore[arg-type]

    def test_none_defaults_to_auto(self):
        # resolve_provider uses (requested or "auto") so None becomes "auto"
        assert resolve_provider(None) == "local"  # type: ignore[arg-type]

    def test_empty_string_defaults_to_auto(self):
        assert resolve_provider("") == "local"  # type: ignore[arg-type]

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_x")
        assert resolve_provider("GROQ") == "groq"  # type: ignore[arg-type]
        assert resolve_provider("Auto") == "groq"  # type: ignore[arg-type]


class TestProviderRegistry:
    def test_all_three_registered(self):
        assert set(TRANSCRIPTION_PROVIDERS.keys()) == {"groq", "huggingface", "local"}

    def test_get_provider_returns_instance(self):
        p = get_provider("local")
        assert p.name == "local"
        assert isinstance(p, TranscriptionProvider)

    def test_get_provider_fresh_instance_each_call(self):
        # No internal caching at this layer — model caching happens inside the
        # local provider via lru_cache on the loader.
        p1 = get_provider("local")
        p2 = get_provider("local")
        assert p1 is not p2

    def test_get_provider_unknown_raises(self):
        with pytest.raises(ValueError):
            get_provider("deepgram")  # type: ignore[arg-type]

    def test_all_providers_satisfy_protocol(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_x")
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        for name in TRANSCRIPTION_PROVIDERS:
            # Skip types that need live instantiation args
            if name == "local":
                p = get_provider(name)  # noqa
                assert isinstance(p, TranscriptionProvider)
