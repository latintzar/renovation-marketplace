"""Universal media parser — structured markdown from any supported input.

One public entry point, :func:`parse_media`, dispatches by MIME to:

* Images → Bedrock Claude Haiku 4.5 vision (Qwen3 VL fallback).
* PDFs → ``pymupdf4llm`` (markdown with tables preserved).
* DOCX → ``python-docx`` (markdown with tables).
* XLSX/XLS → ``openpyxl`` (one markdown table per sheet).
* CSV → stdlib ``csv`` → markdown table.
* TXT / MD / JSON / XML → raw read.

URL content extraction lives in :func:`parse_url`, which fetches via
:func:`core.http_client` and extracts readable markdown via trafilatura.

Invariants:

* Numbers stay associated with their correct label/column — the table
  structure of receipts and invoices must survive OCR.
* Everything is capped at :data:`MAX_DOC_CHARS` so a huge upload never
  overruns the LLM context. :func:`enrich_message` composes results
  from many attachments and depends on this bound.
* Failures return the empty string — the caller annotates "extraction
  unavailable" to the user so the conversation doesn't stall.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from pathlib import Path

from core import http_client

logger = logging.getLogger(__name__)

MAX_DOC_CHARS = 30_000
MAX_IMAGE_TOKENS = 2000


async def parse_media(
    fpath: Path,
    mime_type: str,
    caption: str = "",
) -> str:
    """Parse any media file into structured markdown text.

    Returns empty string on failure. The caller decides how to report
    that to the user (see :func:`messaging.media.enrich.enrich_message`).
    """
    mime = mime_type.split(";")[0].strip().lower()

    if mime.startswith("image/"):
        return await _parse_image(fpath, mime, caption)

    if "pdf" in mime:
        return await _parse_pdf(fpath)

    if "wordprocessingml" in mime or fpath.suffix.lower() == ".docx":
        return await _parse_docx(fpath)

    if "spreadsheetml" in mime or fpath.suffix.lower() in (".xlsx", ".xls"):
        return await _parse_xlsx(fpath)

    if mime in ("text/csv",) or fpath.suffix.lower() == ".csv":
        return await _parse_csv(fpath)

    if mime.startswith("text/") or fpath.suffix.lower() in (".txt", ".md", ".json", ".xml"):
        return _parse_plaintext(fpath)

    logger.warning("parse_media: unsupported mime=%s suffix=%s", mime, fpath.suffix)
    return ""


async def parse_url(url: str, max_chars: int = 8000) -> str:
    """Fetch a URL and extract readable content as markdown via trafilatura."""
    try:
        import trafilatura

        async with http_client(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                url, headers={"User-Agent": "Mozilla/5.0 (compatible; LeoBot/1.0)"}
            )
            if resp.status_code != 200:
                return ""
            html = resp.text

        loop = asyncio.get_event_loop()
        extracted = await loop.run_in_executor(
            None,
            lambda: trafilatura.extract(
                html, include_comments=False, include_tables=True
            )
            or "",
        )
        return extracted[:max_chars] if extracted else ""
    except ImportError:
        logger.debug("trafilatura not installed, skipping URL extraction")
        return ""
    except Exception as exc:
        logger.debug("URL extraction failed | %s | %s", url[:60], exc)
        return ""


_STRUCTURE_PROMPT = """Analyze this image thoroughly and output structured markdown.

CRITICAL RULES FOR STRUCTURE PRESERVATION:
- If you see a TABLE, reproduce it as a markdown table with | separators and --- header row
- If you see NUMBERS next to labels, keep them correctly associated (e.g. "Price: €450" not just "450")
- If you see a LIST, reproduce it as a markdown list
- If you see a FORM or INVOICE, preserve the field:value structure
- If you see a SCREENSHOT of a post/message/listing, extract the FULL text content
- If you see CONTACT INFO (phone numbers, emails, addresses, names), extract them clearly
- If you see a RECEIPT or PRICE LIST, preserve every line item with its price

OUTPUT FORMAT:
### Description
[1-2 sentences of what the image shows overall]

### Extracted Content
[The actual structured content from the image — tables as tables, lists as lists, text as text]

### Key Details
[Phone numbers, names, addresses, prices, dates — anything a human would want to reference later]
"""


def _bedrock_client(region: str):
    """Lazy boto3 client — matches old ``shared.aws.bedrock_client`` signature."""
    import boto3

    return boto3.client("bedrock-runtime", region_name=region)


async def _parse_image(fpath: Path, mime: str, caption: str = "") -> str:
    raw = fpath.read_bytes()
    if not raw:
        return ""

    b64 = base64.b64encode(raw).decode()

    caption_hint = ""
    if caption and caption not in ("📷 Photo", "🎨 Sticker"):
        caption_hint = f'\nThe sender included this caption: "{caption}"'

    prompt = _STRUCTURE_PROMPT + caption_hint

    loop = asyncio.get_event_loop()

    try:
        client = _bedrock_client("eu-west-1")

        def _call_haiku() -> str:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": MAX_IMAGE_TOKENS,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime,
                                    "data": b64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            })
            resp = client.invoke_model(
                modelId="eu.anthropic.claude-haiku-4-5-20251001-v1:0",
                body=body,
            )
            result = json.loads(resp["body"].read())
            return result["content"][0]["text"]

        analysis = await loop.run_in_executor(None, _call_haiku)
        if analysis:
            logger.info(
                "parse_image OK | haiku | file=%s | chars=%d",
                fpath.name, len(analysis),
            )
            return analysis.strip()
    except Exception as exc:
        logger.warning("Haiku image parse failed, trying Qwen3 VL | %s", exc)

    try:
        client = _bedrock_client("us-east-1")

        def _call_qwen() -> str:
            body = json.dumps({
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime,
                                    "data": b64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                "max_tokens": MAX_IMAGE_TOKENS,
            })
            resp = client.invoke_model(
                modelId="qwen.qwen3-vl-235b-a22b", body=body,
            )
            result = json.loads(resp["body"].read())
            output = result.get("output", {})
            choices = output.get("choices", [])
            if choices:
                return (
                    choices[0].get("message", {}).get("content", [{}])[0].get("text", "")
                )
            return ""

        analysis = await loop.run_in_executor(None, _call_qwen)
        if analysis:
            logger.info(
                "parse_image OK | qwen3-vl | file=%s | chars=%d",
                fpath.name, len(analysis),
            )
            return analysis.strip()
    except Exception as exc2:
        logger.warning("Qwen3 VL image parse also failed | %s", exc2)

    return ""


def _extract_pdf_sync(path: str) -> str:
    """Sync: PDF → markdown via ``pymupdf4llm`` (table-aware layout engine)."""
    import pymupdf4llm

    return pymupdf4llm.to_markdown(path)


def _extract_docx_sync(path: str) -> str:
    """Sync: DOCX → markdown with tables preserved."""
    from docx import Document

    doc = Document(path)
    parts: list[str] = []

    for element in doc.element.body:
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

        if tag == "p":
            for para in doc.paragraphs:
                if para._element is element:
                    text = para.text.strip()
                    if text:
                        style = (para.style.name or "").lower()
                        if "heading" in style:
                            level = 1
                            for ch in style:
                                if ch.isdigit():
                                    level = int(ch)
                                    break
                            parts.append(f"{'#' * level} {text}")
                        else:
                            parts.append(text)
                    break

        elif tag == "tbl":
            from docx.table import Table as DocxTable

            tbl = DocxTable(element, doc)
            rows = []
            for row in tbl.rows:
                cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                rows.append("| " + " | ".join(cells) + " |")
            if rows:
                header = rows[0]
                separator = "| " + " | ".join("---" for _ in tbl.rows[0].cells) + " |"
                parts.append(header)
                parts.append(separator)
                parts.extend(rows[1:])

    return "\n\n".join(parts)


async def _parse_pdf(fpath: Path) -> str:
    loop = asyncio.get_event_loop()
    try:
        md = await loop.run_in_executor(None, _extract_pdf_sync, str(fpath))
        return md[:MAX_DOC_CHARS] if md else ""
    except Exception as exc:
        logger.warning("PDF parse failed | %s | %s", fpath.name, exc)
        return ""


async def _parse_docx(fpath: Path) -> str:
    loop = asyncio.get_event_loop()
    try:
        md = await loop.run_in_executor(None, _extract_docx_sync, str(fpath))
        return md[:MAX_DOC_CHARS] if md else ""
    except Exception as exc:
        logger.warning("DOCX parse failed | %s | %s", fpath.name, exc)
        return ""


async def _parse_xlsx(fpath: Path) -> str:
    loop = asyncio.get_event_loop()

    def _extract() -> str:
        import openpyxl

        wb = openpyxl.load_workbook(str(fpath), read_only=True, data_only=True)
        parts: list[str] = []
        for ws in wb.worksheets:
            parts.append(f"## Sheet: {ws.title}\n")
            rows_data = []
            for row in ws.iter_rows(max_row=500, values_only=True):
                cells = [str(c) if c is not None else "" for c in row]
                rows_data.append(cells)

            if rows_data:
                header = "| " + " | ".join(rows_data[0]) + " |"
                separator = "| " + " | ".join("---" for _ in rows_data[0]) + " |"
                parts.append(header)
                parts.append(separator)
                for row_cells in rows_data[1:]:
                    padded = row_cells + [""] * (len(rows_data[0]) - len(row_cells))
                    parts.append("| " + " | ".join(padded[:len(rows_data[0])]) + " |")
            parts.append("")
        wb.close()
        return "\n".join(parts)

    try:
        md = await loop.run_in_executor(None, _extract)
        return md[:MAX_DOC_CHARS] if md else ""
    except Exception as exc:
        logger.warning("XLSX parse failed | %s | %s", fpath.name, exc)
        return ""


async def _parse_csv(fpath: Path) -> str:
    loop = asyncio.get_event_loop()

    def _extract() -> str:
        import csv

        with open(fpath, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            rows: list[list[str]] = []
            for i, row in enumerate(reader):
                if i >= 500:
                    break
                rows.append(row)

        if not rows:
            return ""

        max_cols = max(len(r) for r in rows)
        parts: list[str] = []
        header = rows[0] + [""] * (max_cols - len(rows[0]))
        parts.append("| " + " | ".join(header) + " |")
        parts.append("| " + " | ".join("---" for _ in range(max_cols)) + " |")
        for row in rows[1:]:
            padded = row + [""] * (max_cols - len(row))
            parts.append("| " + " | ".join(padded) + " |")
        return "\n".join(parts)

    try:
        md = await loop.run_in_executor(None, _extract)
        return md[:MAX_DOC_CHARS] if md else ""
    except Exception as exc:
        logger.warning("CSV parse failed | %s | %s", fpath.name, exc)
        return ""


def _parse_plaintext(fpath: Path) -> str:
    try:
        return fpath.read_text(encoding="utf-8", errors="replace")[:MAX_DOC_CHARS]
    except Exception as exc:
        logger.warning("Plaintext parse failed | %s | %s", fpath.name, exc)
        return ""


__all__ = ["parse_media", "parse_url", "MAX_DOC_CHARS", "MAX_IMAGE_TOKENS"]
