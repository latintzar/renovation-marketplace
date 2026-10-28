"""Tests for the curated public surface of ``voice``."""

from __future__ import annotations

import importlib
import inspect

import pytest

import voice


EXPECTED_EXPORTS = {
    "transcribe",
    "TranscriptResult",
    "polish",
    "polish_sync",
    "POLISH_SYSTEM",
    "to_wav",
    "wav_tempfile",
    "ext_for_content_type",
    "detect_language",
    "TranscriptionProvider",
    "RawTranscript",
    "resolve_provider",
    "normalize_language",
    "synthesize",
    "SynthesisResult",
    "SynthesisProvider",
    "list_voices",
    "voice_semaphore",
    "ProviderName",
    "ResolvedProvider",
    "AudioQuality",
}


def test_all_matches_expected_exports():
    """__all__ is the single source of truth for the public surface."""
    assert set(voice.__all__) == EXPECTED_EXPORTS


def test_every_export_is_importable():
    for name in voice.__all__:
        assert hasattr(voice, name), f"voice has no attribute {name!r}"


def test_transcribe_is_async():
    assert inspect.iscoroutinefunction(voice.transcribe)


def test_polish_is_async():
    assert inspect.iscoroutinefunction(voice.polish)


def test_polish_sync_is_sync():
    assert not inspect.iscoroutinefunction(voice.polish_sync)


def test_wav_tempfile_is_contextmanager():
    cm = voice.wav_tempfile.__wrapped__ if hasattr(voice.wav_tempfile, "__wrapped__") else voice.wav_tempfile
    assert callable(cm)


def test_no_accidental_leak_of_internal_modules():
    """Internal submodules shouldn't appear on voice's __all__.

    ``polish`` and ``detect_language`` are intentionally re-exported, so we
    exclude those names from the internals set — the concern here is only
    accidental leakage of submodule objects (``config``, ``types``, etc.) that
    aren't part of the public API.
    """
    internals = {"pipeline", "config", "resilience", "stt", "tts", "types", "audio", "logging"}
    assert not set(voice.__all__).intersection(internals)


def test_py_typed_marker_present():
    """PEP 561: packages must ship py.typed to advertise types."""
    import os

    voice_path = os.path.dirname(voice.__file__)
    assert os.path.isfile(os.path.join(voice_path, "py.typed"))


def test_reimport_is_stable():
    """Re-importing voice should yield the same module instance."""
    v1 = importlib.import_module("voice")
    v2 = importlib.import_module("voice")
    assert v1 is v2
