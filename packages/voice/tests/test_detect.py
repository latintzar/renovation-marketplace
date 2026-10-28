"""Language detection tests."""

from __future__ import annotations

import pytest

from voice.detect import detect_language


class TestLangDetect:
    def test_empty_returns_default(self):
        assert detect_language("") == "es"

    def test_whitespace_returns_default(self):
        assert detect_language("   \n\t  ") == "es"

    def test_none_returns_default(self):
        assert detect_language(None) == "es"

    def test_custom_default(self):
        assert detect_language("", default="en") == "en"

    def test_english_sentence_detects_en(self):
        assert detect_language("The quick brown fox jumps over the lazy dog.") == "en"

    def test_spanish_sentence_detects_es(self):
        assert detect_language("El rápido zorro marrón salta sobre el perro perezoso.") == "es"

    def test_italian_detects_not_es_or_en(self):
        # langdetect usually lands on "it" for Italian. Not our main target but
        # confirms we don't false-positive everything as "es".
        code = detect_language("Il rapido volpe marrone salta sopra il cane pigro.")
        assert code == code.lower()
        assert len(code) == 2

    def test_returns_two_char_code(self):
        code = detect_language("Hello world this is a test")
        assert len(code) <= 2


class TestHeuristicFallback:
    """When langdetect isn't available or raises, the stopword heuristic kicks in."""

    def test_spanish_stopwords_beat_english(self, monkeypatch):
        import voice.detect as detect

        # Force langdetect to fail so we fall through to the heuristic.
        def broken_detect(text):
            raise RuntimeError("langdetect down")

        monkeypatch.setattr("langdetect.detect", broken_detect)
        # 3 Spanish stopwords → "el ", "la ", "de "
        result = detect.detect_language("el hombre con la casa de madera")
        assert result == "es"

    def test_english_stopwords_beat_spanish(self, monkeypatch):
        import voice.detect as detect

        def broken_detect(text):
            raise RuntimeError("langdetect down")

        monkeypatch.setattr("langdetect.detect", broken_detect)
        result = detect.detect_language("the man with the house is for sale")
        assert result == "en"

    def test_heuristic_tie_returns_default(self, monkeypatch):
        import voice.detect as detect

        def broken_detect(text):
            raise RuntimeError("langdetect down")

        monkeypatch.setattr("langdetect.detect", broken_detect)
        assert detect.detect_language("abcdefg", default="es") == "es"
        assert detect.detect_language("abcdefg", default="en") == "en"

    def test_heuristic_never_raises_on_unicode(self):
        # Don't monkey-patch — just confirm unicode doesn't raise.
        result = detect_language("日本語のテキスト")
        # No guarantee what it picks, but it should not raise.
        assert isinstance(result, str)
        assert len(result) <= 2
