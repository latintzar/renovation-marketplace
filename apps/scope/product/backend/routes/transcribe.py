"""
Voice Note Transcription
========================

POST ``/api/transcribe`` — accepts audio blob, returns text transcript.

- **local** (default when no cloud keys): **faster-whisper** on CPU.
- **groq**: Groq OpenAI-compatible ``/audio/transcriptions``.
- **huggingface**: HF Inference ASR.
- **auto**: Groq if ``GROQ_API_KEY`` set, else HF if token set, else local.

Query: ``provider=auto|local|groq|huggingface`` (alias ``hf``), ``polish=true|false``,
optional ``language`` (ISO-639-1 hint). Omit or ``auto`` for multilingual auto-detect.

All transcription logic lives in ``shared/voice.py``.
"""

import asyncio
import logging
import time

from fastapi import APIRouter, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse

from voice import polish_sync, transcribe

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    polish: bool = Query(
        True,
        description="If true, run Bedrock LLM to lightly clean the Whisper text.",
    ),
    provider: str = Query(
        "auto",
        description="auto | local | groq | huggingface (hf). auto prefers Groq, then HF, then local CPU.",
    ),
    language: str | None = Query(
        None,
        description="Optional ISO-639-1 hint (en, es, …). Omit or 'auto' for multilingual auto-detect.",
    ),
) -> JSONResponse:
    content = await audio.read()
    if not content:
        return JSONResponse({"error": "empty audio"}, status_code=400)

    if len(content) > 10 * 1024 * 1024:
        return JSONResponse({"error": "audio too large (max 10MB)"}, status_code=400)

    try:
        result = await transcribe(
            content,
            content_type=audio.content_type or "",
            language=language,
            provider=provider,
            polish=polish,
        )
    except ValueError as err:
        return JSONResponse({"error": str(err)}, status_code=400)
    except Exception as exc:
        logger.error("Transcription error | provider=%s | %s", provider, exc, exc_info=True)
        return JSONResponse({"error": "transcription failed"}, status_code=500)

    if not result.text:
        return JSONResponse({"text": "", "empty": True, "provider": result.provider, "asr_s": round(result.asr_seconds, 3)})
    return JSONResponse(
        {
            "text": result.text,
            "lang": result.lang,
            "provider": result.provider,
            "asr_s": round(result.asr_seconds, 3),
        }
    )


@router.post("/api/transcribe/polish")
async def polish_text(
    text: str = Form(...),
) -> JSONResponse:
    """Polish raw Whisper text with Bedrock LLM. No re-transcription."""
    text = (text or "").strip()
    if not text:
        return JSONResponse({"error": "empty text"}, status_code=400)

    t0 = time.time()
    try:
        polished = await asyncio.to_thread(polish_sync, text)
        elapsed = time.time() - t0
        logger.info("Polish-only | %.1fs | %d→%d chars", elapsed, len(text), len(polished))
        return JSONResponse({"text": polished})
    except Exception as exc:
        logger.error("Polish error | %s", exc, exc_info=True)
        return JSONResponse({"text": text})
