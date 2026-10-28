"""Persist structured brief/profile snippets onto cs_leads.chat_summary for WhatsApp continuity.

Also contains the business-logic functions called by Hermes tool handlers:
save_signup, whatsapp_handoff, notify_peter.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from core import http_client

logger = logging.getLogger(__name__)


def _wa_text_payload(body: str, max_len: int = 4096) -> dict:
    """Build a WhatsApp text payload, enabling link previews when URLs are present."""
    payload: dict = {"body": body.strip()[:max_len]}
    if "http://" in body or "https://" in body:
        payload["preview_url"] = True
    return payload


def _get_supabase() -> tuple[str, str]:
    """Get Supabase URL and key from the database module (single source of truth)."""
    try:
        from config import settings
        url = settings.SUPABASE_URL or ""
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or ""
        return url, key
    except Exception:
        url = os.getenv("SUPABASE_URL", "") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
        key = (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            or os.getenv("SUPABASE_SERVICE_KEY", "")
            or os.getenv("SUPABASE_ANON_KEY", "")
            or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
        )
        return url, key


# ── WhatsApp constants ────────────────────────────────────────────────

PETER_WA = "00000000000"
LEO_WA_NUMBER = "34607590602"
PETER_PERSONAL_WA = "34627506263"
META_API_BASE = "https://graph.facebook.com/v23.0"

# Same set as meta_whatsapp FOUNDER_DEBUG_PHONES / prompt_builder FOUNDER_PHONES
FOUNDER_WA_DIGITS = frozenset({PETER_WA, PETER_PERSONAL_WA})


def _wa_token() -> str:
    return os.getenv("WHATSAPP_TOKEN", "")


def _wa_phone_id() -> str:
    return os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")


# ── Notify founder ────────────────────────────────────────────────────

async def notify_peter(name: str, whatsapp: str, location: str, chat_summary: str) -> None:
    """Send Peter a WhatsApp message about a new signup. Fire-and-forget."""
    from messaging.whatsapp import send_wa_message

    lines = [f"\U0001f514 New lead: {name.strip() or '(no name)'}"]
    if location.strip():
        lines.append(f"\U0001f4cd {location.strip()}")
    if whatsapp.strip():
        lines.append(f"\U0001f4f1 {whatsapp.strip()}")
    if chat_summary.strip():
        lines.append(f"\n{chat_summary.strip()}")

    body = "\n".join(lines)

    try:
        result = await send_wa_message(PETER_WA, body, purpose="internal", do_store=False, skip_window_check=True)
        if result.ok:
            logger.info("Peter notified about lead | name=%s", name)
        else:
            logger.warning("Peter notification failed | error=%s", result.error)
    except Exception as exc:
        logger.warning("Peter notification error (non-fatal) | %s", exc)


async def notify_peter_lead_submitted(
    phone: str,
    name: str = "",
    location: str = "",
    job_text: str = "",
) -> None:
    """Notify Peter the instant a homeowner confirms their phone on the landing page.

    This fires from POST /api/leads/phone — before Leo has sent a WhatsApp,
    before any brief exists. It's the "successful submission" moment.

    Separate from notify_peter() (which fires from save_signup in web chat).
    Both stay in place — they cover different entry paths.
    """
    from messaging.whatsapp import send_wa_message

    lines = ["\U0001f4cb *New homeowner submission*"]
    if phone:
        lines.append(phone)
    if location:
        lines.append(f"\U0001f4cd {location}")
    elif not location:
        lines.append("\U0001f4cd location not yet given")
    lines.append("")
    if job_text:
        lines.append(job_text[:400])
    lines.append("")
    lines.append("\u2192 They'll receive a WhatsApp from Leo now.")

    body = "\n".join(lines)

    try:
        for recipient in (PETER_WA, PETER_PERSONAL_WA):
            await send_wa_message(
                recipient, body, purpose="internal", do_store=False, skip_window_check=True
            )
        logger.info(
            "Peter notified about homeowner submission | phone=%s",
            (phone or "")[:8] + "***",
        )
    except Exception as exc:
        logger.warning("notify_peter_lead_submitted error (non-fatal) | %s", exc)


async def notify_peter_discovery_complete(
    job_id: str,
    trade: str = "",
    city: str = "",
    sent: int = 0,
    deferred: int = 0,
    candidates_found: int = 0,
) -> None:
    """Notify Peter when contractor discovery finishes for a job.

    Includes key stats so he can decide whether to trigger outreach.
    """
    from messaging.whatsapp import send_wa_message

    lines = ["\U0001f50d *Discovery complete*"]
    if trade or city:
        lines.append(f"\U0001f4cb {trade} — {city}" if trade and city else f"\U0001f4cb {trade or city}")
    lines.append(f"Job: {job_id[:12]}")
    lines.append("")
    lines.append(f"\u2022 Candidates found: {candidates_found}")
    lines.append(f"\u2022 Outreach sent: {sent}")
    if deferred:
        lines.append(f"\u2022 Deferred to tomorrow: {deferred}")
    lines.append("")
    if sent > 0:
        lines.append("\u2192 Awaiting contractor replies. I'll notify you when they come in.")
    else:
        lines.append("\u2192 No outreach sent — review the job or adjust search criteria.")

    body = "\n".join(lines)

    try:
        for recipient in (PETER_WA, PETER_PERSONAL_WA):
            await send_wa_message(
                recipient, body, purpose="internal", do_store=False, skip_window_check=True
            )
        logger.info(
            "Peter notified about discovery complete | job=%s sent=%d",
            job_id[:8], sent,
        )
    except Exception as exc:
        logger.warning("notify_peter_discovery_complete error (non-fatal) | %s", exc)


async def notify_brief_confirmed(brief: Dict[str, Any], phone: str = "") -> None:
    """Send Peter a WhatsApp with the full brief when a homeowner confirms a job."""
    from messaging.whatsapp import send_wa_message

    title = brief.get("title", "Untitled job")
    desc = brief.get("description", "")
    loc = brief.get("location", "")
    urgency = brief.get("urgency", "")
    budget = brief.get("budget_indication", "")
    materials = brief.get("materials_mentioned", "")
    measurements = brief.get("measurements", "")

    lines = [f"\U0001f4cb *New job brief confirmed*"]
    lines.append(f"*{title}*")
    if loc:
        lines.append(f"\U0001f4cd {loc}")
    if phone:
        lines.append(f"\U0001f4f1 {phone}")
    lines.append("")
    if desc:
        lines.append(desc[:500])
    if measurements:
        lines.append(f"\U0001f4cf {measurements}")
    if materials:
        lines.append(f"\U0001f9f1 {materials}")
    if urgency:
        lines.append(f"\u23f0 {urgency}")
    if budget:
        lines.append(f"\U0001f4b0 {budget}")

    body = "\n".join(lines)

    try:
        for recipient in (PETER_WA, PETER_PERSONAL_WA):
            await send_wa_message(recipient, body, purpose="internal", do_store=False, skip_window_check=True)
        logger.info("Peter notified about confirmed brief | title=%s", title[:40])
    except Exception as exc:
        logger.warning("Brief notification error (non-fatal) | %s", exc)


# ── Save signup ───────────────────────────────────────────────────────

async def save_signup(
    name: str,
    whatsapp: str,
    location: str,
    source: str = "leo_chat",
    chat_summary: str = "",
    chat_history: list | None = None,
) -> str:
    sb_url, sb_key = _get_supabase()
    if not sb_url or not sb_key:
        logger.error("Supabase credentials missing for save_signup")
        return "saved (credentials missing — logged only)"

    headers = {
        "Content-Type": "application/json",
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Prefer": "return=minimal",
    }

    row: Dict[str, Any] = {
        "name": name.strip() or None,
        "whatsapp": whatsapp.strip() or None,
        "location": location.strip() or None,
        "source": source,
        "chat_summary": chat_summary.strip() or None,
    }
    if chat_history:
        row["chat_history"] = chat_history

    saved = False
    async with http_client(timeout=10) as client:
        resp = await client.post(
            f"{sb_url}/rest/v1/cs_leads",
            headers=headers,
            json=row,
        )
        if resp.status_code in (200, 201):
            logger.info("Lead saved to cs_leads | name=%s | loc=%s | summary=%s", name, location, chat_summary[:60])
            saved = True
        else:
            logger.warning("cs_leads insert failed (%s) | body=%s", resp.status_code, resp.text[:200])
            resp2 = await client.post(
                f"{sb_url}/rest/v1/early_access_signups",
                headers=headers,
                json={
                    "email": None,
                    "whatsapp": whatsapp.strip() or None,
                    "location": location.strip() or None,
                    "source": f"{source} [{name.strip()}] {chat_summary[:100]}",
                },
            )
            if resp2.status_code in (200, 201):
                logger.info("Lead saved to early_access_signups (fallback) | name=%s", name)
                saved = True
            else:
                logger.error("Both save attempts failed | cs_leads=%s | ea=%s", resp.status_code, resp2.status_code)

    if saved:
        await notify_peter(name, whatsapp, location, chat_summary)
        return "saved"
    return "save failed"


# ── WhatsApp handoff ──────────────────────────────────────────────────

async def whatsapp_handoff(name: str, whatsapp: str, detected_lang: str = "es", audience: str = "homeowner") -> str:
    from messaging.whatsapp import send_wa_message

    wa_to = whatsapp.strip().lstrip("+").replace(" ", "").replace("-", "")
    if not wa_to or len(wa_to) < 8:
        return "invalid_number"

    wa_target = PETER_PERSONAL_WA if audience == "agent" else LEO_WA_NUMBER
    target_label = "Peter" if audience == "agent" else "Leo"

    result = await send_wa_message(
        phone=wa_to,
        text=f"Hi {name.strip() or 'there'}, welcome to Leo on WhatsApp!",
        purpose="handoff",
        name=name.strip() or "there",
        template_params=[name.strip() or "there"],
    )

    if not result.ok:
        logger.warning("WhatsApp handoff failed | error=%s — falling back to wa.me link (audience=%s)", result.error, audience)
        prefill = f"Hola {target_label}! Soy {name.strip() or 'yo'} — vengo de la web \U0001f44b"
        wa_me = f"https://wa.me/{wa_target}?text={prefill.replace(' ', '%20')}"
        return (
            f"IMPORTANT: The template message could not be sent. "
            f"You MUST include this exact link in your reply so the user can tap it: {wa_me} "
            f"Do NOT say there was a problem. Just share the link naturally."
        )

    logger.info("WhatsApp handoff sent | to=%s | name=%s | audience=%s | via=%s", wa_to, name, audience, result.method)

    sb_url, sb_key = _get_supabase()
    if sb_url and sb_key:
        try:
            async with http_client(timeout=10) as client:
                await client.post(
                    f"{sb_url}/rest/v1/whatsapp_user_profiles",
                    headers={
                        "Content-Type": "application/json",
                        "apikey": sb_key,
                        "Authorization": f"Bearer {sb_key}",
                        "Prefer": "resolution=merge-duplicates",
                    },
                    json={
                        "phone_number": f"+{wa_to}",
                        "display_name": name.strip() or None,
                        "memory_summary": "web_handoff from leo.casa chat",
                        "message_count": 0,
                    },
                )
        except Exception as exc:
            logger.warning("Profile upsert for handoff failed (non-fatal) | %s", exc)

    return "sent"


# ── Skill proposals (agent self-improvement) ──────────────────────────

def proposal_short_id(proposal_uuid: str) -> str:
    """First 8 hex chars of UUID (no dashes) for founder WhatsApp replies."""
    return (proposal_uuid or "").replace("-", "").lower()[:8]


async def store_skill_proposal(
    skill_name: str,
    action: str,
    reason: str,
    content: str = "",
    conversation_id: str = "",
    skill_payload: Optional[Dict[str, Any]] = None,
) -> dict:
    """Store a skill change proposal and return the row (including id)."""
    sb_url, sb_key = _get_supabase()
    if not sb_url or not sb_key:
        logger.error("Supabase credentials missing for store_skill_proposal")
        return {"ok": False, "error": "db_not_configured"}

    # Check for similar draft/pending proposals to cluster
    similar = await get_similar_proposals(skill_name, action)
    pattern_count = 1
    similar_ids: List[str] = []
    for s in similar:
        similar_ids.append(str(s.get("id", "")))
        pattern_count = max(pattern_count, (s.get("pattern_count") or 0) + 1)

    row = {
        "skill_name": skill_name,
        "action": action,
        "reason": reason,
        "content": content[:10000] if content else None,
        "skill_payload": skill_payload if skill_payload else {},
        "status": "pending",
        "pattern_count": pattern_count,
        "similar_proposals": similar_ids if similar_ids else [],
        "conversation_id": conversation_id or None,
    }

    try:
        async with http_client(timeout=10) as client:
            resp = await client.post(
                f"{sb_url}/rest/v1/agent_skill_proposals",
                headers={
                    "Content-Type": "application/json",
                    "apikey": sb_key,
                    "Authorization": f"Bearer {sb_key}",
                    "Prefer": "return=representation",
                },
                json=row,
            )
            if resp.status_code in (200, 201):
                rows = resp.json()
                stored = rows[0] if isinstance(rows, list) and rows else rows
                logger.info(
                    "Skill proposal stored | skill=%s action=%s pattern_count=%d",
                    skill_name, action, pattern_count,
                )
                return {"ok": True, "id": stored.get("id"), "pattern_count": pattern_count}
            logger.error("Skill proposal insert failed | status=%s body=%s", resp.status_code, resp.text[:200])
            return {"ok": False, "error": f"insert_failed_{resp.status_code}"}
    except Exception as exc:
        logger.error("Skill proposal store error | %s", exc, exc_info=True)
        return {"ok": False, "error": str(exc)}


async def get_similar_proposals(skill_name: str, action: str) -> list:
    """Find existing draft/pending proposals for the same skill and action."""
    sb_url, sb_key = _get_supabase()
    if not sb_url or not sb_key:
        return []
    try:
        async with http_client(timeout=8) as client:
            resp = await client.get(
                f"{sb_url}/rest/v1/agent_skill_proposals",
                params={
                    "skill_name": f"eq.{skill_name}",
                    "action": f"eq.{action}",
                    "status": "in.(pending,draft)",
                    "select": "id,pattern_count,reason,created_at",
                    "order": "created_at.desc",
                    "limit": "10",
                },
                headers={
                    "apikey": sb_key,
                    "Authorization": f"Bearer {sb_key}",
                },
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.debug("get_similar_proposals error (non-fatal) | %s", exc)
    return []


async def resolve_skill_proposal(proposal_id: str, status: str) -> bool:
    """Update a proposal's status to approved/rejected/draft."""
    sb_url, sb_key = _get_supabase()
    if not sb_url or not sb_key:
        return False
    try:
        from datetime import datetime, timezone
        payload: Dict[str, Any] = {"status": status}
        if status == "draft":
            payload["resolved_at"] = None
        else:
            payload["resolved_at"] = datetime.now(timezone.utc).isoformat()
        async with http_client(timeout=8) as client:
            resp = await client.patch(
                f"{sb_url}/rest/v1/agent_skill_proposals?id=eq.{proposal_id}",
                headers={
                    "Content-Type": "application/json",
                    "apikey": sb_key,
                    "Authorization": f"Bearer {sb_key}",
                    "Prefer": "return=minimal",
                },
                json=payload,
            )
            if resp.status_code in (200, 204):
                logger.info("Skill proposal resolved | id=%s status=%s", proposal_id[:8], status)
                return True
            logger.warning("Skill proposal resolve failed | status=%s", resp.status_code)
    except Exception as exc:
        logger.warning("Skill proposal resolve error | %s", exc)
    return False


async def notify_founder_skill_proposal(
    proposal_id: str,
    skill_name: str,
    action: str,
    reason: str,
    pattern_count: int = 1,
    content_preview: str = "",
) -> bool:
    """Send Peter a WhatsApp message about a skill change proposal."""
    from messaging.whatsapp import send_wa_message

    short = proposal_short_id(str(proposal_id))
    pattern_note = ""
    if pattern_count > 1:
        pattern_note = f"\n\n_I've seen this gap {pattern_count} times now._"

    preview = ""
    if (content_preview or "").strip():
        preview = f"\n\n_Preview:_\n{(content_preview.strip())[:900]}"

    body = (
        f"\U0001f9e0 *Skill proposal*  _ref {short}_\n\n"
        f"*{action.upper()}:* {skill_name}\n"
        f"*Why:* {reason[:500]}"
        f"{pattern_note}{preview}\n\n"
        f"Reply with:\n"
        f"• *yes {short}* (or just *yes* for latest)\n"
        f"• *no {short}*\n"
        f"• *wait {short}* — draft for later"
    )

    try:
        for recipient in (PETER_WA, PETER_PERSONAL_WA):
            await send_wa_message(recipient, body, purpose="internal", do_store=False, skip_window_check=True)
        logger.info("Founder notified about skill proposal | skill=%s id=%s", skill_name, proposal_id[:8])
        return True
    except Exception as exc:
        logger.warning("Founder skill notification error | %s", exc)
        return False


async def send_whatsapp_text(to_digits: str, body: str) -> bool:
    """Send a plain text WhatsApp message. Delegates to unified send_wa_message."""
    from messaging.whatsapp import send_wa_message
    result = await send_wa_message(to_digits, body, purpose="internal", do_store=False, skip_window_check=True)
    return result.ok


async def fetch_pending_skill_proposals(limit: int = 40) -> list:
    sb_url, sb_key = _get_supabase()
    if not sb_url or not sb_key:
        return []
    try:
        async with http_client(timeout=10) as client:
            resp = await client.get(
                f"{sb_url}/rest/v1/agent_skill_proposals",
                params={
                    "status": "eq.pending",
                    "select": "*",
                    "order": "created_at.desc",
                    "limit": str(limit),
                },
                headers={"apikey": sb_key, "Authorization": f"Bearer {sb_key}"},
            )
            if resp.status_code == 200:
                return resp.json() or []
    except Exception as exc:
        logger.warning("fetch_pending_skill_proposals | %s", exc)
    return []


async def fetch_skill_proposal_by_id(proposal_id: str) -> Optional[dict]:
    sb_url, sb_key = _get_supabase()
    if not sb_url or not sb_key or not proposal_id:
        return None
    try:
        async with http_client(timeout=8) as client:
            resp = await client.get(
                f"{sb_url}/rest/v1/agent_skill_proposals",
                params={
                    "id": f"eq.{proposal_id}",
                    "select": "*",
                    "limit": "1",
                },
                headers={"apikey": sb_key, "Authorization": f"Bearer {sb_key}"},
            )
            if resp.status_code == 200:
                rows = resp.json() or []
                return rows[0] if rows else None
    except Exception as exc:
        logger.warning("fetch_skill_proposal_by_id | %s", exc)
    return None


async def resolve_proposal_for_founder(short_opt: Optional[str]) -> Optional[dict]:
    """Pick the pending proposal matching ref prefix, or latest pending if short_opt is empty."""
    pending = await fetch_pending_skill_proposals()
    if not pending:
        return None
    if short_opt:
        s = short_opt.lower().strip()
        for row in pending:
            if proposal_short_id(str(row.get("id", ""))) == s:
                return row
        return None
    return pending[0]


def execute_skill_manage_from_row(row: Dict[str, Any]) -> str:
    """Apply an approved proposal by calling Hermes skill_manage (sync)."""
    from messaging.frameworks import get_adapter
    skill_manage = get_adapter("skill_manager.skill_manage")

    action = (row.get("action") or "").strip()
    name = (row.get("skill_name") or "").strip()
    payload = row.get("skill_payload") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {}
    content = row.get("content")

    kw: Dict[str, Any] = {"action": action, "name": name}
    if action in ("create", "edit"):
        kw["content"] = (content or "") if content is not None else ""
    elif action == "patch":
        kw["old_string"] = payload.get("old_string") or ""
        kw["new_string"] = payload.get("new_string", "")
        if payload.get("file_path"):
            kw["file_path"] = payload["file_path"]
        kw["replace_all"] = bool(payload.get("replace_all", False))
    elif action == "write_file":
        kw["file_path"] = payload.get("file_path") or ""
        kw["file_content"] = payload.get("file_content") or ""
    elif action == "remove_file":
        kw["file_path"] = payload.get("file_path") or ""
    elif action == "delete":
        pass
    if action == "create" and payload.get("category"):
        kw["category"] = payload["category"]

    return skill_manage(**kw)


def parse_founder_skill_reply(text: str) -> Optional[Tuple[str, Optional[str]]]:
    """
    Parse founder WhatsApp reply. Returns (verb, optional_ref) where verb is
    approve | reject | draft. Ref is 8-char hex prefix when provided.
    """
    raw = (text or "").strip().lower()
    raw = raw.replace("*", "").replace("“", "").replace("”", "").strip()
    if not raw or len(raw) > 120:
        return None
    if raw.startswith("not yet"):
        tail = raw[7:].strip().split()
        ref_ny: Optional[str] = None
        if tail and re.match(r"^[a-f0-9]+$", tail[0]) and len(tail[0]) <= 8:
            ref_ny = tail[0]
        return ("draft", ref_ny)
    parts = raw.split()
    head = parts[0]
    ref: Optional[str] = None
    if len(parts) >= 2 and len(parts[1]) <= 8 and re.match(r"^[a-f0-9]+$", parts[1]):
        ref = parts[1]
    if head in ("yes", "approve", "ok", "yep", "apply"):
        return ("approve", ref)
    if head in ("no", "reject", "nope", "deny"):
        return ("reject", ref)
    if head in ("wait", "draft", "hold", "later", "pause", "not"):
        if head == "not" and len(parts) >= 3 and parts[1] == "yet":
            return ("draft", ref)
        if head == "not":
            return None
        return ("draft", ref)
    return None


async def try_handle_founder_skill_reply(sender_digits: str, text: str) -> Tuple[bool, str]:
    """
    If sender is founder and text is a skill decision, apply it.
    Returns (handled, message_to_echo) — message_to_echo is sent back to founder on WhatsApp.
    """
    clean = sender_digits.lstrip("+").replace(" ", "").replace("-", "")
    if clean not in FOUNDER_WA_DIGITS:
        return False, ""

    parsed = parse_founder_skill_reply(text)
    if not parsed:
        return False, ""

    verb, ref = parsed
    row = await resolve_proposal_for_founder(ref)
    if not row:
        return True, "No pending skill proposal matched. If you meant something else, ignore this — your next message goes to Leo as normal."

    pid = str(row.get("id", ""))
    if verb == "reject":
        await resolve_skill_proposal(pid, "rejected")
        return True, f"Rejected proposal {proposal_short_id(pid)}. Skipped applying skill_manage."

    if verb == "draft":
        await resolve_skill_proposal(pid, "draft")
        return True, f"Marked {proposal_short_id(pid)} as draft. I'll cluster similar ideas before asking again."

    # approve
    try:
        result = await asyncio.to_thread(execute_skill_manage_from_row, row)
    except Exception as exc:
        logger.exception("execute_skill_manage_from_row failed | %s", exc)
        await resolve_skill_proposal(pid, "rejected")
        return True, f"Apply failed (marked rejected): {exc!s}"[:900]

    await resolve_skill_proposal(pid, "approved")
    tail = (result or "")[:1200]
    return True, f"Approved {proposal_short_id(pid)}. skill_manage result:\n{tail}"


async def notify_founder_improvement_signal(signal_text: str, conversation_id: str) -> None:
    """WhatsApp Peter when the agent flagged IMPROVEMENT_SIGNAL (non-customer-facing)."""
    from messaging.whatsapp import send_wa_message

    if not (signal_text or "").strip():
        return
    body = (
        f"\U0001f6a8 *Improvement signal*\n"
        f"_conv:_ {(conversation_id or '')[:40]}\n\n"
        f"{signal_text.strip()[:2000]}"
    )
    try:
        for recipient in (PETER_WA, PETER_PERSONAL_WA):
            await send_wa_message(recipient, body, purpose="internal", do_store=False, skip_window_check=True)
        logger.info("Founder notified | improvement signal | conv=%s", (conversation_id or "")[:12])
    except Exception as exc:
        logger.warning("notify_founder_improvement_signal | %s", exc)


async def request_human_escalation(
    reason: str,
    conversation_summary: str,
    user_name: str = "",
    user_phone: str = "",
    channel: str = "whatsapp",
) -> dict:
    """Escalate a conversation to Peter. Sends him a WhatsApp alert with context
    and returns a wa.me link to share with the user."""
    token = _wa_token()
    phone_id = _wa_phone_id()

    lines = ["\U0001f6a8 *Human escalation requested*"]
    if user_name:
        lines.append(f"*User:* {user_name}")
    if user_phone:
        lines.append(f"\U0001f4f1 {user_phone}")
    lines.append(f"*Channel:* {channel}")
    lines.append(f"\n*Reason:* {reason}")
    if conversation_summary:
        lines.append(f"\n*Context:*\n{conversation_summary[:1500]}")

    body = "\n".join(lines)
    notified = False

    try:
        from messaging.whatsapp import send_wa_message
        for recipient in (PETER_WA, PETER_PERSONAL_WA):
            result = await send_wa_message(recipient, body, purpose="internal", do_store=False, skip_window_check=True)
            if result.ok:
                notified = True
        if notified:
            logger.info("Human escalation sent to Peter | reason=%s user=%s", reason[:60], user_name or user_phone or "unknown")
    except Exception as exc:
        logger.warning("Human escalation WhatsApp error | %s", exc)

    prefill = urllib.parse.quote(f"Hi Peter — Leo suggested I reach out. {reason[:100]}")
    wa_me_link = f"https://wa.me/{PETER_PERSONAL_WA}?text={prefill}"

    # Store in Supabase for tracking
    sb_url, sb_key = _get_supabase()
    if sb_url and sb_key:
        try:
            async with http_client(timeout=10) as client:
                await client.post(
                    f"{sb_url}/rest/v1/cs_leads",
                    headers={
                        "Content-Type": "application/json",
                        "apikey": sb_key,
                        "Authorization": f"Bearer {sb_key}",
                        "Prefer": "return=minimal",
                    },
                    json={
                        "name": user_name or None,
                        "whatsapp": user_phone or None,
                        "source": "human_escalation",
                        "chat_summary": f"ESCALATION: {reason}\n\n{conversation_summary[:2000]}",
                    },
                )
        except Exception as exc:
            logger.debug("Escalation lead store failed (non-fatal) | %s", exc)

    return {
        "ok": True,
        "notified": notified,
        "wa_me_link": wa_me_link,
        "peter_phone_display": "+34 627 506 263",
    }


async def send_email_resend(
    to: str,
    subject: str,
    body_html: str,
    body_text: str = "",
    from_label: str = "Leo",
    from_address: str = "project-agent@projects.leo.casa",
) -> dict:
    """Send an email via Resend API. Returns {"ok": True, "id": ...} or {"ok": False, "error": ...}."""
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        for line in open("/root/leo/.env.local").readlines():
            line = line.strip()
            if line.startswith("RESEND_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"')
                break
    if not api_key:
        logger.error("send_email_resend: RESEND_API_KEY not found")
        return {"ok": False, "error": "resend_api_key_missing"}

    payload = {
        "from": f"{from_label} <{from_address}>",
        "to": to,
        "subject": subject,
        "html": body_html,
    }
    if body_text:
        payload["text"] = body_text

    try:
        async with http_client(timeout=20) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                logger.info("Email sent via Resend | to=%s subject=%s id=%s", to, subject[:40], data.get("id"))
                return {"ok": True, "id": data.get("id")}
            logger.warning("Resend API error | status=%s body=%s", resp.status_code, resp.text[:300])
            return {"ok": False, "error": f"resend_{resp.status_code}", "detail": resp.text[:300]}
    except Exception as exc:
        logger.error("send_email_resend exception | %s", exc, exc_info=True)
        return {"ok": False, "error": str(exc)}


async def patch_lead_structured(
    *,
    phone: str,
    brief: Optional[Dict[str, Any]] = None,
    profile: Optional[Dict[str, Any]] = None,
    supabase_url: str = "",
    supabase_key: str = "",
) -> None:
    sb_url = supabase_url or ""
    sb_key = supabase_key or ""
    if not sb_url or not sb_key:
        sb_url, sb_key = _get_supabase()
    if not sb_url or not sb_key or not phone:
        return
    clean = phone.strip()
    if not clean:
        return

    blob: Dict[str, Any] = {}
    if brief:
        blob["brief"] = brief
    if profile:
        blob["profile"] = profile
    if not blob:
        return

    marker = "\n\n---LEO_STRUCTURED---\n"
    payload_json = json.dumps(blob, ensure_ascii=False)[:3500]

    headers = {
        "Content-Type": "application/json",
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Prefer": "return=representation",
    }

    # Fetch latest chat_summary for this phone
    try:
        async with http_client(timeout=12) as client:
            sel = urllib.parse.quote(
                "id,name,whatsapp,location,chat_summary,audience",
                safe="",
            )
            or_q = urllib.parse.quote(
                f"(whatsapp.eq.{clean},whatsapp.eq.+{clean.lstrip('+')},whatsapp.eq.{clean.lstrip('+')})",
                safe="",
            )
            url = f"{sb_url}/rest/v1/cs_leads?select={sel}&or={or_q}&order=created_at.desc&limit=1"
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.debug("patch_lead_structured fetch failed | %s", resp.status_code)
                return
            rows = resp.json()
            if not rows:
                logger.debug("patch_lead_structured | no cs_leads row for phone=%s", clean[:8])
                return
            row = rows[0]
            rid = row.get("id")
            prev = (row.get("chat_summary") or "").strip()
            if marker in prev:
                base = prev.split(marker)[0].strip()
            else:
                base = prev
            new_summary = (base + marker + payload_json).strip()[:4000]

            wa_filter = urllib.parse.quote(clean, safe="")
            if rid is not None:
                patch_url = f"{sb_url}/rest/v1/cs_leads?id=eq.{rid}"
            else:
                patch_url = f"{sb_url}/rest/v1/cs_leads?whatsapp=eq.{wa_filter}"
            pr = await client.patch(
                patch_url,
                headers={**headers, "Prefer": "return=minimal"},
                json={"chat_summary": new_summary},
            )
            if pr.status_code in (200, 204):
                logger.info("patch_lead_structured | updated cs_leads id=%s", rid)
            else:
                logger.warning("patch_lead_structured patch failed | %s | %s", pr.status_code, pr.text[:200])
    except Exception as exc:
        logger.warning("patch_lead_structured error (non-fatal) | %s", exc, exc_info=True)
