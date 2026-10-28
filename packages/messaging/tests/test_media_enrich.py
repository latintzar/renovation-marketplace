"""Media enrichment — Hermes gateway routing + in-line text labelling."""

from __future__ import annotations

import pytest

from messaging import LeoMessage, MediaAttachment, enrich_message


@pytest.fixture
def stub_parse(monkeypatch):
    async def _fake(fpath, mime, caption=""):  # noqa: ARG001
        return f"[parsed {mime}]"

    monkeypatch.setattr("messaging.media.enrich.parse_media", _fake)


@pytest.fixture
def stub_transcribe(monkeypatch):
    async def _fake_tf(fpath):  # noqa: ARG001
        return "voice transcript"

    # Patch the module-level alias used by _enrich_audio
    monkeypatch.setattr("messaging.media.enrich.transcribe_file", _fake_tf)


class TestEnrichEmpty:
    @pytest.mark.asyncio
    async def test_no_media_unchanged(self) -> None:
        msg = LeoMessage(role="user", text="hello")
        out = await enrich_message(msg)
        assert out.text == "hello"
        assert out.media == []


class TestEnrichImage:
    @pytest.mark.asyncio
    async def test_photo_added_as_inline(
        self, stub_parse, tmp_path,
    ) -> None:
        path = tmp_path / "pic.jpg"
        path.write_bytes(b"\xff\xd8\xff")
        msg = LeoMessage(
            role="user",
            text="look",
            media=[MediaAttachment(mime_type="image/jpeg", path=str(path))],
        )
        out = await enrich_message(msg)
        assert "[Photo]" in out.text
        assert "[parsed image/jpeg]" in out.text
        assert out.media == []

    @pytest.mark.asyncio
    async def test_missing_file_yields_fallback(
        self, stub_parse,
    ) -> None:
        msg = LeoMessage(
            role="user",
            text="",
            media=[MediaAttachment(mime_type="image/png", path="/does/not/exist.png")],
        )
        out = await enrich_message(msg)
        assert "[Photo: analysis unavailable]" in out.text


class TestEnrichAudio:
    @pytest.mark.asyncio
    async def test_voice_note_routed_to_voice_transcribe(
        self, stub_transcribe, tmp_path,
    ) -> None:
        path = tmp_path / "vn.ogg"
        path.write_bytes(b"OggS")
        msg = LeoMessage(
            role="user",
            text="",
            media=[MediaAttachment(mime_type="audio/ogg", path=str(path))],
        )
        out = await enrich_message(msg)
        assert "[Voice note]: voice transcript" in out.text


class TestEnrichDocument:
    @pytest.mark.asyncio
    async def test_pdf_extracted(
        self, stub_parse, tmp_path,
    ) -> None:
        path = tmp_path / "spec.pdf"
        path.write_bytes(b"%PDF-")
        msg = LeoMessage(
            role="user",
            text="",
            media=[
                MediaAttachment(
                    mime_type="application/pdf",
                    path=str(path),
                    filename="spec.pdf",
                ),
            ],
        )
        out = await enrich_message(msg)
        assert "[Document: spec.pdf]" in out.text
        assert "[parsed application/pdf]" in out.text


class TestEnrichUnknown:
    @pytest.mark.asyncio
    async def test_unsupported_mime_documented(
        self, tmp_path,
    ) -> None:
        path = tmp_path / "x.bin"
        path.write_bytes(b"binary-garbage")
        msg = LeoMessage(
            role="user",
            text="huh",
            media=[MediaAttachment(mime_type="application/octet-stream", path=str(path))],
        )
        out = await enrich_message(msg)
        assert "not processed" in out.text


class TestBase64Attachment:
    @pytest.mark.asyncio
    async def test_inline_data_written_to_tmpfile(
        self, stub_parse,
    ) -> None:
        import base64
        payload = base64.b64encode(b"\xff\xd8\xff\xe0").decode()
        msg = LeoMessage(
            role="user",
            text="",
            media=[MediaAttachment(mime_type="image/jpeg", data=payload)],
        )
        out = await enrich_message(msg)
        assert "[Photo]" in out.text
