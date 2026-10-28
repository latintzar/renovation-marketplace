"""Hermes gateway — convert media attachments to text before the agent sees them.

:func:`enrich_message` accepts a :class:`~messaging.channel.LeoMessage` with
attachments of any supported MIME type and returns a new message whose text
body contains the extracted content in-line (``[Photo]``, ``[Voice note]``,
``[Document: …]`` blocks). The returned message has ``media=[]`` — downstream
agents are expected to reason over text only.

Delegation:

* Images, PDFs, DOCX, XLSX, CSV, TXT → :mod:`~.parse`
* Audio → :func:`voice.transcribe` (this package never owns a codec)
* URLs → :mod:`~.parse` (``parse_url``)
"""

from __future__ import annotations

import base64
import logging
import tempfile
from pathlib import Path

from ..channel import LeoMessage, MediaAttachment
from .parse import parse_media

logger = logging.getLogger(__name__)

_DOCUMENT_MIMES = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/msword",
    "text/csv",
    "text/plain",
    "text/markdown",
    "application/json",
    "application/xml",
    "text/xml",
})

_MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/aac": ".aac",
    "audio/webm": ".webm",
    "audio/wav": ".wav",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/csv": ".csv",
}


async def enrich_message(msg: LeoMessage) -> LeoMessage:
    """Convert all media attachments on ``msg`` into in-line text.

    After this function, the returned :class:`~messaging.channel.LeoMessage`
    has ``media=[]`` and ``text`` contains labelled extractions for every
    attachment. The agent never sees raw media — this is the Hermes
    gateway pattern.
    """
    if not msg.media:
        return msg

    enriched_text = msg.text or ""

    for attachment in msg.media:
        mime_base = attachment.mime_type.split(";")[0].strip().lower()
        try:
            if mime_base.startswith("image/"):
                analysis = await _enrich_image(attachment)
                if analysis:
                    enriched_text += f"\n[Photo]:\n{analysis}"
                else:
                    enriched_text += "\n[Photo: analysis unavailable]"

            elif mime_base.startswith("audio/"):
                transcript = await _enrich_audio(attachment)
                if transcript:
                    enriched_text += f"\n[Voice note]: {transcript}"
                else:
                    enriched_text += "\n[Voice note: transcription unavailable]"

            elif mime_base in _DOCUMENT_MIMES or _is_document_mime(mime_base):
                extracted = await _enrich_document(attachment)
                fname = attachment.filename or "document"
                if extracted:
                    enriched_text += f"\n[Document: {fname}]\n\n{extracted}"
                else:
                    enriched_text += f"\n[Document: {fname} — extraction failed]"

            else:
                logger.info("enrich_message: skipping unsupported mime=%s", mime_base)
                enriched_text += f"\n[Attachment: {mime_base} — not processed]"

        except Exception as exc:
            logger.warning(
                "enrich_message: failed to process %s attachment | %s",
                mime_base, exc, exc_info=True,
            )
            enriched_text += f"\n[Attachment: {mime_base} — processing error]"

    return LeoMessage(role=msg.role, text=enriched_text.strip(), media=[])


def _is_document_mime(mime: str) -> bool:
    """Catch document MIME variants not in the frozen set."""
    return (
        "spreadsheetml" in mime
        or "wordprocessingml" in mime
        or "pdf" in mime
        or mime.startswith("text/")
    )


def _resolve_path(attachment: MediaAttachment) -> Path:
    """Get a local file path, writing base64 to a temp file if needed (web chat uploads)."""
    if attachment.path:
        return Path(attachment.path)

    if attachment.data:
        ext = _MIME_TO_EXT.get(
            attachment.mime_type.split(";")[0].strip().lower(), ".bin"
        )
        raw = base64.b64decode(attachment.data)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(raw)
        tmp.close()
        logger.debug(
            "enrich: wrote base64 attachment to temp file | %s | %d bytes",
            tmp.name, len(raw),
        )
        return Path(tmp.name)

    raise ValueError("MediaAttachment has neither path nor data")


async def _enrich_image(attachment: MediaAttachment) -> str:
    fpath = _resolve_path(attachment)
    if not fpath.exists():
        logger.warning("enrich_image: file not found | %s", fpath)
        return ""

    mime = attachment.mime_type.split(";")[0].strip().lower()
    result = await parse_media(fpath, mime, caption=attachment.caption)
    logger.info(
        "enrich_image | file=%s | chars=%d",
        fpath.name, len(result or ""),
    )
    return result or ""


async def _enrich_audio(attachment: MediaAttachment) -> str:
    """Transcribe audio via :func:`voice.transcribe`. Messaging never owns a codec."""
    fpath = _resolve_path(attachment)
    if not fpath.exists():
        logger.warning("enrich_audio: file not found | %s", fpath)
        return ""

    return await transcribe_file(fpath)


async def transcribe_file(fpath: Path) -> str:
    """Transcribe an audio file on disk using the best available STT provider.

    Also a public helper used by the WhatsApp webhook path for contractor
    voice extraction — we don't want that caller duplicating the provider-
    routing logic.
    """
    from voice import transcribe

    audio_bytes = fpath.read_bytes()
    if not audio_bytes:
        return ""

    ct = "audio/ogg" if fpath.suffix == ".ogg" else f"audio/{fpath.suffix.lstrip('.')}"

    result = await transcribe(audio_bytes, content_type=ct, provider="auto", polish=True)

    logger.info(
        "transcribe_file | provider=%s | lang=%s | %.1fs | %d chars",
        result.provider, result.lang, result.asr_seconds, len(result.text),
    )
    return result.text


async def _enrich_document(attachment: MediaAttachment) -> str:
    fpath = _resolve_path(attachment)
    if not fpath.exists():
        logger.warning("enrich_document: file not found | %s", fpath)
        return ""

    mime = attachment.mime_type.split(";")[0].strip().lower()
    result = await parse_media(fpath, mime, caption=attachment.caption)
    logger.info(
        "enrich_document | file=%s | mime=%s | chars=%d",
        fpath.name, mime, len(result or ""),
    )
    return result or ""


__all__ = ["enrich_message", "transcribe_file"]
