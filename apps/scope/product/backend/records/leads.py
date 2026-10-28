"""records.leads — ``cs_leads`` + ``early_access_signups`` durable writes.

Two public functions plus a read helper:

- :func:`save_lead` — primary path writes to ``cs_leads``; on failure
  falls back to ``early_access_signups`` with a mangled source string.
  **Never raises.** Errors surface via :class:`LeadSaveResult`.
- :func:`patch_lead_structured` — read-modify-write the
  ``cs_leads.chat_summary`` column, embedding a JSON blob via the
  ``---LEO_STRUCTURED---`` marker (see ``design.md`` D14).
- :func:`get_lead_by_phone` — most-recent-row lookup by phone.

The dual-table fallback, the 4000-char cap on ``chat_summary``, and
the marker-based JSON blob are load-bearing legacy invariants —
preserved verbatim; documented in the ``design.md`` migration doc.

Moved from ``packages/storage/src/storage/leads.py`` in Phase 5 Wave 3
because Lead and the ``cs_leads`` / ``early_access_signups`` tables are
scope-specific schemas, not shared storage engines.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core import http_client, sb_headers, sb_key, sb_url

from .types import Lead, LeadSaveResult

logger = logging.getLogger(__name__)

_STRUCTURED_MARKER = "\n\n---LEO_STRUCTURED---\n"
_MAX_CHAT_SUMMARY_CHARS = 4000


async def save_lead(
    name: str,
    whatsapp: str,
    location: str,
    *,
    source: str = "leo_chat",
    chat_summary: str = "",
    chat_history: Optional[List[Dict[str, Any]]] = None,
) -> LeadSaveResult:
    """Insert a new lead row.

    Primary write is ``cs_leads``. If that fails (schema drift,
    unexpected 4xx/5xx), falls back to ``early_access_signups`` with
    ``source = f"{source} [{name}] {chat_summary[:100]}"`` to keep
    some lead signal.

    Never raises. Errors surface via
    :attr:`LeadSaveResult.ok` = ``False`` + ``error``.
    """

    url = sb_url()
    key = sb_key()
    if not url or not key:
        logger.error("Supabase credentials missing for save_lead")
        return LeadSaveResult(
            ok=False,
            error="db_not_configured",
        )

    headers = {**sb_headers(), "Prefer": "return=representation"}

    row: Dict[str, Any] = {
        "name": name.strip() or None,
        "whatsapp": whatsapp.strip() or None,
        "location": location.strip() or None,
        "source": source,
        "chat_summary": chat_summary.strip() or None,
    }
    if chat_history:
        row["chat_history"] = chat_history

    async with http_client(timeout=10) as client:
        resp = await client.post(
            f"{url}/cs_leads",
            headers=headers,
            json=row,
        )
        if resp.status_code in (200, 201):
            lead_id = _extract_id(resp)
            logger.info(
                "Lead saved to cs_leads | name=%s | loc=%s | summary=%s",
                name, location, chat_summary[:60],
            )
            return LeadSaveResult(ok=True, table_written="cs_leads", lead_id=lead_id)

        logger.warning(
            "cs_leads insert failed (%s) | body=%s",
            resp.status_code, resp.text[:200],
        )
        fallback_row = {
            "email": None,
            "whatsapp": whatsapp.strip() or None,
            "location": location.strip() or None,
            "source": f"{source} [{name.strip()}] {chat_summary[:100]}",
        }
        resp2 = await client.post(
            f"{url}/early_access_signups",
            headers=headers,
            json=fallback_row,
        )
        if resp2.status_code in (200, 201):
            lead_id = _extract_id(resp2)
            logger.info("Lead saved to early_access_signups (fallback) | name=%s", name)
            return LeadSaveResult(
                ok=True,
                table_written="early_access_signups",
                lead_id=lead_id,
            )

        logger.error(
            "Both save attempts failed | cs_leads=%s | ea=%s",
            resp.status_code, resp2.status_code,
        )
        return LeadSaveResult(
            ok=False,
            error=f"cs_leads={resp.status_code},ea={resp2.status_code}",
        )


async def patch_lead_structured(
    phone: str,
    *,
    brief: Optional[Dict[str, Any]] = None,
    profile: Optional[Dict[str, Any]] = None,
) -> bool:
    """Embed a JSON blob into ``cs_leads.chat_summary`` via the
    ``---LEO_STRUCTURED---`` marker.

    Reads the existing ``chat_summary``, strips any previous blob,
    appends the new ``{brief, profile}`` payload, and truncates to
    ``_MAX_CHAT_SUMMARY_CHARS``. Returns ``True`` on HTTP 200/204,
    ``False`` otherwise.

    Backward-compat hack; the structured JSON will migrate to proper
    ``structured_brief`` / ``structured_profile`` jsonb columns in a
    follow-up (see ``design.md`` D14).
    """

    if not phone:
        return False
    url = sb_url()
    key = sb_key()
    if not url or not key:
        return False

    clean_phone = phone.strip()
    headers = {**sb_headers(), "Prefer": "return=minimal"}
    read_headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    async with http_client(timeout=10) as client:
        get_resp = await client.get(
            f"{url}/cs_leads",
            params={
                "whatsapp": f"eq.{clean_phone}",
                "select": "chat_summary",
                "order": "created_at.desc",
                "limit": "1",
            },
            headers=read_headers,
        )
        if get_resp.status_code != 200:
            logger.warning(
                "patch_lead_structured: read failed | status=%s",
                get_resp.status_code,
            )
            return False
        rows = get_resp.json()
        if not rows:
            return False

        existing = (rows[0].get("chat_summary") or "").strip()
        base = existing.split(_STRUCTURED_MARKER, 1)[0].strip()
        payload: Dict[str, Any] = {}
        if brief is not None:
            payload["brief"] = brief
        if profile is not None:
            payload["profile"] = profile
        if not payload:
            return True
        blob = json.dumps(payload, ensure_ascii=False)

        new_summary = (base + _STRUCTURED_MARKER + blob)[:_MAX_CHAT_SUMMARY_CHARS]

        resp = await client.patch(
            f"{url}/cs_leads",
            params={"whatsapp": f"eq.{clean_phone}"},
            headers=headers,
            json={"chat_summary": new_summary},
        )
        ok = resp.status_code in (200, 204)
        if not ok:
            logger.warning(
                "patch_lead_structured: patch failed | status=%s",
                resp.status_code,
            )
        return ok


async def get_lead_by_phone(phone: str) -> Optional[Lead]:
    """Fetch the most-recent ``cs_leads`` row for a phone number.

    Returns ``None`` if not found or on error.
    """

    if not phone:
        return None
    url = sb_url()
    key = sb_key()
    if not url or not key:
        return None

    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{url}/cs_leads",
            params={
                "whatsapp": f"eq.{phone.strip()}",
                "select": "*",
                "order": "created_at.desc",
                "limit": "1",
            },
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        if resp.status_code != 200:
            return None
        rows = resp.json()
        if not rows:
            return None
        return _row_to_lead(rows[0])


def _row_to_lead(row: Dict[str, Any]) -> Lead:
    created_at = _parse_ts(row.get("created_at"))
    return Lead(
        id=str(row.get("id", "")),
        name=row.get("name") or "",
        whatsapp=row.get("whatsapp") or "",
        location=row.get("location") or "",
        source=row.get("source") or "",
        chat_summary=row.get("chat_summary") or "",
        chat_history=row.get("chat_history"),
        audience=row.get("audience"),
        created_at=created_at,
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


def _extract_id(resp: Any) -> Optional[str]:
    try:
        data = resp.json()
    except Exception:
        return None
    if isinstance(data, list) and data:
        row = data[0]
    elif isinstance(data, dict):
        row = data
    else:
        return None
    value = row.get("id")
    return str(value) if value is not None else None


__all__ = ["save_lead", "patch_lead_structured", "get_lead_by_phone"]
