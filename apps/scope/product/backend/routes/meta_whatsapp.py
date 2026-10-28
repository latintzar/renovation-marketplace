"""
Meta WhatsApp Cloud API — Webhook & Proxy Chat
================================================

Pure proxy: receives WhatsApp messages, stores in Supabase, serves them to the
Leo Copilot app.  App sends messages via /api/copilot/send, which forwards to
Meta Cloud API.  **No AI agent processing.**

Media files are saved to MEDIA_DIR on the Hetzner server and served via
GET /api/media/whatsapp/{filename}.

Endpoints:
  GET  /api/webhooks/meta-whatsapp          — Meta webhook verification
  POST /api/webhooks/meta-whatsapp          — Receive inbound WhatsApp messages
  GET  /api/copilot/conversations           — List conversations
  GET  /api/copilot/messages/{phone}        — Get messages for a phone
  POST /api/copilot/send                    — Send message (app → WhatsApp)
  POST /api/copilot/upload-voice            — Upload voice note, send via Meta
  GET  /api/media/whatsapp/{filename}       — Serve stored media files
"""

import asyncio
import json
import logging
import os
import pathlib
import re
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core import http_client
from fastapi import APIRouter, Query, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from core import (
    check_supabase_health as _db_check_health,
    close_supabase_pool as _db_close_pool,
)
from core import bedrock_client

logger = logging.getLogger(__name__)

router = APIRouter()

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", '')
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
META_API_VERSION = "v23.0"
META_API_BASE = f"https://graph.facebook.com/{META_API_VERSION}"

MEDIA_DIR = pathlib.Path(__file__).resolve().parent.parent / "media" / "whatsapp"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

PUBLIC_MEDIA_BASE = "http://127.0.0.1:18261/api/media/whatsapp"

MIME_TO_EXT: Dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "video/mp4": "mp4",
    "video/3gpp": "3gp",
    "audio/ogg": "ogg",
    "audio/ogg; codecs=opus": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/aac": "aac",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
}


# ── Markdown → WhatsApp formatting ────────────────────────────────

_MD_BOLD = re.compile(r"\*\*(.+?)\*\*")       # **text** → *text*
_MD_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")  # leftover single * after bold
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")  # [text](url) → text: url
_MD_HEADING = re.compile(r"^#{1,3}\s+", re.MULTILINE)
_MD_BULLET = re.compile(r"^[-*]\s+", re.MULTILINE)


def _markdown_to_whatsapp(text: str) -> str:
    """Convert common markdown to WhatsApp-native formatting."""
    text = _MD_BOLD.sub(r"*\1*", text)
    text = _MD_LINK.sub(r"\1: \2", text)
    text = _MD_HEADING.sub("", text)
    text = _MD_BULLET.sub("• ", text)
    return text.strip()


def _split_wa_reply(text: str, max_chars: int = 800) -> list[str]:
    """Split a long reply into natural WhatsApp-sized messages.

    Splits on double-newlines (paragraph breaks) first. If a paragraph is still
    too long, splits on single newlines. Each chunk stays under max_chars so
    messages feel short and natural.
    """
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    messages: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if current and len(current) + 2 + len(para) > max_chars:
            messages.append(current.strip())
            current = para
        elif not current:
            current = para
        else:
            current += "\n\n" + para

    if current.strip():
        messages.append(current.strip())

    final: list[str] = []
    for msg in messages:
        if len(msg) <= max_chars + 200:
            final.append(msg)
        else:
            lines = msg.split("\n")
            chunk = ""
            for line in lines:
                if chunk and len(chunk) + 1 + len(line) > max_chars:
                    final.append(chunk.strip())
                    chunk = line
                else:
                    chunk = chunk + "\n" + line if chunk else line
            if chunk.strip():
                final.append(chunk.strip())

    return final if final else [text[:max_chars]]


# ── Inbound debounce ────────────────────────────────────────────────
# When a user sends a burst of short messages (common on WhatsApp), we
# accumulate them over a short window then fire one agent call with the
# combined text.  This prevents N separate Hermes calls for N rapid messages.

DEBOUNCE_WINDOW_SECS = 4.0
# Post-reply cooldown: after the bot sends a reply, wait this long before
# processing new messages. This catches the common pattern where the user
# sends a follow-up within seconds of receiving the bot's reply.
POST_REPLY_COOLDOWN_SECS = 3.0

_debounce_buffers: Dict[str, list] = {}      # phone -> list of message dicts
_seen_wa_msg_ids: Dict[str, float] = {}      # wa_msg_id -> timestamp (dedup Meta retries)
_debounce_timers: Dict[str, asyncio.Task] = {}  # phone -> pending asyncio task
_last_reply_ts: Dict[str, float] = {}        # phone -> unix timestamp of last bot reply sent

# Per-phone processing lock — prevents overlapping Hermes calls.
# When a call is in flight, new messages queue up and fire after it completes.
_phone_locks: Dict[str, asyncio.Lock] = {}

def _get_phone_lock(phone: str) -> asyncio.Lock:
    if phone not in _phone_locks:
        _phone_locks[phone] = asyncio.Lock()
    return _phone_locks[phone]

# Outbound "undo-send" delay — feels human, prevents instant-bot responses
SEND_BUFFER_SECS = 0.8

# Founder's personal numbers — get a debug footer on WhatsApp replies
FOUNDER_DEBUG_PHONES = {"00000000000", "34627506263"}

# Max age (seconds) to look back for orphaned messages on startup
ORPHAN_REPLAY_WINDOW_SECS = 600  # 10 minutes


async def retry_orphaned_messages() -> int:
    """
    Called on server startup. Finds user messages that never got a reply
    (server died mid-processing) and replays them.
    Returns count of retried conversations.
    """
    try:
        sb_client = await database.get_client()
        sb_base = database._get_base_url()

        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=ORPHAN_REPLAY_WINDOW_SECS)).isoformat()

        # Get recent messages within the replay window, newest first
        resp = await sb_client.get(
            f"{sb_base}/whatsapp_messages",
            params={
                "select": "phone_number,role,message_text,created_at",
                "created_at": f"gte.{cutoff}",
                "order": "created_at.desc",
                "limit": "200",
            },
            headers=database._get_headers(),
        )
        if resp.status_code != 200:
            logger.warning("Orphan check failed | status=%s", resp.status_code)
            return 0

        rows = resp.json()
        if not rows:
            return 0

        # Group by phone, find conversations where the most recent message is from the user
        phones_seen: Dict[str, dict] = {}
        for row in rows:
            phone = row["phone_number"]
            if phone not in phones_seen:
                phones_seen[phone] = row  # newest message for this phone

        orphans = []
        for phone, newest in phones_seen.items():
            if newest["role"] == "user" and newest.get("message_text", "").strip():
                orphans.append((phone, newest["message_text"]))

        if not orphans:
            logger.info("Orphan check: no unreplied messages found")
            return 0

        logger.info("Orphan check: found %d unreplied conversations, replaying...", len(orphans))

        retried = 0
        for phone, last_text in orphans:
            try:
                # Look up display name from user profiles
                name = "Unknown"
                try:
                    name_resp = await sb_client.get(
                        f"{sb_base}/whatsapp_user_profiles",
                        params={"phone_number": f"eq.{phone}", "select": "display_name", "limit": "1"},
                        headers=database._get_headers(),
                    )
                    if name_resp.status_code == 200 and name_resp.json():
                        name = name_resp.json()[0].get("display_name", "Unknown")
                except Exception:
                    pass

                logger.info("Orphan replay | phone=%s | text=%s", phone, last_text[:60])
                asyncio.create_task(_auto_reply_wa(
                    phone=phone,
                    contact_name=name,
                    user_text=last_text,
                ))
                retried += 1
            except Exception as exc:
                logger.error("Orphan replay failed | phone=%s | err=%s", phone, exc)

        return retried

    except Exception as exc:
        logger.error("Orphan check failed | err=%s", exc, exc_info=True)
        return 0


async def _debounce_reply(phone: str, contact_name: str, msg: dict) -> None:
    """
    Buffer an inbound message.  After DEBOUNCE_WINDOW_SECS of quiet from
    this phone, fire one _auto_reply_wa with all accumulated messages merged.
    Typing indicator fires immediately on the first message so the user
    sees feedback during the debounce wait.
    """
    is_first = phone not in _debounce_buffers or not _debounce_buffers[phone]
    _debounce_buffers.setdefault(phone, []).append(msg)

    # Show typing indicator immediately on the first message in a burst —
    # slight 0.3s delay to feel human, then it shows for up to 25s
    if is_first and msg.get("wa_msg_id"):
        async def _delayed_typing():
            await asyncio.sleep(0.3)
            await _send_typing_indicator(msg["wa_msg_id"])
        asyncio.create_task(_delayed_typing())

    existing = _debounce_timers.get(phone)
    if existing and not existing.done():
        existing.cancel()

    async def _fire():
        await asyncio.sleep(DEBOUNCE_WINDOW_SECS)
        msgs = _debounce_buffers.pop(phone, [])
        _debounce_timers.pop(phone, None)
        if not msgs:
            return

        combined_text_parts = []
        combined_media_urls = []
        combined_media_types = []
        last_wa_msg_id = ""
        msg_type = "text"

        for m in msgs:
            if m.get("text"):
                combined_text_parts.append(m["text"])
            if m.get("media_urls"):
                combined_media_urls.extend(m["media_urls"])
                combined_media_types.extend(m.get("media_types", []))
            if m.get("msg_type") and m["msg_type"] != "text":
                msg_type = m["msg_type"]
            if m.get("wa_msg_id"):
                last_wa_msg_id = m["wa_msg_id"]

        combined_text = "\n".join(combined_text_parts)
        if len(msgs) > 1:
            logger.info("Debounce merged %d messages from %s", len(msgs), phone)

        lock = _get_phone_lock(phone)
        async with lock:
            await _auto_reply_wa(
                phone, contact_name, combined_text,
                msg_type=msg_type,
                media_urls=combined_media_urls or None,
                media_types=combined_media_types or None,
                wa_msg_id=last_wa_msg_id,
            )

    _debounce_timers[phone] = asyncio.create_task(_fire())


# ─── helpers ────────────────────────────────────────────────────────

def _get_token() -> str:
    return os.getenv("WHATSAPP_TOKEN", "") or WHATSAPP_TOKEN


def _get_phone_id() -> str:
    return os.getenv("WHATSAPP_PHONE_NUMBER_ID", "") or PHONE_NUMBER_ID


async def _download_meta_media(media_id: str) -> Optional[Dict[str, str]]:
    """
    Download a media file from Meta Cloud API, save it to MEDIA_DIR,
    and return {"url": public_url, "mime": mime_type, "filename": fname}.
    Returns None on any failure.
    """
    token = _get_token()
    if not token or not media_id:
        return None

    try:
        async with http_client(timeout=30) as client:
            meta_resp = await client.get(
                f"{META_API_BASE}/{media_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if meta_resp.status_code != 200:
                logger.warning("Meta media lookup failed | id=%s | status=%s", media_id, meta_resp.status_code)
                return None

            info = meta_resp.json()
            download_url = info.get("url")
            mime_type = info.get("mime_type", "application/octet-stream")
            if not download_url:
                return None

            bin_resp = await client.get(
                download_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            if bin_resp.status_code != 200:
                logger.warning("Meta media download failed | id=%s | status=%s", media_id, bin_resp.status_code)
                return None

            ext = MIME_TO_EXT.get(mime_type.split(";")[0].strip(), "bin")
            fname = f"{uuid.uuid4().hex[:12]}.{ext}"
            fpath = MEDIA_DIR / fname
            fpath.write_bytes(bin_resp.content)

            public_url = f"{PUBLIC_MEDIA_BASE}/{fname}"
            logger.info(
                "Saved media | id=%s | mime=%s | size=%d bytes | file=%s",
                media_id, mime_type, len(bin_resp.content), fname,
            )
            return {"url": public_url, "mime": mime_type, "filename": fname}

    except Exception as exc:
        logger.error("Media download exception | id=%s | err=%s", media_id, exc)
        return None


async def _store_message(
    phone_number: str,
    role: str,
    text: str,
    message_type: str = "text",
    media_urls: Optional[List[str]] = None,
    media_types: Optional[List[str]] = None,
    wa_message_id: Optional[str] = None,
    reply_to_wa_id: Optional[str] = None,
    reply_to_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert a message into whatsapp_messages via Supabase REST.
    Delegates to the unified send_wa.store_message() function."""
    from messaging import store_message
    return await store_message(
        phone_number=phone_number,
        role=role,
        text=text,
        message_type=message_type,
        media_urls=media_urls,
        media_types=media_types,
        wa_message_id=wa_message_id,
        reply_to_wa_id=reply_to_wa_id,
        reply_to_text=reply_to_text,
    )


# ─── Post-onboarding WhatsApp (landing lead phone submit) ───────────

WHATSAPP_TEMPLATE_HOMEOWNER = os.getenv("WHATSAPP_TEMPLATE_HOMEOWNER", "leo_homeowner_welcome_v1")
WHATSAPP_TEMPLATE_PROFESSIONAL = os.getenv("WHATSAPP_TEMPLATE_PROFESSIONAL", "leo_pro_welcome_v1")
# Short confirmation template that just asks for a reply — opens the 24-hour free messaging window
# Template body: "Hi {{1}}, we've received your {{2}} on Leo. Reply to confirm you got this!"
WHATSAPP_TEMPLATE_RECEIVED = os.getenv("WHATSAPP_TEMPLATE_RECEIVED", "leo_received_v1")


def _onboarding_body_text(
    audience: str,
    display_name: str,
    locale: str,
    location_suffix: str,
) -> str:
    """
    Short confirmation copy for the first WhatsApp message after phone capture.
    Goal: get the user to reply (opens 24-hour free messaging window).
    Rich follow-up details are sent by Hermes when the user replies.
    """
    name = (display_name or "").strip() or ("there" if (locale or "").lower().startswith("en") else "")
    es = (locale or "").lower().startswith("es")
    if audience == "professional":
        if es:
            return (
                f"Hola{' ' + name if name else ''}, hemos recibido tu perfil en Leo. "
                f"Responde a este mensaje para confirmar que te ha llegado y te cuento los próximos pasos."
                f"\n\n— Leo · leo.casa"
            )
        return (
            f"Hi{' ' + name if name else ''}, we've received your profile on Leo. "
            f"Reply to this message to confirm you got it and I'll walk you through what's next."
            f"\n\n— Leo · leo.casa"
        )
    if es:
        return (
            f"Hola{' ' + name if name else ''}, hemos recibido tu solicitud en Leo. "
            f"Responde a este mensaje para confirmar que te ha llegado y te cuento los próximos pasos."
            f"\n\n— Leo · leo.casa"
        )
    return (
        f"Hi{' ' + name if name else ''}, we've received your job request on Leo. "
        f"Reply to this message to confirm you got it and I'll walk you through what's next."
        f"\n\n— Leo · leo.casa"
    )


async def send_onboarding_wa_message(
    phone: str,
    audience: str,
    display_name: str,
    locale: str,
    location_suffix: str = "",
) -> bool:
    """First WhatsApp after user submits phone on the landing flow.
    Delegates to unified send_wa_message() for template/text routing.
    Stores outbound in whatsapp_messages and upserts whatsapp_user_profiles.
    """
    from messaging import send_wa_message

    clean_phone = phone.strip()
    if not clean_phone.startswith("+"):
        clean_phone = f"+{clean_phone.lstrip('+')}"

    body_text = _onboarding_body_text(audience, display_name, locale, location_suffix)
    name_for_template = (display_name or "").strip() or "there"
    lang_full = "es_ES" if (locale or "").lower().startswith("es") else "en_US"
    item_label = "perfil" if (audience == "professional" and lang_full == "es_ES") else (
        "profile" if audience == "professional" else (
            "solicitud" if lang_full == "es_ES" else "job request"
        )
    )

    result = await send_wa_message(
        phone=clean_phone,
        text=body_text,
        purpose="onboarding",
        name=name_for_template,
        template_params=[name_for_template, item_label],
        do_store=True,
    )

    if not result.ok:
        logger.error("send_onboarding_wa_message failed | phone=%s | error=%s", clean_phone[:16], result.error)
        return False

    logger.info("Onboarding WA sent | to=%s | via=%s", clean_phone[:16], result.method)

    mem = (
        "Onboarding: homeowner job request (leo.casa)"
        if audience != "professional"
        else "Onboarding: tradesperson profile (leo.casa)"
    )
    try:
        client = await database.get_client()
        base_url = database._get_base_url()
        await client.post(
            f"{base_url}/whatsapp_user_profiles",
            json={
                "phone_number": clean_phone,
                "display_name": name_for_template if name_for_template != "there" else None,
                "memory_summary": mem,
            },
            headers={**database._get_headers(), "Prefer": "resolution=merge-duplicates"},
        )
    except Exception as exc:
        logger.debug("whatsapp_user_profiles upsert failed (non-fatal) | %s", exc)

    return True


# ─── Auto-reply via CS agent ───────────────────────────────────────

async def _lookup_lead(phone: str) -> Optional[Dict[str, Any]]:
    """Look up a user in cs_leads by their WhatsApp number."""
    try:
        sb_client = await database.get_client()
        sb_base = database._get_base_url()
        clean = phone.lstrip("+").replace(" ", "").replace("-", "")
        resp = await sb_client.get(
            f"{sb_base}/cs_leads",
            params={
                "select": "name,whatsapp,location,chat_summary,audience",
                "or": f"(whatsapp.eq.{phone},whatsapp.eq.+{clean},whatsapp.eq.{clean})",
                "order": "created_at.desc",
                "limit": "1",
            },
            headers=database._get_headers(),
        )
        if resp.status_code == 200:
            rows = resp.json()
            if rows:
                logger.info("WA lead found | phone=%s | name=%s", phone, rows[0].get("name"))
                return rows[0]
    except Exception as exc:
        logger.debug("Lead lookup failed (non-fatal) | %s", exc)
    return None


async def _extract_contractor_voice_response(phone: str, transcript: str, voice_url: str = ""):
    """If this phone belongs to a contractor with an active job outreach,
    extract reaction/needs/availability from the transcript via LLM and update the response."""
    from routes.job_inbox import find_job_for_contractor_phone, update_response
    match = await find_job_for_contractor_phone(phone)
    if not match:
        return

    response_id = match.get("id")
    if not response_id:
        return

    try:
        client = bedrock_client("eu-west-1")
        prompt = f"""Extract structured information from this contractor's voice note response to a job inquiry.

Voice note transcript:
"{transcript}"

Return a JSON object with these fields (use empty string if not mentioned):
- "reaction": Their initial reaction to the project (interested? experienced? concerned?)
- "site_visit_needs": What they'd need to check on a site visit
- "availability": When they're available

Return ONLY the JSON object, no other text."""

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        })
        resp = client.invoke_model(modelId="eu.anthropic.claude-sonnet-4-20250514-v1:0", body=body)
        result_text = json.loads(resp["body"].read())["content"][0]["text"]

        start = result_text.find("{")
        end = result_text.rfind("}") + 1
        if start >= 0 and end > start:
            extracted = json.loads(result_text[start:end])
            updates = {
                "voice_note_url": voice_url,
                "voice_transcript": transcript,
                "reaction": extracted.get("reaction", ""),
                "site_visit_needs": extracted.get("site_visit_needs", ""),
                "availability": extracted.get("availability", ""),
                "outreach_stage": "voice_received",
            }
            await update_response(response_id, updates)
            logger.info("Contractor voice extracted | response=%s | reaction=%s",
                       response_id[:8], (extracted.get("reaction", ""))[:60])
    except Exception as e:
        logger.warning("Voice extraction LLM failed (non-fatal): %s", e)
        await update_response(response_id, {
            "voice_note_url": voice_url,
            "voice_transcript": transcript,
            "outreach_stage": "voice_received",
        })


async def _transcribe_local_file(fpath: pathlib.Path) -> str:
    """Transcribe an audio file — delegates to the unified enrich module."""
    from messaging import transcribe_file
    return await transcribe_file(fpath)


async def _send_typing_indicator(wa_msg_id: str) -> None:
    """Show 'typing...' in the user's WhatsApp chat for up to 25 seconds."""
    token = _get_token()
    phone_id = _get_phone_id()
    if not token or not phone_id or not wa_msg_id:
        return
    try:
        async with http_client(timeout=10) as client:
            resp = await client.post(
                f"{META_API_BASE}/{phone_id}/messages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "messaging_product": "whatsapp",
                    "status": "read",
                    "message_id": wa_msg_id,
                    "typing_indicator": {"type": "text"},
                },
            )
            if resp.status_code in (200, 201):
                logger.debug("Typing indicator sent | msg=%s", wa_msg_id[:20])
            else:
                logger.debug("Typing indicator failed | status=%s", resp.status_code)
    except Exception as exc:
        logger.debug("Typing indicator error (non-fatal) | %s", exc)


async def _auto_reply_wa(
    phone: str,
    contact_name: str,
    user_text: str,
    msg_type: str = "text",
    media_urls: Optional[List[str]] = None,
    media_types: Optional[List[str]] = None,
    wa_msg_id: str = "",
) -> None:
    """
    Fetch full conversation history, call the CS agent, and send the
    reply back via WhatsApp. Runs as a background task so the webhook
    responds quickly to Meta.

    Handles media: voice notes are transcribed, images sent as multimodal,
    documents have text extracted — so Hermes sees actual content, not placeholders.
    """
    try:
        from agent import whatsapp_reply as hermes_reply, _to_openai_messages
        from messaging import WHATSAPP_CAPABILITIES

        # Show "typing..." immediately so the user knows we're processing
        if wa_msg_id:
            await _send_typing_indicator(wa_msg_id)

        sb_client = await database.get_client()
        sb_base = database._get_base_url()

        lead = await _lookup_lead(phone)

        # ── Determine audience from lead data ─────────────────────
        audience = "homeowner"
        if lead and lead.get("audience"):
            aud_raw = str(lead["audience"]).strip().lower()
            if aud_raw in ("professional", "tradesperson", "pro"):
                audience = "professional"
            elif aud_raw == "agent":
                audience = "agent"
            else:
                audience = "homeowner"

        # ── Contractor intake detection ──────────────────────────
        # Check if this phone was contacted as part of a job outreach.
        # If so, treat as a contractor (professional audience) and inject job context.
        # Runs AFTER lead lookup so contractor detection can override audience.
        contractor_job_context = ""
        try:
            from routes.job_inbox import find_job_for_contractor_phone
            match = await find_job_for_contractor_phone(phone)
            if match:
                job = match.get("job", {})
                brief = job.get("brief", {})
                contractor_job_context = (
                    f"IMPORTANT: This person is a CONTRACTOR who was contacted about a job via Leo's outreach. "
                    f"Job: '{brief.get('title', 'home project')}' in {brief.get('location', 'their area')}. "
                    f"Brief: {brief.get('description', '')[:300]}. "
                    f"Your role: Share the job details, ask for a 30-second voice note "
                    f"(their reaction, what they'd need to check on a site visit, and their availability), "
                    f"and then send them the onboarding link: "
                    f"http://127.0.0.1:18260/app/onboard/pro?jobId={job.get('id', '')}&phone={phone}. "
                    f"Be friendly and professional. They are a potential contractor for a homeowner's project."
                )
                if not lead or not lead.get("audience"):
                    audience = "professional"
                logger.info("Contractor intake detected | phone=%s job=%s", phone[:8], job.get("id", "?")[:8])

                from routes.job_inbox import update_response as _update_resp_stage
                resp_id = match.get("id")
                current_stage = match.get("outreach_stage", "contacted") if "outreach_stage" in match else "contacted"
                if resp_id and current_stage in ("contacted", "delivered"):
                    try:
                        await _update_resp_stage(resp_id, {"outreach_stage": "replied"})
                    except Exception:
                        pass
        except Exception as e:
            logger.debug("Contractor job lookup failed (non-fatal): %s", e)

        # Build lead context string for the system prompt (NOT as a fake user message)
        lead_context = ""

        # ── Founder identity injection ───────────────────────────────
        # If this is the founder's number, inject identity so the agent never
        # treats Peter as an anonymous user or refers to him in third-person.
        wa_digits_for_ctx = phone.lstrip("+").replace("whatsapp:", "").replace(" ", "").replace("-", "")
        if wa_digits_for_ctx in FOUNDER_DEBUG_PHONES:
            lead_context = (
                "IMPORTANT: You are talking directly to Peter, the founder of Leo. "
                "He is not a homeowner or tradesperson — he is the person who built this product. "
                "Treat him as your operator. He may ask you to look up data, run tasks, check signups, "
                "query the database, or test features. Never refer to his phone number as a third-party "
                "or unknown user — you ARE talking to him directly. Be direct, efficient, and technical. "
                "Don't explain basics he already knows. Don't ask for his name or location."
            )
            audience = "founder"
        elif lead:
            context_parts = []
            if lead.get("name"):
                context_parts.append(f"name: {lead['name']}")
            if lead.get("location"):
                context_parts.append(f"location: {lead['location']}")
            if lead.get("chat_summary"):
                context_parts.append(f"prior context: {lead['chat_summary']}")
            context_parts.append(
                f"signup type: {'tradesperson' if audience == 'professional' else audience}"
            )
            if context_parts:
                lead_context = (
                    f"You already know this person: {'; '.join(context_parts)}. "
                    f"Don't re-ask for info you already have."
                )

        if contractor_job_context:
            lead_context = contractor_job_context + ("\n\n" + lead_context if lead_context else "")

        # Fetch ALL messages for this conversation (including media metadata)
        # Fetch RECENT messages only (not full history — that's what mem0 is for)
        MAX_WA_HISTORY = 30
        hist_resp = await sb_client.get(
            f"{sb_base}/whatsapp_messages",
            params={
                "phone_number": f"eq.{phone}",
                "select": "role,message_text,message_type,media_urls,media_types",
                "order": "created_at.desc",
                "limit": str(MAX_WA_HISTORY),
            },
            headers=database._get_headers(),
        )
        raw_msgs = []

        if hist_resp.status_code == 200:
            rows = hist_resp.json()
            rows.reverse()  # oldest first

            for row in rows:
                role = row.get("role", "user")
                txt = row.get("message_text", "").strip()
                if not txt:
                    continue

                # All media is already processed at ingest time:
                # - Voice notes → [Voice note]: transcript
                # - Images → [Photo]: structured analysis
                # - Documents → [Document: name]: extracted text
                # No need to re-load any media from disk. Text is the source of truth.
                raw_msgs.append({"role": role, "text": txt})

        # Ensure the current user message is at the end
        # user_text already contains the analyzed/transcribed content from ingest
        if raw_msgs:
            last_user_msgs = [m for m in raw_msgs if m["role"] == "user"]
            if not last_user_msgs or last_user_msgs[-1]["text"] != user_text:
                raw_msgs.append({"role": "user", "text": user_text})
        else:
            raw_msgs = [{"role": "user", "text": user_text}]

        # Ensure conversation starts with user role
        while raw_msgs and raw_msgs[0]["role"] != "user":
            raw_msgs.pop(0)
        if not raw_msgs:
            raw_msgs = [{"role": "user", "text": user_text}]

        logger.info("WA auto-reply | phone=%s | msgs=%d | first_role=%s | last_role=%s | user_text=%s",
                     phone, len(raw_msgs), raw_msgs[0]["role"] if raw_msgs else "?",
                     raw_msgs[-1]["role"] if raw_msgs else "?", user_text[:80])

        openai_msgs = _to_openai_messages(raw_msgs)
        if not openai_msgs:
            logger.warning("WA auto-reply | no valid openai msgs for %s | raw_count=%d", phone, len(raw_msgs))
            return

        # ── Enrichment signal (homeowner WhatsApp only) ───────────────
        # If the homeowner has an active job with enrichment_needed, inject it
        # so Hermes knows exactly what to ask for next (photos first, then details).
        enrichment_needed = None
        if audience == "homeowner":
            try:
                from routes.job_inbox import get_active_job_for_phone
                active_job = await get_active_job_for_phone(phone)
                if active_job:
                    enrichment_needed = active_job.get("enrichment_needed")
                    if enrichment_needed:
                        logger.debug(
                            "WA auto-reply | enrichment_needed injected | job=%s | priority=%s",
                            (active_job.get("id") or "?")[:8],
                            enrichment_needed.get("priority", "?"),
                        )
            except Exception as exc:
                logger.debug("WA auto-reply | enrichment lookup failed (non-fatal): %s", exc)

        result = await hermes_reply(
            openai_msgs,
            mode="whatsapp",
            raw_history=raw_msgs,
            lead_context=lead_context,
            audience=audience,
            lead_phone=phone,
            conversation_id=phone,
            capabilities=WHATSAPP_CAPABILITIES,
            enrichment_needed=enrichment_needed,
        )
        reply = result.get("reply", "")
        tool_activity = result.get("tool_activity", [])
        tokens_used = result.get("tokens", 0)
        cost_usd = result.get("cost_usd", 0)
        model_used = result.get("model_used", "")

        if not reply:
            logger.warning("WA auto-reply | empty reply for %s", phone)
            from messaging import send_wa_message as _send_wa_fallback
            try:
                await _send_wa_fallback(
                    phone=phone,
                    text="Sorry, I ran into a hiccup processing that. Could you try again?",
                    purpose="internal",
                    do_store=False,
                    skip_window_check=True,
                )
            except Exception:
                pass
            return

        # Refresh typing indicator before reply — the one from debounce may
        # have expired during long Hermes processing (voice transcription, search, etc.)
        if wa_msg_id:
            await _send_typing_indicator(wa_msg_id)

        reply_clean = _markdown_to_whatsapp(reply.strip())
        messages_to_send = _split_wa_reply(reply_clean)

        # Append debug footer for founder's numbers
        wa_to_raw = phone.replace("whatsapp:", "").lstrip("+")
        if wa_to_raw in FOUNDER_DEBUG_PHONES and messages_to_send:
            all_tools = result.get("all_tools_used", [])
            leo_tools = [t.get("tool", "?") for t in tool_activity]
            combined_tools = list(dict.fromkeys(all_tools or leo_tools))

            cost_status = result.get("cost_status", "unknown")
            cost_prefix = "~" if cost_status == "estimated" else ""
            cost_str = f"{cost_prefix}${cost_usd:.4f}" if cost_usd else None

            # Build a human-readable single-line footer
            parts = []
            if combined_tools:
                short_tools = [t.replace("_", " ") for t in combined_tools]
                parts.append(f"searched {', '.join(short_tools)}")
            if cost_str:
                parts.append(cost_str)

            if parts:
                footer = "\n_" + " · ".join(parts) + "_"
                messages_to_send[-1] += footer

        # Brief "undo-send" delay so replies feel human-paced
        await asyncio.sleep(SEND_BUFFER_SECS)

        wa_to_raw = phone.replace("whatsapp:", "").lstrip("+")

        sent_wa_id = ""
        from messaging import send_wa_message as _send_wa
        for i, msg_text in enumerate(messages_to_send):
            if not msg_text.strip():
                continue
            if i > 0:
                await asyncio.sleep(0.6)

            r = await _send_wa(
                phone=wa_to_raw,
                text=msg_text,
                purpose="internal",
                do_store=False,
                skip_window_check=True,
            )
            if r.ok:
                sent_wa_id = r.wa_message_id
            else:
                logger.error("WA auto-reply send failed | to=%s | error=%s", phone, r.error)
                break

        full_text = "\n\n".join(messages_to_send)
        logger.info("WA auto-reply sent | to=%s | parts=%d | wamid=%s | text=%s",
                     phone, len(messages_to_send), sent_wa_id, full_text[:80])

        await _store_message(
            phone_number=phone,
            role="assistant",
            text=full_text,
            wa_message_id=sent_wa_id,
        )

        # Mirror the Hermes reply to Chatwoot as an outgoing message so the full
        # conversation thread is visible in the inbox (founder chats included).
        try:
            from routes.chatwoot import push_message_to_chatwoot as _cw_push_reply
            asyncio.create_task(_cw_push_reply(phone, "Leo (auto)", full_text, "outgoing"))
        except Exception as _cw_exc:
            logger.debug("Chatwoot reply mirror failed (non-fatal) | %s", _cw_exc)

    except Exception as exc:
        logger.error("WA auto-reply failed | phone=%s | err=%s", phone, exc, exc_info=True)


# ─── Webhook verification (GET) ────────────────────────────────────

@router.get("/api/webhooks/meta-whatsapp")
async def meta_whatsapp_verify(
    request: Request,
) -> PlainTextResponse:
    """
    Meta sends a GET with hub.mode, hub.verify_token, hub.challenge.
    We echo back hub.challenge if the token matches.
    """
    params = dict(request.query_params)
    mode = params.get("hub.mode", "")
    token = params.get("hub.verify_token", "")
    challenge = params.get("hub.challenge", "")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Meta webhook verified")
        return PlainTextResponse(challenge, status_code=200)

    logger.warning("Meta webhook verification failed | mode=%s token_match=%s", mode, token == VERIFY_TOKEN)
    return PlainTextResponse("Forbidden", status_code=403)


# ─── Webhook receiver (POST) ───────────────────────────────────────

@router.post("/api/webhooks/meta-whatsapp")
async def meta_whatsapp_webhook(request: Request) -> JSONResponse:
    """
    Receive inbound WhatsApp messages from Meta Cloud API.
    Store in Supabase.  No AI processing — pure proxy.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    entry_list = payload.get("entry", [])
    for entry in entry_list:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})

            # Log status updates for debugging delivery issues
            statuses = value.get("statuses", [])
            if statuses:
                for st in statuses:
                    sid = st.get("id", "?")
                    status_val = st.get("status", "?")
                    recip = st.get("recipient_id", "?")
                    errors = st.get("errors", [])
                    err_str = f" | errors={errors}" if errors else ""
                    logger.info(
                        "Meta status update | wamid=%s | status=%s | recipient=%s%s",
                        sid, status_val, recip, err_str,
                    )

            if "messages" not in value:
                continue

            contacts = value.get("contacts", [])
            contact_name = contacts[0].get("profile", {}).get("name", "Unknown") if contacts else "Unknown"
            messages = value.get("messages", [])

            for msg in messages:
                from_number = msg.get("from", "")
                msg_type = msg.get("type", "text")
                wa_msg_id = msg.get("id", "")

                if not from_number:
                    continue

                # Dedup Meta webhook retries — same wa_msg_id means same message
                if wa_msg_id:
                    import time as _time_mod
                    now = _time_mod.time()
                    if wa_msg_id in _seen_wa_msg_ids:
                        logger.debug("Dedup: skipping already-seen wa_msg_id=%s", wa_msg_id[:16])
                        continue
                    _seen_wa_msg_ids[wa_msg_id] = now
                    # Prune old entries (keep last 10 minutes)
                    cutoff = now - 600
                    stale = [k for k, v in _seen_wa_msg_ids.items() if v < cutoff]
                    for k in stale:
                        _seen_wa_msg_ids.pop(k, None)

                phone = f"+{from_number}" if not from_number.startswith("+") else from_number

                # Extract reply context if this message is replying to another
                context = msg.get("context", {})
                reply_to_wa_id = context.get("id") if context else None

                text = ""
                media_urls: List[str] = []
                media_types: List[str] = []

                # --- Extract media_id and text for each type ---
                media_id: Optional[str] = None

                if msg_type == "text":
                    text = msg.get("text", {}).get("body", "")

                    # Extract links at ingest — if the text contains URLs, fetch and
                    # summarize the content so the agent never needs to re-fetch.
                    if text and ("http://" in text or "https://" in text):
                        import re as _re_urls
                        from messaging import parse_url
                        urls = _re_urls.findall(r'https?://[^\s<>"\'\\]+', text)
                        for url in urls[:2]:
                            try:
                                extracted = await parse_url(url)
                                if extracted:
                                    text += f"\n\n[Link content from {url}]:\n{extracted}"
                                    logger.info("WA ingest URL extracted | url=%s | chars=%d", url[:60], len(extracted))
                            except Exception as url_exc:
                                logger.debug("URL extraction failed at ingest (non-fatal) | %s | %s", url[:60], url_exc)

                elif msg_type == "image":
                    media_id = msg.get("image", {}).get("id")
                    text = msg.get("image", {}).get("caption", "") or ""

                elif msg_type == "sticker":
                    media_id = msg.get("sticker", {}).get("id")

                elif msg_type == "video":
                    media_id = msg.get("video", {}).get("id")
                    text = msg.get("video", {}).get("caption", "") or ""

                elif msg_type == "audio":
                    media_id = msg.get("audio", {}).get("id")

                elif msg_type == "document":
                    media_id = msg.get("document", {}).get("id")
                    text = msg.get("document", {}).get("filename", "") or ""

                elif msg_type == "reaction":
                    text = msg.get("reaction", {}).get("emoji", "")

                elif msg_type == "button":
                    text = msg.get("button", {}).get("text", "")

                elif msg_type == "location":
                    loc = msg.get("location", {})
                    text = f"📍 {loc.get('name', 'Location')} ({loc.get('latitude', '')}, {loc.get('longitude', '')})"

                elif msg_type == "contacts":
                    c_list = msg.get("contacts", [])
                    parts = []
                    for c in c_list:
                        name = c.get("name", {}).get("formatted_name", "?")
                        phones = c.get("phones", [])
                        phone_strs = [p.get("phone", "") or p.get("wa_id", "") for p in phones]
                        phone_strs = [p for p in phone_strs if p]
                        emails = [e.get("email", "") for e in c.get("emails", []) if e.get("email")]
                        org = c.get("org", {}).get("company", "")
                        detail_parts = [name]
                        if phone_strs:
                            detail_parts.append(f"phone: {', '.join(phone_strs)}")
                        if emails:
                            detail_parts.append(f"email: {', '.join(emails)}")
                        if org:
                            detail_parts.append(f"company: {org}")
                        parts.append(" | ".join(detail_parts))
                    text = f"👤 Contact card: {'; '.join(parts)}"

                elif msg_type == "interactive":
                    interactive = msg.get("interactive", {})
                    itype = interactive.get("type", "")
                    if itype == "button_reply":
                        text = interactive.get("button_reply", {}).get("title", "")
                    elif itype == "list_reply":
                        lr = interactive.get("list_reply", {})
                        text = f"{lr.get('title', '')} — {lr.get('description', '')}"
                    elif itype == "nfm_reply":
                        text = interactive.get("nfm_reply", {}).get("body", "") or interactive.get("nfm_reply", {}).get("response_json", "")
                    else:
                        text = f"[interactive: {itype}]"

                elif msg_type == "order":
                    order = msg.get("order", {})
                    items = order.get("product_items", [])
                    item_names = [i.get("product_retailer_id", "item") for i in items]
                    text = f"🛒 Order: {', '.join(item_names)}" if item_names else "🛒 Order"

                elif msg_type == "referral":
                    ref = msg.get("referral", {})
                    text = f"📢 Referral from ad: {ref.get('headline', '')} — {ref.get('body', '')}"

                elif msg_type == "unsupported":
                    text = "[Unsupported message type — user sent something WhatsApp can't forward to APIs]"

                else:
                    text = f"[{msg_type}]"

                # --- Download media if present ---
                if media_id:
                    result = await _download_meta_media(media_id)
                    if result:
                        media_urls.append(result["url"])
                        media_types.append(result["mime"])

                    # Enrich at ingest via unified pipeline (enrich.py)
                    if result:
                        mime_base = (result["mime"] or "").split(";")[0].strip()
                        fname = result["url"].split("/")[-1]
                        fpath = MEDIA_DIR / fname

                        if (msg_type == "audio" or mime_base.startswith("audio/")) and fpath.exists():
                            from messaging import transcribe_file
                            try:
                                transcript = await transcribe_file(fpath)
                                if transcript:
                                    text = f"[Voice note]: {transcript}"
                                    logger.info("WA ingest transcribed | file=%s | chars=%d", fname, len(transcript))
                            except Exception as exc:
                                logger.warning("WA ingest transcription failed | %s", exc)
                                if not text:
                                    text = "🎤 Voice note (transcription failed)"

                        elif fpath.exists():
                            from messaging import parse_media
                            try:
                                parsed = await parse_media(fpath, mime_base, caption=text)
                                if parsed:
                                    if mime_base.startswith("image/"):
                                        text = f"[Photo]:\n{parsed}"
                                    else:
                                        text = f"[Document: {text or fname}]\n\n{parsed}"
                                    logger.info("WA ingest parsed | type=%s | file=%s | chars=%d", mime_base, fname, len(parsed))
                            except Exception as exc:
                                logger.warning("WA ingest parse failed | type=%s | %s", mime_base, exc)
                                if not text or text in ("📷 Photo", "📎 Document", "🎨 Sticker"):
                                    friendly_fallback = {"image": "📷 Photo", "application": "📎 Document"}
                                    prefix = mime_base.split("/")[0]
                                    text = friendly_fallback.get(prefix, f"[{msg_type}]") + f" ({fname})"

                    if not text:
                        friendly = {"image": "📷 Photo", "sticker": "🎨 Sticker", "video": "🎥 Video",
                                    "audio": "🎤 Voice note", "document": "📎 Document"}
                        text = friendly.get(msg_type, f"[{msg_type}]")

                logger.info(
                    "Meta WhatsApp inbound | from=%s | name=%s | type=%s | media=%d | text=%s",
                    phone, contact_name, msg_type, len(media_urls), text[:80],
                )

                # Look up the text of the message being replied to
                reply_to_text_val = None
                if reply_to_wa_id:
                    try:
                        sb_client = await database.get_client()
                        sb_base = database._get_base_url()
                        rp_resp = await sb_client.get(
                            f"{sb_base}/whatsapp_messages",
                            params={
                                "wa_message_id": f"eq.{reply_to_wa_id}",
                                "select": "message_text",
                                "limit": "1",
                            },
                            headers=database._get_headers(),
                        )
                        if rp_resp.status_code == 200:
                            rp_rows = rp_resp.json()
                            if rp_rows:
                                reply_to_text_val = rp_rows[0].get("message_text", "")
                    except Exception as rp_exc:
                        logger.debug("Reply-to lookup failed (non-fatal) | %s", rp_exc)

                try:
                    await _store_message(
                        phone_number=phone,
                        role="user",
                        text=text,
                        message_type=msg_type,
                        media_urls=media_urls,
                        media_types=media_types,
                        wa_message_id=wa_msg_id,
                        reply_to_wa_id=reply_to_wa_id,
                        reply_to_text=reply_to_text_val,
                    )

                    if contact_name and contact_name != "Unknown":
                        try:
                            client = await database.get_client()
                            base_url = database._get_base_url()
                            await client.post(
                                f"{base_url}/whatsapp_user_profiles",
                                json={
                                    "phone_number": phone,
                                    "display_name": contact_name,
                                },
                                headers={
                                    **database._get_headers(),
                                    "Prefer": "resolution=merge-duplicates",
                                },
                            )
                        except Exception as exc:
                            logger.debug("Profile upsert failed (non-fatal) | %s", exc)

                    wa_digits = phone.lstrip("+").replace("whatsapp:", "").replace(" ", "").replace("-", "")
                    is_founder = wa_digits in FOUNDER_DEBUG_PHONES

                    # Mirror ALL inbound messages to Chatwoot (non-blocking, non-fatal)
                    if text and text.strip():
                        from routes.chatwoot import push_message_to_chatwoot as _cw_push
                        asyncio.create_task(_cw_push(phone, contact_name, text, "incoming"))

                    # Auto-reply via Hermes only for the founder's numbers.
                    # All other contacts land in Chatwoot for manual agent reply.
                    if is_founder and (text or "").strip():
                        skip_agent = False
                        try:
                            from agent import try_handle_founder_skill_reply

                            handled, founder_msg = await try_handle_founder_skill_reply(wa_digits, text)
                            if handled and founder_msg.strip():
                                skip_agent = True
                                tok = _get_token()
                                pid = _get_phone_id()
                                if tok and pid:
                                    async with http_client(timeout=15) as _cl:
                                        pr = await _cl.post(
                                            f"{META_API_BASE}/{pid}/messages",
                                            headers={
                                                "Authorization": f"Bearer {tok}",
                                                "Content-Type": "application/json",
                                            },
                                            json={
                                                "messaging_product": "whatsapp",
                                                "to": wa_digits,
                                                "type": "text",
                                                "text": {"body": founder_msg.strip()[:4096]},
                                            },
                                        )
                                        if pr.status_code not in (200, 201):
                                            logger.warning(
                                                "Founder skill reply WA failed | %s | %s",
                                                pr.status_code,
                                                pr.text[:200],
                                            )
                                try:
                                    await _store_message(
                                        phone_number=phone,
                                        role="assistant",
                                        text=founder_msg.strip()[:4096],
                                        message_type="text",
                                    )
                                    # Mirror skill reply to Chatwoot as outgoing
                                    from routes.chatwoot import push_message_to_chatwoot as _cw_push_out
                                    asyncio.create_task(_cw_push_out(phone, contact_name, founder_msg.strip()[:4096], "outgoing"))
                                except Exception as _st_exc:
                                    logger.debug("Store founder skill ack failed | %s", _st_exc)
                                logger.info("Founder skill command handled | skip_agent=1")
                        except Exception as _fs_exc:
                            logger.warning("Founder skill handler error | %s", _fs_exc, exc_info=True)

                        if not skip_agent:
                            asyncio.create_task(_debounce_reply(
                                phone, contact_name, {
                                    "text": text,
                                    "msg_type": msg_type,
                                    "media_urls": media_urls,
                                    "media_types": media_types,
                                    "wa_msg_id": wa_msg_id,
                                }
                            ))
                    else:
                        logger.info(
                            "Non-founder message logged to Chatwoot only | phone=%s | name=%s",
                            phone[:10], contact_name,
                        )

                except Exception as exc:
                    logger.error("Failed to store inbound message | from=%s | err=%s", phone, exc)

    return JSONResponse({"status": "ok"}, status_code=200)


# ─── Read conversations ────────────────────────────────────────────

@router.get("/api/copilot/conversations")
async def list_conversations() -> JSONResponse:
    """
    List distinct phone numbers with their most recent message + display name.
    """
    client = await database.get_client()
    base_url = database._get_base_url()

    resp = await client.get(
        f"{base_url}/rpc/copilot_conversations",
        headers=database._get_headers(),
    )

    if resp.status_code != 200:
        # Fallback: raw distinct query
        resp2 = await client.get(
            f"{base_url}/whatsapp_messages",
            params={
                "select": "phone_number,message_text,role,created_at",
                "order": "created_at.desc",
                "limit": "100",
            },
            headers=database._get_headers(),
        )
        if resp2.status_code != 200:
            return JSONResponse({"error": "failed to fetch"}, status_code=500)

        rows = resp2.json() or []
        seen = {}
        for r in rows:
            pn = r.get("phone_number", "")
            if pn not in seen:
                seen[pn] = {
                    "phone_number": pn,
                    "last_message": r.get("message_text", ""),
                    "last_role": r.get("role", ""),
                    "last_at": r.get("created_at", ""),
                    "display_name": None,
                }
        return JSONResponse(list(seen.values()))

    return JSONResponse(resp.json())


# ─── Read messages for a phone ─────────────────────────────────────

@router.get("/api/copilot/messages/{phone}")
async def get_messages(
    phone: str,
    limit: int = Query(default=50, le=200),
    after: Optional[str] = Query(default=None),
) -> JSONResponse:
    """
    Get messages for a specific phone number, ordered by time.
    Pass `after` (ISO timestamp) for polling new messages.
    """
    clean_phone = phone if phone.startswith("+") else f"+{phone}"
    client = await database.get_client()
    base_url = database._get_base_url()

    params: Dict[str, str] = {
        "phone_number": f"eq.{clean_phone}",
        "select": "id,phone_number,role,message_text,message_type,media_urls,media_types,created_at,wa_message_id,reply_to_wa_id,reply_to_text",
        "order": "created_at.asc",
        "limit": str(limit),
    }
    if after:
        params["created_at"] = f"gt.{after}"

    resp = await client.get(
        f"{base_url}/whatsapp_messages",
        params=params,
        headers=database._get_headers(),
    )
    if resp.status_code != 200:
        return JSONResponse({"error": "failed to fetch"}, status_code=500)

    return JSONResponse(resp.json())


# ─── Send message from app ─────────────────────────────────────────

@router.post("/api/copilot/send")
async def send_message(request: Request) -> JSONResponse:
    """
    Send a WhatsApp message from the Leo Copilot app.

    Body: { "to": "00000000000", "text": "Hello from Leo!" }

    Stores in Supabase as role='assistant' then sends via Meta Cloud API.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    to = str(body.get("to", "")).strip()
    text = str(body.get("text", "")).strip()
    reply_to = str(body.get("reply_to", "")).strip() or None

    if not to or not text:
        return JSONResponse({"error": "to and text required"}, status_code=400)

    clean_to = to if to.startswith("+") else f"+{to}"
    wa_to = clean_to.lstrip("+")

    # Send via Meta Cloud API first so we get the wa_message_id
    token = _get_token()
    phone_id = _get_phone_id()

    if not token or not phone_id:
        logger.error("Meta Cloud API credentials missing | token=%s phone_id=%s", bool(token), bool(phone_id))
        return JSONResponse({"error": "WhatsApp not configured"}, status_code=500)

    meta_payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": wa_to,
        "type": "text",
        "text": {"body": text},
    }
    if reply_to:
        meta_payload["context"] = {"message_id": reply_to}

    try:
        async with http_client(timeout=15) as client:
            resp = await client.post(
                f"{META_API_BASE}/{phone_id}/messages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=meta_payload,
            )
            result = resp.json()
            if resp.status_code not in (200, 201):
                logger.error("Meta send failed | status=%s body=%s", resp.status_code, result)
                return JSONResponse({
                    "error": "Meta API error",
                    "detail": result,
                }, status_code=502)

            sent_wa_id = result.get("messages", [{}])[0].get("id", "")
            logger.info("Meta WhatsApp sent | to=%s | text=%s | wamid=%s",
                        clean_to, text[:50], sent_wa_id)

    except Exception as exc:
        logger.error("Meta send exception | to=%s | err=%s", clean_to, exc)
        return JSONResponse({"error": str(exc)}, status_code=502)

    # Look up the text of the message being replied to for display
    reply_to_text_val = None
    if reply_to:
        try:
            sb_client = await database.get_client()
            sb_base = database._get_base_url()
            rp_resp = await sb_client.get(
                f"{sb_base}/whatsapp_messages",
                params={
                    "wa_message_id": f"eq.{reply_to}",
                    "select": "message_text",
                    "limit": "1",
                },
                headers=database._get_headers(),
            )
            if rp_resp.status_code == 200:
                rp_rows = rp_resp.json()
                if rp_rows:
                    reply_to_text_val = rp_rows[0].get("message_text", "")
        except Exception:
            pass

    # Store in Supabase with wa_message_id and reply context
    try:
        stored = await _store_message(
            phone_number=clean_to,
            role="assistant",
            text=text,
            wa_message_id=sent_wa_id,
            reply_to_wa_id=reply_to,
            reply_to_text=reply_to_text_val,
        )
    except Exception as exc:
        logger.error("Failed to store outbound message | to=%s | err=%s", clean_to, exc)
        return JSONResponse({"ok": True, "stored": False, "wa_message_id": sent_wa_id})

    return JSONResponse({
        "ok": True,
        "message_id": stored.get("id") if isinstance(stored, dict) else None,
        "wa_message_id": sent_wa_id,
    })


# ─── Send template message ─────────────────────────────────────────

@router.post("/api/copilot/send-template")
async def send_template(request: Request) -> JSONResponse:
    """
    Send a WhatsApp template message to initiate a conversation.

    Body: { "to": "00000000000", "template": "hello_world" }
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    to = str(body.get("to", "")).strip()
    template_name = str(body.get("template", "hello_world")).strip()
    language = str(body.get("language", "en_US")).strip()

    if not to:
        return JSONResponse({"error": "to required"}, status_code=400)

    wa_to = to.lstrip("+")
    token = _get_token()
    phone_id = _get_phone_id()

    if not token or not phone_id:
        return JSONResponse({"error": "WhatsApp not configured"}, status_code=500)

    try:
        async with http_client(timeout=15) as client:
            resp = await client.post(
                f"{META_API_BASE}/{phone_id}/messages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "messaging_product": "whatsapp",
                    "to": wa_to,
                    "type": "template",
                    "template": {
                        "name": template_name,
                        "language": {"code": language},
                    },
                },
            )
            result = resp.json()
            if resp.status_code not in (200, 201):
                logger.error("Template send failed | status=%s body=%s", resp.status_code, result)
                return JSONResponse({"error": "Meta API error", "detail": result}, status_code=502)

    except Exception as exc:
        logger.error("Template send exception | to=%s | err=%s", to, exc)
        return JSONResponse({"error": str(exc)}, status_code=502)

    # Store the template send as an outbound message
    try:
        await _store_message(
            phone_number=to if to.startswith("+") else f"+{to}",
            role="assistant",
            text=f"[Template: {template_name}]",
            message_type="template",
        )
    except Exception as exc:
        logger.warning("Failed to store template message (non-fatal) | %s", exc)

    return JSONResponse({
        "ok": True,
        "wa_message_id": result.get("messages", [{}])[0].get("id", ""),
    })


# ─── Serve media files from disk ──────────────────────────────────

@router.get("/api/media/whatsapp/{filename}")
async def serve_media(filename: str):
    """Serve a media file that was downloaded from Meta."""
    safe_name = pathlib.Path(filename).name
    fpath = MEDIA_DIR / safe_name
    if not fpath.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(fpath, headers={"Cache-Control": "public, max-age=31536000"})


# ─── Upload & send voice note from app ────────────────────────────

@router.post("/api/copilot/upload-voice")
async def upload_voice(
    to: str = Form(...),
    audio: UploadFile = File(...),
) -> JSONResponse:
    """
    Upload a voice note from the Leo Copilot app, save to disk, convert
    to OGG Opus (WhatsApp requirement), send via Meta Cloud API, and
    store in Supabase.
    """
    clean_to = to if to.startswith("+") else f"+{to}"
    wa_to = clean_to.lstrip("+")

    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        return JSONResponse({"error": "empty audio"}, status_code=400)

    uid = uuid.uuid4().hex[:12]
    raw_fname = f"voice_raw_{uid}.webm"
    raw_path = MEDIA_DIR / raw_fname
    raw_path.write_bytes(audio_bytes)

    # Convert WebM -> OGG Opus (mono 48kHz, speech-optimized for WhatsApp PTT)
    ogg_fname = f"voice_{uid}.ogg"
    ogg_path = MEDIA_DIR / ogg_fname
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(raw_path),
            "-ar", "48000", "-ac", "1",
            "-c:a", "libopus", "-b:a", "128k",
            "-application", "voip",
            "-f", "ogg", str(ogg_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=15)
        if proc.returncode != 0:
            logger.error("ffmpeg convert failed | rc=%s | stderr=%s", proc.returncode, stderr_data.decode()[:300])
            return JSONResponse({"error": "Audio conversion failed"}, status_code=500)
    except asyncio.TimeoutError:
        logger.error("ffmpeg conversion timed out")
        return JSONResponse({"error": "Audio conversion timed out"}, status_code=500)

    ogg_bytes = ogg_path.read_bytes()
    public_url = f"{PUBLIC_MEDIA_BASE}/{ogg_fname}"

    logger.info(
        "Voice upload | to=%s | raw=%d bytes | ogg=%d bytes | file=%s",
        clean_to, len(audio_bytes), len(ogg_bytes), ogg_fname,
    )

    token = _get_token()
    phone_id = _get_phone_id()
    sent_wa_id = ""

    if not token or not phone_id:
        logger.error("Meta Cloud API credentials missing for voice upload")
        return JSONResponse({"error": "WhatsApp not configured"}, status_code=500)

    try:
        async with http_client(timeout=30) as client:
            upload_resp = await client.post(
                f"{META_API_BASE}/{phone_id}/media",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": (ogg_fname, ogg_bytes, "audio/ogg; codecs=opus")},
                data={"messaging_product": "whatsapp", "type": "audio/ogg; codecs=opus"},
            )
            if upload_resp.status_code not in (200, 201):
                logger.error("Meta voice upload failed | status=%s body=%s", upload_resp.status_code, upload_resp.text[:300])
                return JSONResponse({"error": "Meta voice upload failed", "detail": upload_resp.json()}, status_code=502)

            wa_media_id = upload_resp.json().get("id")
            if not wa_media_id:
                return JSONResponse({"error": "No media ID from Meta"}, status_code=502)

            send_resp = await client.post(
                f"{META_API_BASE}/{phone_id}/messages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "messaging_product": "whatsapp",
                    "to": wa_to,
                    "type": "audio",
                    "audio": {"id": wa_media_id},
                },
            )
            result = send_resp.json()
            if send_resp.status_code not in (200, 201):
                logger.error("Meta voice send failed | status=%s body=%s", send_resp.status_code, result)
                return JSONResponse({"error": "Meta voice send failed", "detail": result}, status_code=502)

            sent_wa_id = result.get("messages", [{}])[0].get("id", "")
            logger.info("Meta voice sent | to=%s | wamid=%s", clean_to, sent_wa_id)

    except Exception as exc:
        logger.error("Voice send exception | to=%s | err=%s", clean_to, exc)
        return JSONResponse({"error": str(exc)}, status_code=502)

    try:
        await _store_message(
            phone_number=clean_to,
            role="assistant",
            text="🎤 Voice note",
            message_type="audio",
            media_urls=[public_url],
            media_types=["audio/ogg"],
            wa_message_id=sent_wa_id,
        )
    except Exception as exc:
        logger.error("Failed to store voice message | to=%s | err=%s", clean_to, exc)

    return JSONResponse({"ok": True, "url": public_url, "wa_message_id": sent_wa_id})


# ─── Upload & send media (image/document) from app ────────────────

UPLOAD_MIME_TO_WA_TYPE = {
    "image/jpeg": "image", "image/png": "image", "image/webp": "image",
    "image/gif": "image", "video/mp4": "video", "video/3gpp": "video",
    "audio/ogg": "audio", "audio/mpeg": "audio", "audio/mp4": "audio",
    "application/pdf": "document", "application/msword": "document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
    "application/vnd.ms-excel": "document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "document",
}


@router.post("/api/copilot/upload-media")
async def upload_media(
    to: str = Form(...),
    media: UploadFile = File(...),
    caption: Optional[str] = Form(default=None),
) -> JSONResponse:
    """
    Upload any media from the Leo Copilot app, save to disk, send via
    Meta Cloud API, and store in Supabase.
    """
    clean_to = to if to.startswith("+") else f"+{to}"
    wa_to = clean_to.lstrip("+")

    media_bytes = await media.read()
    if len(media_bytes) == 0:
        return JSONResponse({"error": "empty file"}, status_code=400)

    content_type = media.content_type or "application/octet-stream"
    wa_type = UPLOAD_MIME_TO_WA_TYPE.get(content_type, "document")
    ext = MIME_TO_EXT.get(content_type.split(";")[0].strip(), "bin")
    fname = f"upload_{uuid.uuid4().hex[:12]}.{ext}"
    fpath = MEDIA_DIR / fname
    fpath.write_bytes(media_bytes)
    public_url = f"{PUBLIC_MEDIA_BASE}/{fname}"

    logger.info(
        "Media upload | to=%s | type=%s | mime=%s | size=%d bytes | file=%s",
        clean_to, wa_type, content_type, len(media_bytes), fname,
    )

    token = _get_token()
    phone_id = _get_phone_id()
    sent_wa_id = ""

    if token and phone_id:
        try:
            async with http_client(timeout=30) as client:
                upload_resp = await client.post(
                    f"{META_API_BASE}/{phone_id}/media",
                    headers={"Authorization": f"Bearer {token}"},
                    files={"file": (media.filename or fname, media_bytes, content_type)},
                    data={"messaging_product": "whatsapp", "type": content_type},
                )
                if upload_resp.status_code not in (200, 201):
                    logger.error("Meta media upload failed | status=%s body=%s",
                                 upload_resp.status_code, upload_resp.text[:300])
                    return JSONResponse({"error": "Meta upload failed"}, status_code=502)

                wa_media_id = upload_resp.json().get("id")
                if not wa_media_id:
                    return JSONResponse({"error": "No media ID from Meta"}, status_code=502)

                msg_payload: Dict[str, Any] = {
                    "messaging_product": "whatsapp",
                    "to": wa_to,
                    "type": wa_type,
                    wa_type: {"id": wa_media_id},
                }
                if caption and wa_type in ("image", "video", "document"):
                    msg_payload[wa_type]["caption"] = caption
                if wa_type == "document" and media.filename:
                    msg_payload[wa_type]["filename"] = media.filename

                send_resp = await client.post(
                    f"{META_API_BASE}/{phone_id}/messages",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=msg_payload,
                )
                result = send_resp.json()
                if send_resp.status_code not in (200, 201):
                    logger.error("Meta media send failed | status=%s body=%s",
                                 send_resp.status_code, result)
                    return JSONResponse({"error": "Meta send failed", "detail": result}, status_code=502)

                sent_wa_id = result.get("messages", [{}])[0].get("id", "")

        except Exception as exc:
            logger.error("Media send exception | to=%s | err=%s", clean_to, exc)
            return JSONResponse({"error": str(exc)}, status_code=502)

    friendly = {"image": "📷 Photo", "video": "🎥 Video", "document": "📎 Document", "audio": "🎤 Audio"}
    display_text = caption or friendly.get(wa_type, f"[{wa_type}]")

    try:
        await _store_message(
            phone_number=clean_to,
            role="assistant",
            text=display_text,
            message_type=wa_type,
            media_urls=[public_url],
            media_types=[content_type],
            wa_message_id=sent_wa_id,
        )
    except Exception as exc:
        logger.error("Failed to store media message | to=%s | err=%s", clean_to, exc)

    return JSONResponse({"ok": True, "url": public_url, "wa_message_id": sent_wa_id})
