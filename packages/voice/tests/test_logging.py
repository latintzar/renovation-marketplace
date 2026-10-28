"""Logging-helper tests — confirm the PII gate works."""

from __future__ import annotations

import logging

import pytest

from voice import logging as voice_logging


@pytest.fixture
def capture_records():
    """Capture log records the voice package emits."""
    records: list[logging.LogRecord] = []

    class Handler(logging.Handler):
        def emit(self, record):
            records.append(record)

    h = Handler(level=logging.DEBUG)
    logger = logging.getLogger("voice.test")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(h)
    yield logger, records
    logger.removeHandler(h)


class TestTranscriptLogging:
    def test_metadata_always_info(self, capture_records):
        logger, records = capture_records
        voice_logging.log_transcript(
            logger,
            event="ASR done",
            provider="groq",
            lang="es",
            asr_seconds=1.23,
            raw="hola mundo",
        )
        metadata_record = records[0]
        assert metadata_record.levelno == logging.INFO
        assert "groq" in metadata_record.getMessage()
        assert "es" in metadata_record.getMessage()
        assert "1.23" in metadata_record.getMessage()
        assert "chars=10" in metadata_record.getMessage()

    def test_content_preview_is_debug_by_default(self, capture_records):
        logger, records = capture_records
        voice_logging.log_transcript(
            logger,
            event="ASR done",
            provider="local",
            lang="en",
            asr_seconds=2.5,
            raw="the quick brown fox",
        )
        # Records: [metadata @ INFO, content preview @ DEBUG]
        assert len(records) == 2
        content_record = records[1]
        assert content_record.levelno == logging.DEBUG
        assert "the quick brown fox" in content_record.getMessage()

    def test_content_preview_promotes_to_info_when_flag_on(self, capture_records, monkeypatch):
        monkeypatch.setenv("VOICE_LOG_CONTENT", "1")
        logger, records = capture_records
        voice_logging.log_transcript(
            logger,
            event="ASR done",
            provider="local",
            lang="en",
            asr_seconds=2.5,
            raw="pii-ish text",
        )
        content_record = records[1]
        assert content_record.levelno == logging.INFO
        assert "pii-ish text" in content_record.getMessage()

    def test_empty_raw_skips_content_record(self, capture_records):
        logger, records = capture_records
        voice_logging.log_transcript(
            logger,
            event="ASR done",
            provider="local",
            lang="",
            asr_seconds=0.5,
            raw="",
        )
        # Only metadata record
        assert len(records) == 1
        assert records[0].levelno == logging.INFO

    def test_preview_truncated_to_80_chars_by_default(self, capture_records):
        logger, records = capture_records
        long = "a" * 200
        voice_logging.log_transcript(
            logger,
            event="ASR done",
            provider="local",
            lang="en",
            asr_seconds=1,
            raw=long,
        )
        preview = records[1].getMessage()
        # The preview should contain exactly 80 a's, not 200.
        # msg is "ASR done preview | aaaaa..." — strip prefix and count a's.
        assert "a" * 80 in preview
        assert "a" * 81 not in preview

    def test_missing_lang_shows_question_mark(self, capture_records):
        logger, records = capture_records
        voice_logging.log_transcript(
            logger,
            event="ASR done",
            provider="huggingface",
            lang="",
            asr_seconds=1,
            raw="text",
        )
        assert "lang=?" in records[0].getMessage()


class TestPolishLogging:
    def test_metadata_info_content_debug(self, capture_records):
        logger, records = capture_records
        voice_logging.log_polish(
            logger,
            event="polish.anthropic ok",
            model_id="us.anthropic.claude-haiku-4-5",
            raw_chars=100,
            out_chars=120,
            input_tokens=50,
            output_tokens=60,
            out="polished content",
        )
        metadata = records[0]
        content = records[1]
        assert metadata.levelno == logging.INFO
        assert "us.anthropic" in metadata.getMessage()
        assert "in_tok=50" in metadata.getMessage()
        assert "out_tok=60" in metadata.getMessage()
        assert content.levelno == logging.DEBUG

    def test_polish_tokens_may_be_none(self, capture_records):
        logger, records = capture_records
        voice_logging.log_polish(
            logger,
            event="polish.converse ok",
            model_id="qwen",
            raw_chars=10,
            out_chars=10,
            input_tokens=None,
            output_tokens=None,
            out="text",
        )
        assert "in_tok=?" in records[0].getMessage()
        assert "out_tok=?" in records[0].getMessage()

    def test_polish_no_content_skipped_when_empty(self, capture_records):
        logger, records = capture_records
        voice_logging.log_polish(
            logger,
            event="polish empty",
            model_id="haiku",
            raw_chars=10,
            out_chars=0,
            out="",
        )
        assert len(records) == 1
