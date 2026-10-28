"""TTS dispatcher + stub tests (Phase 3.5b: API shape locked, raises NIE)."""

from __future__ import annotations

import pytest

from voice import list_voices, synthesize
from voice.tts.elevenlabs import ElevenLabsProvider
from voice.tts.polly import PollyProvider
from voice.tts.voices import VOICE_REGISTRY, VoiceMapping


class TestSynthesizeStub:
    async def test_raises_notimplemented(self):
        with pytest.raises(NotImplementedError, match="Phase"):
            await synthesize("hola", voice_id="leo-es")

    async def test_raises_notimplemented_en(self):
        with pytest.raises(NotImplementedError):
            await synthesize("hello", voice_id="leo-en")

    async def test_default_voice_id(self):
        with pytest.raises(NotImplementedError):
            await synthesize("hola")


class TestProviderStubs:
    async def test_polly_raises(self):
        with pytest.raises(NotImplementedError):
            await PollyProvider().synthesize("hola", voice_id="leo-es")

    async def test_polly_name(self):
        assert PollyProvider.name == "polly"

    async def test_elevenlabs_raises(self):
        with pytest.raises(NotImplementedError):
            await ElevenLabsProvider().synthesize("hola", voice_id="leo-es")

    async def test_elevenlabs_name(self):
        assert ElevenLabsProvider.name == "elevenlabs"


class TestVoiceRegistry:
    def test_leo_es_present(self):
        assert "leo-es" in VOICE_REGISTRY
        mapping = VOICE_REGISTRY["leo-es"]
        assert isinstance(mapping, VoiceMapping)
        assert mapping.language == "es"
        assert mapping.polly_voice_id == "Lupe"
        assert mapping.polly_engine == "neural"
        assert mapping.elevenlabs_voice_id is None

    def test_leo_en_present(self):
        assert "leo-en" in VOICE_REGISTRY
        mapping = VOICE_REGISTRY["leo-en"]
        assert mapping.language == "en"
        assert mapping.polly_voice_id == "Joanna"
        assert mapping.polly_engine == "neural"


class TestListVoices:
    def test_all_returns_all(self):
        voices = list_voices()
        canonicals = {v["canonical"] for v in voices}
        assert canonicals == set(VOICE_REGISTRY.keys())

    def test_filter_by_language(self):
        voices = list_voices(language="es")
        assert len(voices) == 1
        assert voices[0]["canonical"] == "leo-es"
        assert voices[0]["language"] == "es"

    def test_filter_english(self):
        voices = list_voices(language="en")
        assert len(voices) == 1
        assert voices[0]["canonical"] == "leo-en"

    def test_filter_unknown_language(self):
        voices = list_voices(language="zz")
        assert voices == []

    def test_shape_includes_polly_and_elevenlabs(self):
        voices = list_voices(language="es")
        v = voices[0]
        assert "polly_voice_id" in v
        assert "polly_engine" in v
        assert "elevenlabs_voice_id" in v
        assert "description" in v
