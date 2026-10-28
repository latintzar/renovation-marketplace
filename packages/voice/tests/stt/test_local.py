"""Local faster-whisper provider tests — model loader mocked.

Tests bypass ffmpeg by monkeypatching ``voice.stt.local.wav_tempfile`` to yield
an arbitrary path. We care about the model call here, not the ffmpeg dispatch.
"""

from __future__ import annotations

import contextlib
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from voice.stt.local import LocalWhisperProvider


class _Segment:
    """Minimal faster-whisper segment shape: ``.text`` attribute only."""

    def __init__(self, text: str) -> None:
        self.text = text


@pytest.fixture
def stub_wav_tempfile(monkeypatch):
    """Replace :func:`voice.stt.local.wav_tempfile` with a stub that yields a
    temp path without invoking ffmpeg. Tracks how many times it was entered.
    """
    stats = {"enter_count": 0}

    @contextlib.contextmanager
    def _stub(audio, *, content_type, **kwargs):
        stats["enter_count"] += 1
        fd, path = tempfile.mkstemp(suffix=".wav")
        import os

        os.close(fd)
        try:
            yield Path(path)
        finally:
            with contextlib.suppress(Exception):
                os.unlink(path)

    monkeypatch.setattr("voice.stt.local.wav_tempfile", _stub)
    return stats


class TestLocalWhisperTranscribe:
    async def test_successful_transcription(
        self, monkeypatch, fake_whisper_model, stub_wav_tempfile
    ):
        monkeypatch.setenv("WHISPER_MODEL", "base")
        model, _reset = fake_whisper_model(
            segments=[_Segment("hello"), _Segment(" world")],
            info=SimpleNamespace(language="en"),
        )
        result = await LocalWhisperProvider().transcribe(
            b"fake-audio-bytes", content_type="audio/wav"
        )
        assert result.text == "hello world"
        assert result.lang == "en"
        assert result.asr_seconds >= 0
        assert model.transcribe.call_count == 1

    async def test_language_hint_passed_to_faster_whisper(
        self, monkeypatch, fake_whisper_model, stub_wav_tempfile
    ):
        monkeypatch.setenv("WHISPER_MODEL", "base")
        model, _reset = fake_whisper_model(
            segments=[_Segment("hola")],
            info=SimpleNamespace(language="es"),
        )
        await LocalWhisperProvider().transcribe(
            b"audio", content_type="audio/wav", language="es"
        )
        call = model.transcribe.call_args_list[0]
        assert call.kwargs.get("language") == "es"

    async def test_no_language_hint_leaves_language_none(
        self, monkeypatch, fake_whisper_model, stub_wav_tempfile
    ):
        monkeypatch.setenv("WHISPER_MODEL", "base")
        model, _reset = fake_whisper_model(
            segments=[_Segment("x")],
            info=SimpleNamespace(language="es"),
        )
        await LocalWhisperProvider().transcribe(b"audio", content_type="audio/wav")
        call = model.transcribe.call_args_list[0]
        # Pipeline lets faster-whisper auto-detect when no hint.
        assert call.kwargs.get("language") is None

    async def test_language_fallback_to_empty_string(
        self, monkeypatch, fake_whisper_model, stub_wav_tempfile
    ):
        monkeypatch.setenv("WHISPER_MODEL", "base")
        fake_whisper_model(
            segments=[_Segment("x")],
            info=SimpleNamespace(language=None),
        )
        result = await LocalWhisperProvider().transcribe(b"audio", content_type="audio/wav")
        assert result.lang == ""

    async def test_info_without_language_attr(
        self, monkeypatch, fake_whisper_model, stub_wav_tempfile
    ):
        monkeypatch.setenv("WHISPER_MODEL", "base")
        fake_whisper_model(
            segments=[_Segment("x")],
            info=SimpleNamespace(),
        )
        result = await LocalWhisperProvider().transcribe(b"audio", content_type="audio/wav")
        assert result.lang == ""

    async def test_segments_concatenated(
        self, monkeypatch, fake_whisper_model, stub_wav_tempfile
    ):
        monkeypatch.setenv("WHISPER_MODEL", "base")
        fake_whisper_model(
            segments=[_Segment("one "), _Segment("two "), _Segment("three")],
            info=SimpleNamespace(language="en"),
        )
        result = await LocalWhisperProvider().transcribe(b"audio", content_type="audio/wav")
        assert result.text == "one two three"

    async def test_result_stripped(
        self, monkeypatch, fake_whisper_model, stub_wav_tempfile
    ):
        monkeypatch.setenv("WHISPER_MODEL", "base")
        fake_whisper_model(
            segments=[_Segment("  hello  ")],
            info=SimpleNamespace(language="en"),
        )
        result = await LocalWhisperProvider().transcribe(b"audio", content_type="audio/wav")
        assert result.text == "hello"

    async def test_empty_segments(
        self, monkeypatch, fake_whisper_model, stub_wav_tempfile
    ):
        monkeypatch.setenv("WHISPER_MODEL", "base")
        fake_whisper_model(
            segments=[],
            info=SimpleNamespace(language=""),
        )
        result = await LocalWhisperProvider().transcribe(b"audio", content_type="audio/wav")
        assert result.text == ""

    async def test_initial_prompt_forwarded(
        self, monkeypatch, fake_whisper_model, stub_wav_tempfile
    ):
        monkeypatch.setenv("WHISPER_MODEL", "base")
        model, _reset = fake_whisper_model(
            segments=[_Segment("x")],
            info=SimpleNamespace(language="en"),
        )
        await LocalWhisperProvider().transcribe(
            b"audio",
            content_type="audio/wav",
            initial_prompt="Vocabulary hint",
        )
        call = model.transcribe.call_args_list[0]
        assert call.kwargs.get("initial_prompt") == "Vocabulary hint"

    async def test_distil_model_disables_condition_on_previous(
        self, monkeypatch, fake_whisper_model, stub_wav_tempfile
    ):
        monkeypatch.setenv("WHISPER_MODEL", "distil-large-v3")
        model, _reset = fake_whisper_model(
            segments=[_Segment("x")],
            info=SimpleNamespace(language="en"),
        )
        await LocalWhisperProvider().transcribe(b"audio", content_type="audio/wav")
        call = model.transcribe.call_args_list[0]
        assert call.kwargs.get("condition_on_previous_text") is False

    async def test_non_distil_model_no_condition_flag(
        self, monkeypatch, fake_whisper_model, stub_wav_tempfile
    ):
        monkeypatch.setenv("WHISPER_MODEL", "base")
        model, _reset = fake_whisper_model(
            segments=[_Segment("x")],
            info=SimpleNamespace(language="en"),
        )
        await LocalWhisperProvider().transcribe(b"audio", content_type="audio/wav")
        call = model.transcribe.call_args_list[0]
        assert "condition_on_previous_text" not in call.kwargs


class TestFfmpegDispatch:
    async def test_transcribe_goes_through_wav_tempfile(
        self, monkeypatch, fake_whisper_model, stub_wav_tempfile
    ):
        """Local provider must go through ``voice.audio.wav_tempfile``, the
        single audio dispatch point per the design."""
        fake_whisper_model(
            segments=[_Segment("x")],
            info=SimpleNamespace(language="en"),
        )
        await LocalWhisperProvider().transcribe(b"audio", content_type="audio/ogg")
        assert stub_wav_tempfile["enter_count"] == 1


class TestModelCache:
    async def test_model_reused_across_calls(
        self, monkeypatch, fake_whisper_model, stub_wav_tempfile
    ):
        monkeypatch.setenv("WHISPER_MODEL", "base")
        model, _reset = fake_whisper_model(
            segments=[_Segment("x")],
            info=SimpleNamespace(language="en"),
        )
        p = LocalWhisperProvider()
        await p.transcribe(b"a", content_type="audio/wav")
        await p.transcribe(b"b", content_type="audio/wav")
        # Same mock instance served both calls.
        assert model.transcribe.call_count == 2


class TestName:
    def test_name_is_local(self):
        assert LocalWhisperProvider.name == "local"
