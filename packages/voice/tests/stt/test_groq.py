"""Groq provider tests — HTTP round-trip mocked via respx."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from voice.stt.groq import GroqProvider, _filename_for_audio
from voice.types import RawTranscript


_GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


class TestFilenameForAudio:
    def test_ogg(self):
        assert _filename_for_audio("audio/ogg") == "recording.ogg"

    def test_mp4(self):
        assert _filename_for_audio("audio/mp4") == "recording.m4a"

    def test_wav(self):
        assert _filename_for_audio("audio/wav") == "recording.wav"

    def test_unknown(self):
        assert _filename_for_audio("audio/flac") == "recording.webm"

    def test_empty(self):
        assert _filename_for_audio("") == "recording.webm"


class TestGroqProviderSuccess:
    async def test_missing_key_raises(self):
        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            await GroqProvider().transcribe(b"audio", content_type="audio/ogg")

    async def test_successful_call_returns_rawtranscript(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
        with respx.mock(base_url="https://api.groq.com") as mock:
            mock.post("/openai/v1/audio/transcriptions").respond(
                200,
                json={"text": "hola mundo", "language": "es"},
            )
            result = await GroqProvider().transcribe(b"audio bytes", content_type="audio/ogg")
        assert isinstance(result, RawTranscript)
        assert result.text == "hola mundo"
        assert result.lang == "es"
        assert result.asr_seconds >= 0

    async def test_explicit_constructor_api_key_wins(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "env_key")
        captured: list[httpx.Request] = []

        def respond(request):
            captured.append(request)
            return httpx.Response(200, json={"text": "ok"})

        with respx.mock(base_url="https://api.groq.com") as mock:
            mock.post("/openai/v1/audio/transcriptions").mock(side_effect=respond)
            await GroqProvider(api_key="explicit_key").transcribe(
                b"audio", content_type="audio/ogg"
            )
        auth = captured[0].headers["authorization"]
        assert auth == "Bearer explicit_key"

    async def test_model_in_form_field(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
        captured_data: list[bytes] = []

        def respond(request):
            captured_data.append(request.content)
            return httpx.Response(200, json={"text": "ok"})

        with respx.mock(base_url="https://api.groq.com") as mock:
            mock.post("/openai/v1/audio/transcriptions").mock(side_effect=respond)
            await GroqProvider(model_name="whisper-large-v3").transcribe(
                b"audio", content_type="audio/ogg"
            )
        body = captured_data[0].decode("utf-8", errors="ignore")
        assert "whisper-large-v3" in body

    async def test_language_hint_passed(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
        captured: list[httpx.Request] = []

        def respond(request):
            captured.append(request)
            return httpx.Response(200, json={"text": "x"})

        with respx.mock(base_url="https://api.groq.com") as mock:
            mock.post("/openai/v1/audio/transcriptions").mock(side_effect=respond)
            await GroqProvider().transcribe(b"audio", content_type="audio/ogg", language="es")
        body = captured[0].content.decode("utf-8", errors="ignore")
        assert 'name="language"' in body
        assert "es" in body

    async def test_initial_prompt_passed_as_prompt_field(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
        captured: list[httpx.Request] = []

        def respond(request):
            captured.append(request)
            return httpx.Response(200, json={"text": "x"})

        with respx.mock(base_url="https://api.groq.com") as mock:
            mock.post("/openai/v1/audio/transcriptions").mock(side_effect=respond)
            await GroqProvider().transcribe(
                b"audio",
                content_type="audio/ogg",
                initial_prompt="Vocabulary: fontanería, alicatado, pintura",
            )
        body = captured[0].content.decode("utf-8", errors="ignore")
        assert 'name="prompt"' in body
        assert "fontanería" in body

    async def test_non_string_language_in_response_ignored(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
        with respx.mock(base_url="https://api.groq.com") as mock:
            mock.post("/openai/v1/audio/transcriptions").respond(
                200, json={"text": "t", "language": None}
            )
            result = await GroqProvider().transcribe(b"audio", content_type="audio/ogg")
        assert result.lang == ""

    async def test_empty_text_field(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
        with respx.mock(base_url="https://api.groq.com") as mock:
            mock.post("/openai/v1/audio/transcriptions").respond(200, json={"text": ""})
            result = await GroqProvider().transcribe(b"audio", content_type="audio/ogg")
        assert result.text == ""

    async def test_whitespace_text_stripped(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
        with respx.mock(base_url="https://api.groq.com") as mock:
            mock.post("/openai/v1/audio/transcriptions").respond(
                200, json={"text": "  hola mundo  "}
            )
            result = await GroqProvider().transcribe(b"audio", content_type="audio/ogg")
        assert result.text == "hola mundo"


class TestGroqProviderErrors:
    async def test_404_raises(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
        with respx.mock(base_url="https://api.groq.com") as mock:
            mock.post("/openai/v1/audio/transcriptions").respond(404, text="not found")
            with pytest.raises(httpx.HTTPStatusError):
                await GroqProvider().transcribe(b"audio", content_type="audio/ogg")

    async def test_500_raises(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
        with respx.mock(base_url="https://api.groq.com") as mock:
            mock.post("/openai/v1/audio/transcriptions").respond(500, text="server error")
            with pytest.raises(httpx.HTTPStatusError):
                await GroqProvider().transcribe(b"audio", content_type="audio/ogg")

    async def test_429_raises(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
        with respx.mock(base_url="https://api.groq.com") as mock:
            mock.post("/openai/v1/audio/transcriptions").respond(429, text="rate limit")
            with pytest.raises(httpx.HTTPStatusError):
                await GroqProvider().transcribe(b"audio", content_type="audio/ogg")

    async def test_timeout_ignored_via_httpx(self, monkeypatch):
        """Construct sanity — the timeout is threaded through to httpx."""
        monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
        p = GroqProvider(timeout=5.0)
        assert p._timeout == 5.0


class TestName:
    def test_name_is_groq(self):
        assert GroqProvider.name == "groq"
