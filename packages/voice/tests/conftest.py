"""Shared fixtures for the voice test suite.

Principles:
- **Env isolation.** Every test starts with voice env vars cleared, so no test
  depends on the host's ``GROQ_API_KEY``/``HF_TOKEN`` state. Individual tests
  monkey-patch ``voice.config.*`` directly (the thin-function convention in
  ``voice.config`` is here precisely for this).
- **Semaphore reset.** ``voice.resilience.reset_semaphore_for_tests()`` runs
  between every test so concurrency isn't bleed across event loops.
- **Stub-chat fixture.** ``fake_chat`` patches
  ``voice.polish.chat_sync`` (the symbol re-imported from ``llm``) to return
  a ``MagicMock``; callers program ``mock.return_value = ChatResponse(...)``
  or ``mock.side_effect = Exception(...)`` per test.
- **Stub-faster-whisper fixture.** ``fake_whisper_model`` patches the cached
  loader to return a ``MagicMock`` model so ``LocalWhisperProvider`` tests
  don't hit the 600 MB download.
- **respx** mocks the Groq HTTP endpoint.
"""

from __future__ import annotations

import io
import os
import wave
from typing import Iterator
from unittest.mock import MagicMock

import pytest

# Environment variables the voice package reads. We clear all of them at test
# start to guarantee reproducibility.
_VOICE_ENV_VARS = [
    "GROQ_API_KEY",
    "GROQ_WHISPER_MODEL",
    "HF_TOKEN",
    "HUGGINGFACE_HUB_TOKEN",
    "HF_WHISPER_MODEL",
    "WHISPER_MODEL",
    "WHISPER_DEVICE",
    "WHISPER_COMPUTE_TYPE",
    "WHISPER_CPU_THREADS",
    "WHISPER_BEAM_SIZE",
    "VOICE_CONCURRENCY",
    "TRANSCRIPT_POLISH_ENABLED",
    "TRANSCRIPT_POLISH_MODEL",
    "POLISH_API_STYLE",
    "VOICE_LOG_CONTENT",
    "AWS_REGION",
    "ELEVENLABS_API_KEY",
]


@pytest.fixture(autouse=True)
def _voice_env_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear every voice-related env var before each test."""
    for name in _VOICE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _reset_semaphore() -> Iterator[None]:
    """Drop the module-level asyncio.Semaphore before each test so it rebinds
    to the test's event loop."""
    from voice import resilience

    resilience.reset_semaphore_for_tests()
    yield
    resilience.reset_semaphore_for_tests()


@pytest.fixture
def fake_chat(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Patch :func:`voice.polish.chat_sync` to return a MagicMock.

    ``voice.polish`` calls :func:`llm.chat_sync` to run the polish prompt.
    Tests program ``mock.return_value = ChatResponse(text="...", ...)`` or
    ``mock.side_effect = RuntimeError(...)`` to exercise behaviour without
    touching Bedrock.

    Note: ``voice.polish`` (attribute) is the *function* because ``__init__``
    re-exports it. Reach the actual module through ``sys.modules`` and patch
    there.
    """
    import sys

    import voice  # noqa: F401 — side-effect: submodule registered

    polish_module = sys.modules["voice.polish"]
    mock = MagicMock(name="chat_sync")
    monkeypatch.setattr(polish_module, "chat_sync", mock)
    return mock


@pytest.fixture
def fake_whisper_model(monkeypatch: pytest.MonkeyPatch):
    """Factory to patch the cached faster-whisper loader.

    Call ``fake_whisper_model(segments=[...], info=SimpleNamespace(language="en"))``
    to install a stub model whose ``transcribe`` returns ``(segments, info)``.

    Returns ``(model_mock, reset_cache)`` where ``reset_cache`` clears the
    ``@lru_cache`` on the real loader so subsequent tests don't see cached
    instances from prior runs.
    """
    from types import SimpleNamespace

    def _factory(
        *,
        segments=None,
        info=None,
    ):
        model = MagicMock(name="whisper_model")
        segs = list(segments or [])
        _info = info if info is not None else SimpleNamespace(language="")

        def _fake_transcribe(*a, **k):
            return (list(segs), _info)

        model.transcribe.side_effect = _fake_transcribe
        monkeypatch.setattr(
            "voice.stt.local._load_whisper_model", lambda *a, **k: model
        )

        def _reset() -> None:
            from voice.stt.local import _load_whisper_model as real

            # _load_whisper_model is our monkeypatched lambda now, but clear the
            # original cache for safety in case other tests reset the patch.
            if hasattr(real, "cache_clear"):
                real.cache_clear()

        return model, _reset

    return _factory


@pytest.fixture
def sample_wav_bytes() -> bytes:
    """A minimal valid WAV payload (1 second of silence at 16 kHz mono).

    Used by tests that need real audio bytes to pass into ``to_wav`` without
    requiring ffmpeg to know how to decode a fake codec. ffmpeg can re-encode
    this to WAV successfully.
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 16000)
    return buf.getvalue()


@pytest.fixture
def ffmpeg_available() -> bool:
    """Skip-marker fixture: returns True if ``ffmpeg`` is on PATH.

    Tests needing real ffmpeg use ``pytest.skipif(not ffmpeg_available, ...)``.
    """
    import shutil

    return shutil.which("ffmpeg") is not None
