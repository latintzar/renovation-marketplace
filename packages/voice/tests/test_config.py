"""Config-reader tests — each env var has one reader, so one test each."""

from __future__ import annotations

import pytest

from voice import config


class TestGroq:
    def test_groq_api_key_default_empty(self):
        assert config.groq_api_key() == ""

    def test_groq_api_key_strips_whitespace(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "  gsk_foo  ")
        assert config.groq_api_key() == "gsk_foo"

    def test_groq_whisper_model_default(self):
        assert config.groq_whisper_model() == "whisper-large-v3-turbo"

    def test_groq_whisper_model_override(self, monkeypatch):
        monkeypatch.setenv("GROQ_WHISPER_MODEL", "whisper-large-v3")
        assert config.groq_whisper_model() == "whisper-large-v3"


class TestHF:
    def test_hf_token_prefers_hf_token(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_primary")
        monkeypatch.setenv("HUGGINGFACE_HUB_TOKEN", "hf_legacy")
        assert config.hf_token() == "hf_primary"

    def test_hf_token_falls_back_to_legacy(self, monkeypatch):
        monkeypatch.setenv("HUGGINGFACE_HUB_TOKEN", "hf_legacy")
        assert config.hf_token() == "hf_legacy"

    def test_hf_token_empty(self):
        assert config.hf_token() == ""

    def test_hf_whisper_model_default(self):
        assert config.hf_whisper_model() == "openai/whisper-large-v3"


class TestWhisper:
    def test_whisper_model_default(self):
        assert config.whisper_model_name() == "distil-large-v3"

    def test_whisper_device_default_cpu(self):
        assert config.whisper_device() == "cpu"

    def test_whisper_device_cuda(self, monkeypatch):
        monkeypatch.setenv("WHISPER_DEVICE", "cuda")
        assert config.whisper_device() == "cuda"

    def test_whisper_compute_type_default_int8_on_cpu(self):
        assert config.whisper_compute_type() == "int8"

    def test_whisper_compute_type_default_float16_on_cuda(self, monkeypatch):
        monkeypatch.setenv("WHISPER_DEVICE", "cuda")
        assert config.whisper_compute_type() == "float16"

    def test_whisper_compute_type_explicit_override(self, monkeypatch):
        monkeypatch.setenv("WHISPER_COMPUTE_TYPE", "int16")
        assert config.whisper_compute_type() == "int16"

    def test_whisper_cpu_threads_default(self):
        assert config.whisper_cpu_threads() == 0

    def test_whisper_cpu_threads_parsed(self, monkeypatch):
        monkeypatch.setenv("WHISPER_CPU_THREADS", "4")
        assert config.whisper_cpu_threads() == 4

    def test_whisper_cpu_threads_invalid_defaults_zero(self, monkeypatch):
        monkeypatch.setenv("WHISPER_CPU_THREADS", "not-an-int")
        assert config.whisper_cpu_threads() == 0

    def test_whisper_beam_size_default(self):
        assert config.whisper_beam_size() == 5

    def test_whisper_beam_size_clamped_low(self, monkeypatch):
        monkeypatch.setenv("WHISPER_BEAM_SIZE", "0")
        assert config.whisper_beam_size() == 1

    def test_whisper_beam_size_clamped_high(self, monkeypatch):
        monkeypatch.setenv("WHISPER_BEAM_SIZE", "99")
        assert config.whisper_beam_size() == 10

    def test_whisper_beam_size_invalid_defaults(self, monkeypatch):
        monkeypatch.setenv("WHISPER_BEAM_SIZE", "not-an-int")
        assert config.whisper_beam_size() == 5


class TestConcurrency:
    def test_voice_concurrency_default(self):
        assert config.voice_concurrency() == 8

    def test_voice_concurrency_override(self, monkeypatch):
        monkeypatch.setenv("VOICE_CONCURRENCY", "16")
        assert config.voice_concurrency() == 16

    def test_voice_concurrency_min_one(self, monkeypatch):
        monkeypatch.setenv("VOICE_CONCURRENCY", "0")
        assert config.voice_concurrency() == 1

    def test_voice_concurrency_invalid(self, monkeypatch):
        monkeypatch.setenv("VOICE_CONCURRENCY", "not-an-int")
        assert config.voice_concurrency() == 8


class TestPolish:
    def test_polish_enabled_default_true(self):
        assert config.polish_enabled() is True

    @pytest.mark.parametrize("val,expected", [
        ("1", True), ("true", True), ("yes", True), ("on", True),
        ("0", False), ("false", False), ("no", False), ("off", False),
        ("TRUE", True), ("False", False),
    ])
    def test_polish_enabled_flag_values(self, monkeypatch, val, expected):
        monkeypatch.setenv("TRANSCRIPT_POLISH_ENABLED", val)
        assert config.polish_enabled() is expected

    def test_polish_model_default(self):
        assert config.polish_model_id() == "us.anthropic.claude-haiku-4-5-20251001-v1:0"

    def test_polish_api_style_default_empty(self):
        assert config.polish_api_style() == ""

    @pytest.mark.parametrize("val,expected", [
        ("anthropic", "anthropic"),
        ("converse", "converse"),
        ("CONVERSE", "converse"),
        ("  anthropic  ", "anthropic"),
    ])
    def test_polish_api_style_normalized(self, monkeypatch, val, expected):
        monkeypatch.setenv("POLISH_API_STYLE", val)
        assert config.polish_api_style() == expected


class TestPII:
    def test_voice_log_content_default_false(self):
        """PII-safe default — transcript preview is DEBUG-level."""
        assert config.voice_log_content() is False

    @pytest.mark.parametrize("val", ["1", "true", "yes", "on", "TRUE"])
    def test_voice_log_content_true(self, monkeypatch, val):
        monkeypatch.setenv("VOICE_LOG_CONTENT", val)
        assert config.voice_log_content() is True


class TestAWS:
    def test_aws_region_default(self):
        assert config.aws_region() == "us-east-1"

    def test_aws_region_override(self, monkeypatch):
        monkeypatch.setenv("AWS_REGION", "eu-west-1")
        assert config.aws_region() == "eu-west-1"


class TestElevenLabs:
    def test_elevenlabs_key_empty_default(self):
        assert config.elevenlabs_api_key() == ""

    def test_elevenlabs_key_override(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "el_foo")
        assert config.elevenlabs_api_key() == "el_foo"
