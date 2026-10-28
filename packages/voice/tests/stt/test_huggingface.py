"""HuggingFace provider tests — InferenceClient mocked."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from voice.stt.huggingface import HuggingFaceProvider


class TestCredentialsRequired:
    async def test_missing_token_raises(self):
        with pytest.raises(ValueError, match="HF_TOKEN"):
            await HuggingFaceProvider().transcribe(b"audio", content_type="audio/ogg")

    async def test_explicit_token_overrides_env(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "env_token")
        p = HuggingFaceProvider(token="explicit_token")
        assert p._resolve_token() == "explicit_token"


class TestSuccessfulInference:
    async def test_basic_call(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        mock_client = MagicMock()
        mock_client.automatic_speech_recognition.return_value = SimpleNamespace(text="hello world")
        monkeypatch.setattr(
            "huggingface_hub.InferenceClient",
            lambda **kwargs: mock_client,
        )
        result = await HuggingFaceProvider().transcribe(b"audio", content_type="audio/ogg")
        assert result.text == "hello world"
        assert result.lang == ""
        assert result.asr_seconds >= 0

    async def test_client_constructed_with_token(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        mock_client = MagicMock()
        mock_client.automatic_speech_recognition.return_value = SimpleNamespace(text="x")
        captured_kwargs: dict = {}

        def fake_ctor(**kwargs):
            captured_kwargs.update(kwargs)
            return mock_client

        monkeypatch.setattr("huggingface_hub.InferenceClient", fake_ctor)
        await HuggingFaceProvider().transcribe(b"audio", content_type="audio/ogg")
        assert captured_kwargs["token"] == "hf_x"

    async def test_text_stripped(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        mock_client = MagicMock()
        mock_client.automatic_speech_recognition.return_value = SimpleNamespace(text="   hello world   ")
        monkeypatch.setattr("huggingface_hub.InferenceClient", lambda **k: mock_client)
        result = await HuggingFaceProvider().transcribe(b"audio", content_type="audio/ogg")
        assert result.text == "hello world"

    async def test_missing_text_attr_returns_empty(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        mock_client = MagicMock()
        mock_client.automatic_speech_recognition.return_value = SimpleNamespace()
        monkeypatch.setattr("huggingface_hub.InferenceClient", lambda **k: mock_client)
        result = await HuggingFaceProvider().transcribe(b"audio", content_type="audio/ogg")
        assert result.text == ""


class TestLanguageThreading:
    """Wave-12 fix: today's ``shared/stt_providers.transcribe_hf_sync`` drops
    the language hint. The new provider threads it through when the HF client
    supports it."""

    async def test_language_passed_when_supported(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        mock_client = MagicMock()
        mock_client.automatic_speech_recognition.return_value = SimpleNamespace(text="hola")
        monkeypatch.setattr("huggingface_hub.InferenceClient", lambda **k: mock_client)

        await HuggingFaceProvider().transcribe(
            b"audio", content_type="audio/ogg", language="es"
        )
        # First call should include `language` kwarg.
        first_call = mock_client.automatic_speech_recognition.call_args_list[0]
        assert first_call.kwargs.get("language") == "es"

    async def test_retries_without_language_on_typeerror(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        mock_client = MagicMock()
        mock_client.automatic_speech_recognition.side_effect = [
            TypeError("unexpected keyword argument 'language'"),
            SimpleNamespace(text="hola"),
        ]
        monkeypatch.setattr("huggingface_hub.InferenceClient", lambda **k: mock_client)

        result = await HuggingFaceProvider().transcribe(
            b"audio", content_type="audio/ogg", language="es"
        )
        assert result.text == "hola"
        assert mock_client.automatic_speech_recognition.call_count == 2
        # Second call omits language
        second_call = mock_client.automatic_speech_recognition.call_args_list[1]
        assert "language" not in second_call.kwargs

    async def test_retries_without_language_on_lang_error_message(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        mock_client = MagicMock()
        mock_client.automatic_speech_recognition.side_effect = [
            Exception("Error: language hint not supported"),
            SimpleNamespace(text="hola"),
        ]
        monkeypatch.setattr("huggingface_hub.InferenceClient", lambda **k: mock_client)

        result = await HuggingFaceProvider().transcribe(
            b"audio", content_type="audio/ogg", language="es"
        )
        assert result.text == "hola"

    async def test_no_retry_when_language_hint_absent(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        mock_client = MagicMock()
        mock_client.automatic_speech_recognition.return_value = SimpleNamespace(text="hola")
        monkeypatch.setattr("huggingface_hub.InferenceClient", lambda **k: mock_client)

        await HuggingFaceProvider().transcribe(b"audio", content_type="audio/ogg")
        assert mock_client.automatic_speech_recognition.call_count == 1
        call = mock_client.automatic_speech_recognition.call_args_list[0]
        assert "language" not in call.kwargs

    async def test_unrelated_error_bubbles(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        mock_client = MagicMock()
        mock_client.automatic_speech_recognition.side_effect = RuntimeError("network down")
        monkeypatch.setattr("huggingface_hub.InferenceClient", lambda **k: mock_client)

        with pytest.raises(RuntimeError, match="network down"):
            await HuggingFaceProvider().transcribe(
                b"audio", content_type="audio/ogg", language="es"
            )


class TestInitialPromptIgnored:
    async def test_initial_prompt_is_ignored(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        mock_client = MagicMock()
        mock_client.automatic_speech_recognition.return_value = SimpleNamespace(text="x")
        monkeypatch.setattr("huggingface_hub.InferenceClient", lambda **k: mock_client)

        await HuggingFaceProvider().transcribe(
            b"audio",
            content_type="audio/ogg",
            initial_prompt="Vocabulary hint",
        )
        # initial_prompt should NOT be passed to the HF client
        call = mock_client.automatic_speech_recognition.call_args_list[0]
        assert "prompt" not in call.kwargs
        assert "initial_prompt" not in call.kwargs


class TestClientReuse:
    async def test_client_reused_across_calls(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        ctor_count = 0

        def fake_ctor(**kwargs):
            nonlocal ctor_count
            ctor_count += 1
            mock = MagicMock()
            mock.automatic_speech_recognition.return_value = SimpleNamespace(text="x")
            return mock

        monkeypatch.setattr("huggingface_hub.InferenceClient", fake_ctor)
        provider = HuggingFaceProvider()
        await provider.transcribe(b"audio", content_type="audio/ogg")
        await provider.transcribe(b"audio", content_type="audio/ogg")
        assert ctor_count == 1  # lazy-created once, reused


class TestName:
    def test_name_is_huggingface(self):
        assert HuggingFaceProvider.name == "huggingface"
