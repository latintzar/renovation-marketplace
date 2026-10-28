"""records.conversations — verbatim message log (whatsapp + web).

**Purpose.** Per-user, per-channel durable log of every message. The
messaging layer's durable log; feeds :func:`summarize_recent` for
LLM context. Two tables today:

- ``whatsapp_messages`` — existing; WA inbound + outbound. Legacy
  column layout (``phone_number``, ``message_text``, ``message_type``,
  ``media_urls[]``). This module adapts the generic API to the legacy
  schema at the WA boundary.
- ``web_messages`` — **new** (Phase-4 migration adds it); web-chat
  history. Target schema with the consistent column names
  (``user_id``, ``role``, ``text``, ``metadata``).

**API** is channel-agnostic:

- :func:`add_message` — append a row.
- :func:`get_messages` — paginated, cursor-based (``before``),
  newest-first, cap 200.
- :func:`get_recent_window` — convenience: last N hours, capped.
- :func:`summarize_recent` — recency-weighted summary built with
  :mod:`llm` (Haiku). Graceful fallback if ``llm.complete`` fails.

Retention: **infinite** by default — WA history is a legal audit trail
(Spain B2B commerce) and full history feeds summarization /
re-engagement. See design §D11.

Moved from ``packages/storage/src/storage/conversations.py`` in
Phase 5 Wave 3 because Message and the ``whatsapp_messages`` /
``web_messages`` tables are scope schemas, not shared storage engines.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

from core import http_client, sb_headers, sb_key, sb_url

from .types import Message

logger = logging.getLogger(__name__)

Channel = Literal["whatsapp", "web"]
Role = Literal["user", "assistant", "system"]

_MAX_PAGE = 200
_DEFAULT_PAGE = 50
_DEFAULT_WINDOW_HOURS = 24
_DEFAULT_WINDOW_CAP = 200


SUMMARY_PROMPT = (
    "Summarize the older portion of a WhatsApp/web conversation between a "
    "Spanish homeowner and Leo (an AI assistant helping them hire a "
    "contractor). Produce concise English bullet points, one per 15-minute "
    "bucket, preserving concrete facts (address, budget, trade, "
    "constraints). Do not summarize the verbatim tail; it will be appended "
    "separately.\n\n"
)


async def add_message(
    user_id: str,
    role: Role,
    text: str,
    *,
    channel: Channel = "whatsapp",
    media_url: Optional[str] = None,
    wa_message_id: Optional[str] = None,
    reply_to_wa_id: Optional[str] = None,
    reply_to_text: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Message]:
    """Append a message row to ``whatsapp_messages`` or ``web_messages``.

    :param user_id: phone (WA) or anon-token/lead-id (web).
    :param role: one of ``"user"``, ``"assistant"``, ``"system"``.
    :param text: message body (may be empty for media-only rows).
    :param channel: routing key; selects the table + column layout.
    :param media_url: optional attached media URL. For WA, stored as
        the first element of legacy ``media_urls[]``. For web, stored
        scalar.
    :param wa_message_id: Meta message id; WA only (ignored for web).
    :param reply_to_wa_id: Meta reply pointer; WA only.
    :param reply_to_text: verbatim quoted-reply text; WA only.
    :param metadata: caller-supplied jsonb. Never trust for PII scrub.

    Returns ``None`` on HTTP error (never raises).
    """

    url = sb_url()
    key = sb_key()
    if not url or not key:
        logger.error("Supabase credentials missing for add_message")
        return None

    now = datetime.now(timezone.utc).isoformat()

    if channel == "whatsapp":
        row: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "phone_number": user_id,
            "role": role,
            "message_text": text,
            "message_type": "text",
            "media_urls": [media_url] if media_url else [],
            "media_types": [],
            "created_at": now,
        }
        if wa_message_id:
            row["wa_message_id"] = wa_message_id
        if reply_to_wa_id:
            row["reply_to_wa_id"] = reply_to_wa_id
        if reply_to_text:
            row["reply_to_text"] = reply_to_text
        table = "whatsapp_messages"
    else:
        row = {
            "id": str(uuid.uuid4()),
            "channel": channel,
            "user_id": user_id,
            "role": role,
            "text": text,
            "created_at": now,
        }
        if media_url:
            row["media_url"] = media_url
        if metadata:
            row["metadata"] = metadata
        table = "web_messages"

    try:
        async with http_client(timeout=10) as client:
            resp = await client.post(
                f"{url}/{table}",
                headers={**sb_headers(), "Prefer": "return=representation"},
                json=row,
            )
            if resp.status_code in (200, 201):
                rows = resp.json()
                stored = rows[0] if isinstance(rows, list) and rows else rows
                return _row_to_message(stored, channel=channel)
            logger.error(
                "add_message insert failed | table=%s status=%s body=%s",
                table, resp.status_code, resp.text[:200],
            )
    except Exception as exc:
        logger.error("add_message error | %s", exc, exc_info=True)
    return None


async def get_messages(
    user_id: str,
    *,
    channel: Channel = "whatsapp",
    before: Optional[datetime] = None,
    limit: int = _DEFAULT_PAGE,
) -> List[Message]:
    """Fetch messages for a user, newest-first, paginated.

    :param user_id: phone (WA) or anon-token/lead-id (web).
    :param channel: selects the table.
    :param before: cursor — only return rows strictly older than this.
        ``None`` = latest rows.
    :param limit: page size. Clamped to ``1 <= limit <= 200``.
    :returns: up to ``limit`` rows, sorted DESC by ``created_at``. Empty
        list on error (never raises).
    """

    url = sb_url()
    key = sb_key()
    if not url or not key:
        return []

    limit = max(1, min(_MAX_PAGE, int(limit)))

    if channel == "whatsapp":
        table = "whatsapp_messages"
        params: Dict[str, str] = {
            "phone_number": f"eq.{user_id}",
            "select": "*",
            "order": "created_at.desc",
            "limit": str(limit),
        }
    else:
        table = "web_messages"
        params = {
            "user_id": f"eq.{user_id}",
            "channel": f"eq.{channel}",
            "select": "*",
            "order": "created_at.desc",
            "limit": str(limit),
        }

    if before is not None:
        params["created_at"] = f"lt.{before.isoformat()}"

    try:
        async with http_client(timeout=10) as client:
            resp = await client.get(
                f"{url}/{table}",
                params=params,
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
            )
            if resp.status_code == 200:
                rows = resp.json() or []
                return [_row_to_message(r, channel=channel) for r in rows]
            logger.warning(
                "get_messages failed | table=%s status=%s",
                table, resp.status_code,
            )
    except Exception as exc:
        logger.warning("get_messages error | %s", exc)
    return []


async def get_recent_window(
    user_id: str,
    *,
    channel: Channel = "whatsapp",
    hours: int = _DEFAULT_WINDOW_HOURS,
    cap: int = _DEFAULT_WINDOW_CAP,
) -> List[Message]:
    """Messages from the last ``hours``, capped at ``cap`` rows.

    Uses :func:`get_messages` internally; the window filter is applied
    post-query (small pages, not worth a second round-trip for the
    rare case where 200 messages land in 24h).

    :returns: rows newest-first.
    """

    cap = max(1, min(_MAX_PAGE, int(cap)))
    rows = await get_messages(user_id, channel=channel, limit=cap)
    if not rows or hours <= 0:
        return rows

    cutoff = datetime.now(timezone.utc) - timedelta(hours=int(hours))
    filtered: List[Message] = []
    for msg in rows:
        ts = msg.created_at
        if ts is None or _ensure_aware(ts) >= cutoff:
            filtered.append(msg)
    return filtered


async def summarize_recent(
    user_id: str,
    *,
    channel: Channel = "whatsapp",
    recent_verbatim: int = 20,
    max_chars: int = 3000,
) -> str:
    """Recency-weighted summary of a user's conversation.

    Algorithm:

    1. Fetch last 200 messages for (user_id, channel).
    2. The newest ``recent_verbatim`` rows are kept verbatim as
       ``role: text`` lines.
    3. Everything older is grouped into 15-minute buckets; each bucket
       fed to :func:`llm.complete` at summary-tier (Haiku). One bullet
       per bucket.
    4. Prepend bullets chronologically, append verbatim tail.
    5. Trim to ``max_chars`` (older bullets drop first).

    If :func:`llm.complete` fails (proxy down, timeout), degrades
    gracefully to verbatim-only with a ``(... older messages
    omitted)`` marker.

    :returns: the rendered summary. Empty string if there are no
        messages.
    """

    messages = await get_messages(user_id, channel=channel, limit=_MAX_PAGE)
    if not messages:
        return ""

    messages_chrono = list(reversed(messages))
    recent_verbatim = max(0, int(recent_verbatim))
    if recent_verbatim >= len(messages_chrono):
        verbatim = messages_chrono
        older: List[Message] = []
    else:
        verbatim = messages_chrono[-recent_verbatim:] if recent_verbatim else []
        older = messages_chrono[: len(messages_chrono) - recent_verbatim]

    verbatim_lines = [f"{m.role}: {m.text}".strip() for m in verbatim if m.text]
    verbatim_block = "\n".join(verbatim_lines)

    bullets: List[str] = []
    if older:
        bullets = await _summarize_older(older)

    parts: List[str] = []
    if bullets:
        parts.append("\n".join(f"- {b}" for b in bullets))
    if verbatim_block:
        parts.append(verbatim_block)
    summary = "\n\n".join(parts).strip()

    if len(summary) > max_chars and bullets:
        dropped = 0
        while len(summary) > max_chars and bullets:
            bullets.pop(0)
            dropped += 1
            parts = []
            if bullets:
                parts.append("\n".join(f"- {b}" for b in bullets))
            if verbatim_block:
                parts.append(verbatim_block)
            summary = "\n\n".join(parts).strip()
        if dropped:
            summary = f"(... {dropped} older bullet(s) omitted)\n{summary}"

    if len(summary) > max_chars:
        summary = summary[:max_chars].rstrip() + " …"

    return summary


async def _summarize_older(older: List[Message]) -> List[str]:
    """Group into 15-min buckets and summarize each via :func:`llm.chat`.

    On LLM failure, returns a single degraded bullet noting the count.
    """

    if not older:
        return []

    try:
        from llm import Message as _LlmMessage, chat
    except Exception as exc:
        logger.debug("summarize_recent: llm import failed | %s", exc)
        return [f"({len(older)} older messages — summary unavailable)"]

    buckets: List[List[Message]] = []
    current: List[Message] = []
    last_bucket: Optional[datetime] = None

    for msg in older:
        ts = msg.created_at
        if ts is None:
            current.append(msg)
            continue
        aware = _ensure_aware(ts)
        bucket_key = aware.replace(minute=(aware.minute // 15) * 15, second=0, microsecond=0)
        if last_bucket is None or bucket_key == last_bucket:
            current.append(msg)
            last_bucket = bucket_key
        else:
            buckets.append(current)
            current = [msg]
            last_bucket = bucket_key
    if current:
        buckets.append(current)

    bullets: List[str] = []
    for bucket in buckets:
        lines = [f"{m.role}: {m.text}" for m in bucket if m.text]
        if not lines:
            continue
        prompt_body = SUMMARY_PROMPT + "\n".join(lines)
        try:
            resp = await chat(
                [_LlmMessage(role="user", content=prompt_body)],
                tier="cheap",
                max_tokens=160,
            )
            bullet = (resp.text or "").strip()
            if bullet:
                bullets.append(bullet)
        except Exception as exc:
            logger.warning("summarize_recent: llm.chat failed | %s", exc)
            bullets.append(f"({len(lines)} older message(s) — summary unavailable)")

    return bullets


def _row_to_message(row: Dict[str, Any], *, channel: Channel) -> Message:
    """Adapt legacy + target schemas into the unified :class:`Message`."""

    if channel == "whatsapp":
        user_id = row.get("phone_number", "") or ""
        text = row.get("message_text") or ""
        media_urls = row.get("media_urls") or []
        first_media = media_urls[0] if isinstance(media_urls, list) and media_urls else None
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else None
    else:
        user_id = row.get("user_id", "") or ""
        text = row.get("text") or ""
        first_media = row.get("media_url")
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else None

    role = row.get("role") or "user"
    if role not in ("user", "assistant", "system"):
        role = "user"

    return Message(
        id=str(row.get("id", "")),
        channel=channel,
        user_id=str(user_id),
        role=role,
        text=str(text),
        media_url=first_media if isinstance(first_media, str) else None,
        wa_message_id=row.get("wa_message_id"),
        reply_to_wa_id=row.get("reply_to_wa_id"),
        reply_to_text=row.get("reply_to_text"),
        metadata=metadata,
        created_at=_parse_ts(row.get("created_at")),
    )


def _parse_ts(raw: Any) -> Optional[datetime]:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _ensure_aware(ts: datetime) -> datetime:
    """Supabase timestamps are UTC; guard against naive by coercing."""

    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


__all__ = [
    "add_message",
    "get_messages",
    "get_recent_window",
    "summarize_recent",
    "SUMMARY_PROMPT",
]
