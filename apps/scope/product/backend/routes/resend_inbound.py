"""
Resend Inbound Email Webhook
==============================

Receives emails sent to *@projects.leo.casa via Resend's inbound MX webhook.

Primary use case: someone replies to an email Leo sent (from project-agent@projects.leo.casa).
The reply is:
  1. Verified (Svix HMAC-SHA256 signature)
  2. Logged to Supabase (leo_inbound_emails table)
  3. Forwarded to the founder's WhatsApp as a notification
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

FOUNDER_PHONE = os.getenv("PETER_WHATSAPP", '')


# ─── Svix signature verification ─────────────────────────────────────

def _b64decode_secret(secret: str) -> bytes:
    s = (secret or "").strip()
    if s.startswith("whsec_"):
        s = s[len("whsec_"):]
    pad = "=" * (-len(s) % 4)
    return base64.b64decode(s + pad)


def _parse_svix_signatures(signature_header: str) -> List[str]:
    """Extract all v1 signatures from the svix-signature header.
    Format: "v1,BASE64SIG" or "v1,BASE64SIG v1,BASE64SIG2"
    """
    out: List[str] = []
    s = (signature_header or "").strip()
    if not s:
        return out
    for p in s.split():
        if "," not in p:
            continue
        ver, sig = p.split(",", 1)
        if ver.strip() == "v1" and sig.strip():
            out.append(sig.strip())
    return out


def _verify_resend_webhook(*, raw_body: bytes, headers: Dict[str, str]) -> bool:
    secret = str(settings.RESEND_WEBHOOK_SECRET or "").strip()
    if not secret:
        logger.error("RESEND_WEBHOOK_SECRET not set — cannot verify inbound email webhook")
        return False

    svix_id = str(headers.get("svix-id") or "").strip()
    svix_ts = str(headers.get("svix-timestamp") or "").strip()
    svix_sig = str(headers.get("svix-signature") or "").strip()
    if not svix_id or not svix_ts or not svix_sig:
        logger.warning("Resend webhook missing Svix headers | id=%s ts=%s sig=%s", bool(svix_id), bool(svix_ts), bool(svix_sig))
        return False

    try:
        ts_int = int(svix_ts)
    except Exception:
        logger.warning("Resend webhook: invalid svix-timestamp: %r", svix_ts)
        return False

    tolerance_s = int(os.getenv("RESEND_WEBHOOK_TOLERANCE_SECONDS", "300"))
    now = int(time.time())
    if abs(now - ts_int) > max(30, tolerance_s):
        logger.warning("Resend webhook: timestamp outside tolerance | now=%s ts=%s delta=%ss", now, ts_int, abs(now - ts_int))
        return False

    try:
        key = _b64decode_secret(secret)
    except Exception as exc:
        logger.error("Resend webhook: secret decode failed | err=%s", exc)
        return False

    try:
        payload_text = raw_body.decode("utf-8")
    except Exception as exc:
        logger.warning("Resend webhook: body decode failed | err=%s", exc)
        return False

    signed = f"{svix_id}.{svix_ts}.{payload_text}".encode("utf-8")
    digest = hmac.new(key, signed, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")

    candidates = _parse_svix_signatures(svix_sig)
    return any(hmac.compare_digest(expected, cand) for cand in candidates)


# ─── Helpers ──────────────────────────────────────────────────────────

def _extract_email_address(from_field: str) -> str:
    s = str(from_field or "").strip()
    if "<" in s and ">" in s:
        return s.split("<", 1)[1].split(">", 1)[0].strip()
    return s


def _clean_reply_text(body: str) -> str:
    """Strip common email reply cruft (quoted text, signatures) to get the actual reply."""
    lines = body.split("\n")
    clean: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("On ") and stripped.endswith("wrote:"):
            break
        if stripped.startswith(">"):
            break
        if stripped == "---" or stripped == "--":
            break
        if stripped.startswith("From:") or stripped.startswith("Sent:") or stripped.startswith("Date:"):
            break
        clean.append(line)
    result = "\n".join(clean).strip()
    return result if result else body.strip()


def _format_wa_notification(from_addr: str, subject: str, body: str) -> str:
    """Format an inbound email as a WhatsApp notification to the founder."""
    reply_text = _clean_reply_text(body)
    truncated = reply_text[:800] + ("…" if len(reply_text) > 800 else "")
    parts = [f"*Email received*"]
    parts.append(f"From: {from_addr}")
    if subject:
        parts.append(f"Subject: {subject}")
    parts.append(f"\n{truncated}")
    return "\n".join(parts)


async def _send_wa_notification(phone: str, text: str) -> bool:
    """Send a WhatsApp text message via unified send_wa_message."""
    from messaging import send_wa_message
    try:
        result = await send_wa_message(phone, text, purpose="internal", do_store=False, skip_window_check=True)
        if result.ok:
            logger.info("Email notification sent to WhatsApp | phone=%s", phone)
            return True
        logger.warning("WhatsApp send failed for email notification | error=%s", result.error)
        return False
    except Exception as exc:
        logger.error("WhatsApp send exception for email notification | err=%s", exc)
        return False


async def _store_inbound_email(
    from_addr: str,
    to_addrs: Any,
    subject: str,
    body: str,
    raw_payload: dict,
) -> bool:
    """Store the inbound email in Supabase for audit trail."""
    try:
        from core import http_client, sb_headers, sb_url

        to_list = to_addrs if isinstance(to_addrs, list) else [str(to_addrs or "")]

        row = {
            "from_addr": from_addr,
            "to_addrs": to_list,
            "subject": subject,
            "body_text": body[:10000],
            "raw_headers": {
                k: v for k, v in raw_payload.items()
                if k in ("type", "created_at", "headers")
            },
        }

        async with http_client(timeout=15) as client:
            resp = await client.post(
                f"{sb_url()}/leo_inbound_emails",
                json=row,
                headers={**sb_headers(), "Prefer": "return=minimal"},
            )
        if resp.status_code in (200, 201):
            logger.info("Inbound email stored | from=%s subject=%s", from_addr, subject[:60])
            return True
        logger.warning("Inbound email store failed (non-fatal) | status=%s body=%s", resp.status_code, resp.text[:200])
        return False
    except Exception as exc:
        logger.warning("Inbound email store exception (non-fatal) | err=%s", exc)
        return False


# ─── Webhook endpoint ─────────────────────────────────────────────────

@router.post("/api/webhooks/resend")
async def resend_inbound_webhook(request: Request) -> JSONResponse:
    """
    Resend inbound MX webhook.

    Expects Svix headers (svix-id, svix-timestamp, svix-signature) for verification.
    Processes email.received events — forwards to founder WhatsApp and stores in DB.
    """
    raw = await request.body()
    hdrs = {k.lower(): v for k, v in dict(request.headers or {}).items()}

    if not _verify_resend_webhook(raw_body=raw, headers=hdrs):
        logger.warning("Resend webhook: signature verification failed")
        return JSONResponse({"ok": False, "error": "invalid signature"}, status_code=400)

    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        logger.warning("Resend webhook: invalid JSON | err=%s", exc)
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)

    event_type = str(payload.get("type") or "").strip()
    logger.info("Resend webhook received | type=%s", event_type)

    if event_type != "email.received":
        return JSONResponse({"ok": True, "ignored": True, "type": event_type}, status_code=200)

    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    from_field = str(data.get("from") or "").strip()
    to_field = data.get("to")
    subject = str(data.get("subject") or "").strip()
    body_text = str(data.get("text") or "").strip()
    body_html = str(data.get("html") or "").strip()

    from_addr = _extract_email_address(from_field)
    effective_body = body_text or body_html

    logger.info(
        "Inbound email | from=%s to=%s subject=%s body_len=%d",
        from_addr, to_field, subject[:60], len(effective_body),
    )

    await _store_inbound_email(
        from_addr=from_field,
        to_addrs=to_field,
        subject=subject,
        body=effective_body,
        raw_payload=payload,
    )

    wa_text = _format_wa_notification(from_field, subject, effective_body)
    await _send_wa_notification(FOUNDER_PHONE, wa_text)

    # Route the email content through Leo agent and reply via email
    asyncio.create_task(_auto_reply_email(
        from_addr=from_addr,
        from_field=from_field,
        subject=subject,
        body=effective_body,
    ))

    return JSONResponse({"ok": True, "from": from_addr, "subject": subject[:60]}, status_code=200)


async def _auto_reply_email(
    from_addr: str,
    from_field: str,
    subject: str,
    body: str,
) -> None:
    """Process inbound email through Leo agent and send a reply email back."""
    try:
        from agent import run_leo_chat, _to_openai_messages
        from messaging import EMAIL_CAPABILITIES

        reply_text = _clean_reply_text(body)
        if not reply_text.strip():
            logger.info("Inbound email empty body — skipping agent reply | from=%s", from_addr)
            return

        user_text = f"[Email from {from_addr}]\nSubject: {subject}\n\n{reply_text}"

        conv_id = f"email:{from_addr}"
        openai_msgs = _to_openai_messages([{"role": "user", "text": user_text}])
        if not openai_msgs:
            return

        result = await run_leo_chat(
            openai_msgs,
            mode="email",
            raw_history=[{"role": "user", "text": user_text}],
            lead_context=(
                f"This person emailed Leo at projects.leo.casa. "
                f"Their email: {from_addr}. "
                "Reply context: they may be replying to a previous email Leo sent them."
            ),
            audience="homeowner",
            lead_phone="",
            channel="email",
            conversation_id=conv_id,
            capabilities=EMAIL_CAPABILITIES,
        )
        reply = (result.get("reply") or "").strip()
        if not reply:
            logger.warning("Empty agent reply for inbound email | from=%s", from_addr)
            return

        from agent import send_email_resend
        reply_subject = f"Re: {subject}" if subject and not subject.lower().startswith("re:") else subject
        reply_html = reply.replace("\n", "<br>")

        email_result = await send_email_resend(
            to=from_addr,
            subject=reply_subject,
            body_html=reply_html,
            body_text=reply,
        )
        if email_result.get("ok"):
            logger.info("Email reply sent | to=%s | subject=%s | chars=%d", from_addr, reply_subject[:40], len(reply))
        else:
            logger.warning("Email reply send failed | to=%s | err=%s", from_addr, email_result.get("error"))

    except Exception as exc:
        logger.error("Email auto-reply failed | from=%s | err=%s", from_addr, exc, exc_info=True)
