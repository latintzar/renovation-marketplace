"""Media enrichment — image / audio / document / URL to text.

One public function, :func:`enrich_message`, implements the **Hermes gateway
pattern**: every channel's raw media attachments on a
:class:`~messaging.channel.LeoMessage` become in-line text before the agent
sees the message. Effect: the LLM reasons over uniform text regardless of
whether the user sent a photo from WhatsApp, a PDF from web chat, or a voice
note from email.

Delegation graph:

* **Images / documents** → :func:`~.parse.parse_media` (Bedrock Haiku 4.5
  vision, Qwen3 VL fallback; structure-preserving markdown via pymupdf4llm
  for PDFs, python-docx for DOCX, openpyxl for XLSX).
* **Audio** → :func:`voice.transcribe` (Groq/HF/local Whisper). The
  ``messaging`` package never owns a codec path — audio handling lives
  in :mod:`voice`.
* **URLs** → :func:`~.parse.parse_url` (trafilatura).

The :class:`~messaging.channel.LeoMessage` returned by :func:`enrich_message`
has ``media=[]`` — raw attachments are consumed.
"""

from __future__ import annotations

from .enrich import enrich_message, transcribe_file
from .parse import parse_media, parse_url

__all__ = [
    "enrich_message",
    "transcribe_file",
    "parse_media",
    "parse_url",
]
