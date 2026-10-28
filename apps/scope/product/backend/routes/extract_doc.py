"""
Document text extraction endpoint
=================================

POST /api/extract-doc — Upload a PDF or DOCX, get back Markdown text
(with tables preserved) for LLM context injection.

Uses the canonical parse_media module for all extraction.
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from messaging import _extract_pdf_sync, _extract_docx_sync

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
MAX_OUTPUT_CHARS = 50_000


@router.post("/api/extract-doc")
async def extract_doc(file: UploadFile = File(...)) -> JSONResponse:
    """Extract text from PDF/DOCX as Markdown (tables preserved)."""
    if not file.filename:
        return JSONResponse({"error": "no filename"}, status_code=400)

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JSONResponse(
            {"error": f"unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"},
            status_code=400,
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return JSONResponse({"error": f"file too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)"}, status_code=400)

    if len(content) == 0:
        return JSONResponse({"error": "empty file"}, status_code=400)

    suffix = ext if ext != ".doc" else ".docx"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(content)
        tmp.close()

        loop = asyncio.get_event_loop()
        if ext == ".pdf":
            markdown = await loop.run_in_executor(None, _extract_pdf_sync, tmp.name)
        else:
            markdown = await loop.run_in_executor(None, _extract_docx_sync, tmp.name)

        if len(markdown) > MAX_OUTPUT_CHARS:
            markdown = markdown[:MAX_OUTPUT_CHARS] + "\n\n[... document truncated ...]"

        logger.info("extract-doc | file=%s ext=%s chars=%d", file.filename, ext, len(markdown))
        return JSONResponse({"markdown": markdown, "chars": len(markdown), "filename": file.filename})

    except Exception as exc:
        logger.error("extract-doc failed | file=%s | %s", file.filename, exc, exc_info=True)
        return JSONResponse({"error": f"extraction failed: {str(exc)}"}, status_code=500)
    finally:
        os.unlink(tmp.name)
