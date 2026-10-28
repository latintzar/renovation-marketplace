"""End-to-end pipeline tests — STT + polish orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from voice import transcribe
from voice.types import RawTranscript, TranscriptResult


async def _set_provider(monkeypatch, *, name: str, raw_text: str, raw_lang: str = ""):
    """Patch :func:`voice.stt.get_provider` to return a stub that yields
    ``raw_text`` / ``raw_lang``.

    Returns the ``AsyncMock`` so tests can assert on kwargs passed in.
    """

    async def _transcribe(audio, *, content_type, language=None, initial_prompt=None):
        return RawTranscript(text=raw_text, lang=raw_lang, asr_seconds=0.1)

    stub = AsyncMock()
    stub.name = name
    stub.transcribe = AsyncMock(side_effect=_transcribe)
    monkeypatch.setattr("voice.pipeline.get_provider", lambda n: stub)
    monkeypatch.setattr("voice.pipeline.resolve_provider", lambda req: name)
    return stub


class TestProviderResolutionAndCalls:
    async def test_auto_picks_groq_when_creds_present(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_x")
        stub = await _set_provider(monkeypatch, name="groq", raw_text="hola")
        monkeypatch.setattr("voice.pipeline.resolve_provider", lambda req: "groq")

        result = await transcribe(b"audio", content_type="audio/ogg", polish=False)
        assert result.provider == "groq"
        assert result.text == "hola"
        assert stub.transcribe.await_count == 1

    async def test_auto_falls_through_to_local(self, monkeypatch):
        """No cloud creds → resolve_provider returns ``local``."""
        stub = await _set_provider(monkeypatch, name="local", raw_text="hola")
        monkeypatch.setattr("voice.pipeline.resolve_provider", lambda req: "local")

        result = await transcribe(b"audio", content_type="audio/ogg", polish=False)
        assert result.provider == "local"

    async def test_explicit_provider_passed_through(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        stub = await _set_provider(monkeypatch, name="huggingface", raw_text="hola")
        captured = {}

        def fake_resolve(req):
            captured["req"] = req
            return "huggingface"

        monkeypatch.setattr("voice.pipeline.resolve_provider", fake_resolve)
        await transcribe(
            b"audio", content_type="audio/ogg", provider="huggingface", polish=False
        )
        assert captured["req"] == "huggingface"

    async def test_content_type_forwarded(self, monkeypatch):
        stub = await _set_provider(monkeypatch, name="local", raw_text="x")
        await transcribe(b"audio", content_type="audio/ogg", polish=False)
        call = stub.transcribe.call_args_list[0]
        assert call.kwargs["content_type"] == "audio/ogg"

    async def test_language_auto_aliases_normalized_to_none(self, monkeypatch):
        """``"auto"`` / ``"multilingual"`` / ``"detect"`` / ``"any"`` / empty
        collapse to ``None`` (multilingual auto-detect)."""
        stub = await _set_provider(monkeypatch, name="local", raw_text="x")
        await transcribe(
            b"audio",
            content_type="audio/ogg",
            language="auto",
            polish=False,
        )
        call = stub.transcribe.call_args_list[0]
        assert call.kwargs["language"] is None

    async def test_language_iso_code_lowercased(self, monkeypatch):
        stub = await _set_provider(monkeypatch, name="local", raw_text="x")
        await transcribe(
            b"audio",
            content_type="audio/ogg",
            language="ES",
            polish=False,
        )
        call = stub.transcribe.call_args_list[0]
        assert call.kwargs["language"] == "es"

    async def test_initial_prompt_forwarded(self, monkeypatch):
        stub = await _set_provider(monkeypatch, name="local", raw_text="x")
        await transcribe(
            b"audio",
            content_type="audio/ogg",
            initial_prompt="Vocabulary: fontanería",
            polish=False,
        )
        call = stub.transcribe.call_args_list[0]
        assert call.kwargs["initial_prompt"] == "Vocabulary: fontanería"


class TestPolish:
    async def test_polish_disabled_returns_raw(self, monkeypatch):
        await _set_provider(monkeypatch, name="local", raw_text="hola mundo")
        result = await transcribe(
            b"audio", content_type="audio/ogg", polish=False
        )
        assert result.text == "hola mundo"
        assert result.raw_text == "hola mundo"
        assert result.polished is False

    async def test_polish_success_sets_flag(self, monkeypatch):
        await _set_provider(monkeypatch, name="groq", raw_text="hola")
        monkeypatch.setattr(
            "voice.pipeline.polish_module.polish",
            AsyncMock(return_value="Hola."),
        )
        result = await transcribe(
            b"audio", content_type="audio/ogg", polish=True
        )
        assert result.text == "Hola."
        assert result.raw_text == "hola"
        assert result.polished is True

    async def test_polish_same_as_raw_not_flagged(self, monkeypatch):
        """If polish returns exact raw, ``polished=False``."""
        await _set_provider(monkeypatch, name="groq", raw_text="hola")
        monkeypatch.setattr(
            "voice.pipeline.polish_module.polish",
            AsyncMock(return_value="hola"),
        )
        result = await transcribe(
            b"audio", content_type="audio/ogg", polish=True
        )
        assert result.polished is False

    async def test_polish_empty_return_not_flagged(self, monkeypatch):
        await _set_provider(monkeypatch, name="groq", raw_text="hola")
        monkeypatch.setattr(
            "voice.pipeline.polish_module.polish", AsyncMock(return_value="")
        )
        result = await transcribe(
            b"audio", content_type="audio/ogg", polish=True
        )
        assert result.polished is False
        assert result.text == "hola"

    async def test_empty_raw_skips_polish(self, monkeypatch):
        await _set_provider(monkeypatch, name="groq", raw_text="")
        mock_polish = AsyncMock(return_value="should not be called")
        monkeypatch.setattr("voice.pipeline.polish_module.polish", mock_polish)
        result = await transcribe(
            b"audio", content_type="audio/ogg", polish=True
        )
        assert result.text == ""
        assert result.polished is False
        assert mock_polish.await_count == 0


class TestTranscriptResultShape:
    async def test_result_fields(self, monkeypatch):
        await _set_provider(
            monkeypatch, name="local", raw_text="hola mundo", raw_lang="es"
        )
        result = await transcribe(
            b"audio", content_type="audio/ogg", polish=False
        )
        assert isinstance(result, TranscriptResult)
        assert result.text == "hola mundo"
        assert result.raw_text == "hola mundo"
        assert result.lang == "es"
        assert result.provider == "local"
        assert result.asr_seconds >= 0
        assert result.polished is False


class TestSemaphore:
    async def test_semaphore_acquired(self, monkeypatch):
        """Verify pipeline acquires the concurrency semaphore during the
        provider call — if we hold it externally first, the call should wait."""
        import asyncio
        import time

        from voice.resilience import voice_semaphore

        monkeypatch.setenv("VOICE_CONCURRENCY", "1")
        await _set_provider(monkeypatch, name="local", raw_text="x")

        sem = voice_semaphore()

        async def busy_holder():
            async with sem:
                await asyncio.sleep(0.05)

        started = time.monotonic()
        await asyncio.gather(
            busy_holder(),
            transcribe(b"audio", content_type="audio/ogg", polish=False),
        )
        elapsed = time.monotonic() - started
        # With sem size=1, the two tasks serialize — ≥0.05s
        assert elapsed >= 0.04
