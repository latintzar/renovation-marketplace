"""
Chatwoot Integration — Leo Scope Customer Support Inbox
=======================================================

Architecture:
- ALL inbound WhatsApp messages are mirrored to Chatwoot as "incoming" messages
- Auto-reply (Hermes agent) fires ONLY for the founder's phone numbers
- All other numbers: message appears in Chatwoot for manual agent reply
- When an agent replies in Chatwoot: Chatwoot calls our outbound webhook here
  → we forward the reply via Meta WhatsApp Cloud API

Data flow:
  WhatsApp → meta_whatsapp.py (store + push_to_chatwoot) → Chatwoot UI
  Chatwoot reply → POST /api/webhooks/chatwoot-outbound → WhatsApp

Endpoints:
  POST /api/webhooks/chatwoot-outbound — Chatwoot fires this when agent replies
"""

import asyncio
import logging
import os
from typing import Optional

from core import http_client
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Config ─────────────────────────────────────────────────────────

CHATWOOT_URL = os.getenv("CHATWOOT_URL", '')
CHATWOOT_API_TOKEN = os.getenv("CHATWOOT_API_TOKEN", "")
CHATWOOT_ACCOUNT_ID = int(os.getenv("CHATWOOT_ACCOUNT_ID", "1"))
CHATWOOT_INBOX_ID = int(os.getenv("CHATWOOT_INBOX_ID", "1"))

# Base URL for all Chatwoot API v1 calls
_CW_BASE = f"{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}"
_CW_HEADERS = lambda: {
    "api_access_token": CHATWOOT_API_TOKEN,
    "Content-Type": "application/json",
}


# ── Chatwoot API helpers ────────────────────────────────────────────

async def _cw(method: str, path: str, **kwargs) -> Optional[dict]:
    """Make a Chatwoot API call. Returns parsed JSON or None on error."""
    url = f"{_CW_BASE}{path}"
    try:
        async with http_client(timeout=10) as client:
            resp = await getattr(client, method)(url, headers=_CW_HEADERS(), **kwargs)
            if resp.status_code in (200, 201):
                return resp.json()
            logger.warning("Chatwoot API %s %s → %s | %s", method.upper(), path, resp.status_code, resp.text[:200])
            return None
    except Exception as exc:
        logger.error("Chatwoot API error | %s %s | %s", method.upper(), path, exc)
        return None


async def get_or_create_contact(phone: str, name: str) -> Optional[int]:
    """
    Find or create a Chatwoot contact by phone number.
    Returns the Chatwoot contact ID.
    Normalises the phone to E.164 format (+34...) for consistency.
    """
    # Normalise: ensure leading +
    clean = phone.strip()
    if not clean.startswith("+"):
        clean = f"+{clean.lstrip('+')}"

    # Search for existing contact by phone
    search = await _cw("get", "/contacts/search", params={"q": clean, "include_contacts": True})
    if search and search.get("payload"):
        for contact in search["payload"]:
            cphone = (contact.get("phone_number") or "").strip()
            if cphone == clean or cphone.lstrip("+") == clean.lstrip("+"):
                logger.debug("Chatwoot: found existing contact id=%s phone=%s", contact["id"], clean)
                return contact["id"]

    # Create new contact
    new_contact = await _cw("post", "/contacts", json={
        "inbox_id": CHATWOOT_INBOX_ID,
        "name": name or clean,
        "phone_number": clean,
    })
    if new_contact:
        # Chatwoot wraps create response: {"payload": {"contact": {...}}}
        payload = new_contact.get("payload", new_contact)
        if isinstance(payload, dict) and "contact" in payload:
            payload = payload["contact"]
        contact_id = payload.get("id")
        logger.info("Chatwoot: created contact id=%s phone=%s name=%s", contact_id, clean, name)
        return contact_id

    logger.error("Chatwoot: failed to create contact | phone=%s", clean)
    return None


async def get_or_create_conversation(contact_id: int) -> Optional[int]:
    """
    Find the most recent open conversation for this contact in our inbox,
    or create a new one. Returns the Chatwoot conversation ID.
    """
    # Check if this contact already has an open conversation in our inbox
    contact_convs = await _cw("get", f"/contacts/{contact_id}/conversations")
    if contact_convs and contact_convs.get("payload"):
        for conv in contact_convs["payload"]:
            if conv.get("inbox_id") == CHATWOOT_INBOX_ID and conv.get("status") in ("open", "pending"):
                logger.debug("Chatwoot: reusing conversation id=%s contact=%s", conv["id"], contact_id)
                return conv["id"]

    # Create new conversation
    new_conv = await _cw("post", "/conversations", json={
        "contact_id": contact_id,
        "inbox_id": CHATWOOT_INBOX_ID,
        "status": "open",
    })
    if new_conv:
        conv_id = new_conv.get("id")
        logger.info("Chatwoot: created conversation id=%s contact=%s", conv_id, contact_id)
        return conv_id

    logger.error("Chatwoot: failed to create conversation | contact=%s", contact_id)
    return None


async def push_message_to_chatwoot(
    phone: str,
    name: str,
    text: str,
    message_type: str = "incoming",
) -> bool:
    """
    Push a message to the Chatwoot conversation for this phone number.

    message_type:
      - "incoming"  = customer sent this (WhatsApp → Chatwoot)
      - "outgoing"  = agent/bot sent this (Hermes reply → Chatwoot)

    Non-fatal: logs errors but never raises.
    """
    if not CHATWOOT_API_TOKEN:
        logger.debug("Chatwoot push skipped — no API token configured")
        return False

    try:
        contact_id = await get_or_create_contact(phone, name)
        if not contact_id:
            return False

        conv_id = await get_or_create_conversation(contact_id)
        if not conv_id:
            return False

        msg_payload = {
            "content": text or "(no text)",
            "message_type": message_type,
            "private": False,
        }

        result = await _cw("post", f"/conversations/{conv_id}/messages", json=msg_payload)
        if result:
            logger.debug(
                "Chatwoot: pushed %s message | conv=%s | phone=%s | chars=%d",
                message_type, conv_id, phone[:10], len(text),
            )
            return True

        return False

    except Exception as exc:
        logger.error("push_message_to_chatwoot failed (non-fatal) | phone=%s | %s", phone[:12], exc)
        return False


# ── Outbound webhook — agent replies ────────────────────────────────

@router.post("/api/webhooks/chatwoot-outbound")
async def chatwoot_outbound_webhook(request: Request) -> JSONResponse:
    """
    Chatwoot fires this when any message is created on the WhatsApp inbox.
    We only care about 'outgoing' messages (agent replies) that aren't private notes.
    Those get forwarded to the customer via Meta WhatsApp Cloud API.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    event = payload.get("event", "")
    logger.debug("Chatwoot webhook | event=%s", event)

    if event != "message_created":
        return JSONResponse({"status": "ignored", "reason": "not message_created"})

    # Only forward outgoing messages (agent replies), not incoming or private notes
    message_type = payload.get("message_type", "")
    if message_type != "outgoing":
        return JSONResponse({"status": "ignored", "reason": "not outgoing"})

    private = payload.get("private", False)
    if private:
        return JSONResponse({"status": "ignored", "reason": "private note"})

    content = (payload.get("content") or "").strip()
    if not content:
        return JSONResponse({"status": "ignored", "reason": "empty content"})

    # Get the conversation to find the customer's phone number
    conv = payload.get("conversation", {})
    conv_id = conv.get("id")
    if not conv_id:
        logger.warning("Chatwoot outbound webhook: no conversation id in payload")
        return JSONResponse({"error": "no conversation id"}, status_code=400)

    # Try to get phone from conversation meta (sender is the customer)
    meta = conv.get("meta", {})
    sender = meta.get("sender", {})
    customer_phone = sender.get("phone_number", "")

    # If not in payload, look up via API
    if not customer_phone:
        conv_data = await _cw("get", f"/conversations/{conv_id}")
        if conv_data:
            meta = conv_data.get("meta", {})
            sender_meta = meta.get("sender", {})
            customer_phone = sender_meta.get("phone_number", "")

    if not customer_phone:
        logger.error("Chatwoot outbound: could not resolve customer phone | conv=%s", conv_id)
        return JSONResponse({"error": "could not resolve customer phone"}, status_code=400)

    # Normalise phone (Meta expects digits without + for WhatsApp API)
    phone_digits = customer_phone.lstrip("+").replace(" ", "").replace("-", "")

    logger.info(
        "Chatwoot outbound: forwarding agent reply | conv=%s | to=%s | chars=%d | text=%s",
        conv_id, phone_digits[:10], len(content), content[:80],
    )

    # Fire and forget — send via Meta WhatsApp API
    asyncio.create_task(_forward_to_whatsapp(phone_digits, content, conv_id))

    return JSONResponse({"status": "ok", "queued": True})


async def _forward_to_whatsapp(phone_digits: str, content: str, conv_id: int) -> None:
    """Forward a Chatwoot agent reply to WhatsApp via Meta Cloud API."""
    try:
        from messaging import send_wa_message
        result = await send_wa_message(
            phone=phone_digits,
            text=content,
            purpose="internal",
            do_store=True,
            skip_window_check=True,
        )
        if result.ok:
            logger.info("Chatwoot→WA forwarded | conv=%s | to=%s | wamid=%s", conv_id, phone_digits[:10], result.wa_message_id)
        else:
            logger.error("Chatwoot→WA forward failed | conv=%s | to=%s | error=%s", conv_id, phone_digits[:10], result.error)
    except Exception as exc:
        logger.error("Chatwoot→WA forward exception | conv=%s | %s", conv_id, exc, exc_info=True)
