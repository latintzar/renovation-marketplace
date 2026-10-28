"""Audio normalization (ffmpeg) helper tests.

Most tests gate on ffmpeg availability — CI hosts and dev laptops have it, but
sandboxed environments may not. We skip those tests when ffmpeg is absent
rather than fail.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from voice.audio import ext_for_content_type, to_wav, wav_tempfile


class TestExtForContentType:
    def test_ogg(self):
        assert ext_for_content_type("audio/ogg") == "ogg"

    def test_ogg_with_codecs(self):
        assert ext_for_content_type("audio/ogg; codecs=opus") == "ogg"

    def test_mp4(self):
        assert ext_for_content_type("audio/mp4") == "m4a"

    def test_m4a(self):
        assert ext_for_content_type("audio/m4a") == "m4a"

    def test_wav(self):
        assert ext_for_content_type("audio/wav") == "wav"

    def test_webm(self):
        assert ext_for_content_type("audio/webm") == "webm"

    def test_unknown_falls_back_to_webm(self):
        assert ext_for_content_type("audio/flac") == "webm"

    def test_empty_falls_back_to_webm(self):
        assert ext_for_content_type("") == "webm"

    def test_none_falls_back_to_webm(self):
        assert ext_for_content_type(None) == "webm"  # type: ignore[arg-type]

    def test_case_insensitive(self):
        assert ext_for_content_type("Audio/OGG") == "ogg"
        assert ext_for_content_type("AUDIO/WAV") == "wav"


class TestToWav:
    def test_missing_ffmpeg_raises_filenotfound(self, monkeypatch, sample_wav_bytes):
        import voice.audio as audio

        def broken_run(*args, **kwargs):
            raise FileNotFoundError("ffmpeg not found")

        monkeypatch.setattr("voice.audio.subprocess.run", broken_run)
        with pytest.raises(FileNotFoundError):
            to_wav(sample_wav_bytes, content_type="audio/wav")

    def test_ffmpeg_nonzero_raises_runtimeerror(self, monkeypatch, sample_wav_bytes):
        class FakeResult:
            returncode = 1
            stderr = "Invalid data found when processing input"

        def fake_run(*args, **kwargs):
            return FakeResult()

        monkeypatch.setattr("voice.audio.subprocess.run", fake_run)
        with pytest.raises(RuntimeError, match="ffmpeg failed"):
            to_wav(sample_wav_bytes, content_type="audio/wav")

    def test_success_returns_path_and_writes_wav(self, monkeypatch, sample_wav_bytes, tmp_path):
        # Monkey-patch ffmpeg to just copy src → dst so we can verify the call
        # without invoking the real binary.
        import voice.audio as audio

        class FakeResult:
            returncode = 0
            stderr = ""

        captured: dict = {}

        def fake_run(argv, capture_output, text, timeout):  # noqa: ARG001
            captured["argv"] = argv
            # Find -i <src> and the output path (last arg).
            src = argv[argv.index("-i") + 1]
            dst = argv[-1]
            Path(dst).write_bytes(Path(src).read_bytes())
            return FakeResult()

        monkeypatch.setattr("voice.audio.subprocess.run", fake_run)

        result = to_wav(sample_wav_bytes, content_type="audio/wav")

        assert result.exists()
        assert result.suffix == ".wav"
        assert "-ar" in captured["argv"]
        assert "16000" in captured["argv"]
        assert "-ac" in captured["argv"]
        assert "1" in captured["argv"]
        result.unlink(missing_ok=True)

    def test_custom_sample_rate_and_channels(self, monkeypatch, sample_wav_bytes):
        class FakeResult:
            returncode = 0
            stderr = ""

        captured: dict = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            Path(argv[-1]).write_bytes(b"fake")
            return FakeResult()

        monkeypatch.setattr("voice.audio.subprocess.run", fake_run)

        result = to_wav(sample_wav_bytes, content_type="audio/webm", sample_rate=8000, channels=2)
        assert "8000" in captured["argv"]
        assert "2" in captured["argv"]
        result.unlink(missing_ok=True)

    def test_timeout_propagates_to_ffmpeg_call(self, monkeypatch, sample_wav_bytes):
        class FakeResult:
            returncode = 0
            stderr = ""

        captured: dict = {}

        def fake_run(argv, capture_output, text, timeout):  # noqa: ARG001
            captured["timeout"] = timeout
            Path(argv[-1]).write_bytes(b"fake")
            return FakeResult()

        monkeypatch.setattr("voice.audio.subprocess.run", fake_run)

        result = to_wav(sample_wav_bytes, content_type="audio/webm", timeout=120)
        assert captured["timeout"] == 120
        result.unlink(missing_ok=True)


class TestWavTempfile:
    def test_cleans_up_on_normal_exit(self, monkeypatch, sample_wav_bytes):
        class FakeResult:
            returncode = 0
            stderr = ""

        wav_paths: list[Path] = []

        def fake_run(argv, **kwargs):
            wav_paths.append(Path(argv[-1]))
            Path(argv[-1]).write_bytes(b"fake")
            return FakeResult()

        monkeypatch.setattr("voice.audio.subprocess.run", fake_run)

        with wav_tempfile(sample_wav_bytes, content_type="audio/wav") as wav_path:
            assert wav_path.exists()
            captured = wav_path

        assert not captured.exists()

    def test_cleans_up_on_exception(self, monkeypatch, sample_wav_bytes):
        class FakeResult:
            returncode = 0
            stderr = ""

        def fake_run(argv, **kwargs):
            Path(argv[-1]).write_bytes(b"fake")
            return FakeResult()

        monkeypatch.setattr("voice.audio.subprocess.run", fake_run)

        captured: list[Path] = []

        with pytest.raises(RuntimeError):
            with wav_tempfile(sample_wav_bytes, content_type="audio/wav") as wav_path:
                captured.append(wav_path)
                raise RuntimeError("body raised")

        assert len(captured) == 1
        assert not captured[0].exists()

    def test_cleans_up_src_tempfile_too(self, monkeypatch, sample_wav_bytes):
        class FakeResult:
            returncode = 0
            stderr = ""

        def fake_run(argv, **kwargs):
            Path(argv[-1]).write_bytes(b"fake")
            return FakeResult()

        monkeypatch.setattr("voice.audio.subprocess.run", fake_run)

        seen_src_paths: list[Path] = []

        with wav_tempfile(sample_wav_bytes, content_type="audio/ogg") as wav_path:
            src_path = wav_path.with_suffix(".ogg")
            seen_src_paths.append(src_path)

        # Both wav and src should be gone
        assert not wav_path.exists()
        assert not seen_src_paths[0].exists()

    def test_ffmpeg_failure_cleans_src(self, monkeypatch, sample_wav_bytes):
        class FakeResult:
            returncode = 1
            stderr = "bad"

        src_paths: list[Path] = []

        original_write = None

        def fake_run(argv, **kwargs):
            src = Path(argv[argv.index("-i") + 1])
            src_paths.append(src)
            assert src.exists(), "src should exist before ffmpeg runs"
            return FakeResult()

        monkeypatch.setattr("voice.audio.subprocess.run", fake_run)

        with pytest.raises(RuntimeError):
            to_wav(sample_wav_bytes, content_type="audio/ogg")

        # Source should be cleaned up even on ffmpeg failure
        assert len(src_paths) == 1
        assert not src_paths[0].exists()
