"""
leo_agent/tools/delivery.py — Message delivery tools.

Tools: send_whatsapp, send_email, request_human
"""

from __future__ import annotations

import json
import logging

from ..tool_utils import _get_ctx_val, _record_activity, _run_async

logger = logging.getLogger(__name__)


# ── Handlers ─────────────────────────────────────────────────────────

def _handle_send_whatsapp(args: dict, **kw) -> str:
    """Unified WhatsApp send tool."""
    _record_activity("send_whatsapp")
    phone = str(args.get("phone", "")).strip()
    message = str(args.get("message", "")).strip()
    purpose = str(args.get("purpose", "general")).strip().lower()
    name = str(args.get("name", "")).strip()

    if not phone or len(phone) < 7:
        return json.dumps({"ok": False, "error": "valid phone number required"}, ensure_ascii=False)
    if not message:
        return json.dumps({"ok": False, "error": "message text required"}, ensure_ascii=False)

    from messaging.whatsapp import send_wa_message_sync

    purpose_map = {
        "general": "general",
        "referral": "referral_pro",
        "referral_pro": "referral_pro",
        "referral_homeowner": "referral_ho",
        "onboarding": "onboarding",
        "handoff": "handoff",
    }
    internal_purpose = purpose_map.get(purpose, "general")

    result = send_wa_message_sync(
        phone=phone,
        text=message,
        purpose=internal_purpose,
        name=name,
    )

    if purpose.startswith("referral") and result.ok:
        referrer_phone = _get_ctx_val("lead_phone", "")
        _store_referral_lead(phone, name, referrer_phone, purpose)

    logger.info(
        "send_whatsapp | to=%s | purpose=%s | ok=%s | method=%s",
        phone[:12], purpose, result.ok, result.method,
    )
    return json.dumps({
        "ok": result.ok,
        "method": result.method,
        "window_was_open": result.window_was_open,
        "note": result.note,
        "error": result.error or None,
    }, ensure_ascii=False)


def _store_referral_lead(phone: str, name: str, referrer_phone: str, purpose: str) -> None:
    """Store a referral in cs_leads (fire-and-forget)."""
    audience = "professional" if "pro" in purpose else "homeowner"
    try:
        from ..peter_notify import _get_supabase as _get_sb
        sb_url, sb_key = _get_sb()
        if sb_url and sb_key:
            from core import http_client_sync
            with http_client_sync(timeout=10) as client:
                client.post(
                    f"{sb_url}/rest/v1/cs_leads",
                    headers={
                        "Content-Type": "application/json",
                        "apikey": sb_key,
                        "Authorization": f"Bearer {sb_key}",
                        "Prefer": "return=minimal",
                    },
                    json={
                        "name": name or None,
                        "whatsapp": phone,
                        "audience": audience,
                        "source": "referral",
                        "chat_summary": f"Referred by {referrer_phone or 'unknown'} via WhatsApp",
                        "referred_by": referrer_phone or None,
                    },
                )
    except Exception as exc:
        logger.warning("Referral lead store failed (non-fatal) | %s", exc)


def _handle_send_email(args: dict, **kw) -> str:
    """Send an email via Resend."""
    _record_activity("send_email")
    from ..peter_notify import send_email_resend

    to = str(args.get("to", "")).strip()
    subject = str(args.get("subject", "")).strip()
    body = str(args.get("body", "")).strip()
    if not to or not subject or not body:
        return json.dumps({"ok": False, "error": "to, subject, and body are required"}, ensure_ascii=False)

    body_html = body.replace("\n", "<br>")
    result = _run_async(send_email_resend(
        to=to, subject=subject, body_html=body_html, body_text=body,
    ))
    return json.dumps(result, ensure_ascii=False)


def _handle_request_human(args: dict, **kw) -> str:
    """Escalate the conversation to a human (Peter)."""
    _record_activity("request_human")
    from ..peter_notify import request_human_escalation

    reason = str(args.get("reason", "")).strip()
    summary = str(args.get("conversation_summary", "")).strip()
    if not reason:
        return json.dumps({"ok": False, "error": "reason is required"}, ensure_ascii=False)

    lead_phone = _get_ctx_val("lead_phone", "")
    result = _run_async(request_human_escalation(
        reason=reason,
        conversation_summary=summary,
        user_name=str(args.get("user_name", "")).strip(),
        user_phone=str(args.get("user_phone", "") or lead_phone).strip(),
        channel="whatsapp" if lead_phone else "web",
    ))
    return json.dumps(result, ensure_ascii=False)


# ── Schemas ───────────────────────────────────────────────────────────

SEND_WHATSAPP_SCHEMA = {
    "name": "send_whatsapp",
    "description": (
        "Send a WhatsApp message to any phone number. Handles everything automatically: "
        "if the recipient has messaged us recently, sends plain text; if not, sends an "
        "introductory template so they can opt in. "
        "Use for: messaging someone Peter asks you to contact, sending referral invites, "
        "forwarding briefs to contractors (one-off), or any ad-hoc WhatsApp message. "
        "Do NOT use for bulk outreach (use batch_outreach for that)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "phone": {
                "type": "string",
                "description": "Recipient's phone number (with country code, e.g. +34612345678)",
            },
            "message": {
                "type": "string",
                "description": "The message text to send",
            },
            "purpose": {
                "type": "string",
                "enum": ["general", "referral", "referral_pro", "referral_homeowner", "onboarding", "handoff"],
                "description": "Message purpose — affects template selection for cold numbers. Default: general",
            },
            "name": {
                "type": "string",
                "description": "Recipient name if known (used for template personalization)",
            },
        },
        "required": ["phone", "message"],
    },
}

SEND_EMAIL_SCHEMA = {
    "name": "send_email",
    "description": (
        "Send an email to someone via Leo's email system (Resend). "
        "Use when the user asks you to email something — a summary, a brief, a report, or any info. "
        "The founder's email is operator@example.invalid "
        "Body supports plain text (newlines will be converted to <br> in HTML)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address (e.g. operator@example.invalid)"},
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Email body (plain text, newlines ok)"},
        },
        "required": ["to", "subject", "body"],
    },
}

REQUEST_HUMAN_SCHEMA = {
    "name": "request_human",
    "description": (
        "Escalate the conversation to a real human (Peter, the founder). "
        "Use when you genuinely can't help — the user is frustrated, needs a business decision, "
        "wants to discuss pricing/contracts, has a complaint, or explicitly asks for a human. "
        "This sends Peter a WhatsApp alert with context and returns a direct wa.me link "
        "you MUST share with the user so they can message Peter directly. "
        "Do NOT use this for things you can handle yourself (searches, briefs, general questions)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Why this needs a human — be specific",
            },
            "conversation_summary": {
                "type": "string",
                "description": "2-4 sentence summary of the conversation so far",
            },
            "user_name": {"type": "string", "description": "User's name if known"},
            "user_phone": {"type": "string", "description": "User's phone if known"},
        },
        "required": ["reason", "conversation_summary"],
    },
}


# ── Registration ──────────────────────────────────────────────────────

def register(registry) -> None:
    registry.register(
        name="send_whatsapp",
        toolset="leo-quote",
        schema=SEND_WHATSAPP_SCHEMA,
        handler=_handle_send_whatsapp,
        check_fn=lambda: True,
    )
    registry.register(
        name="send_email",
        toolset="leo-quote",
        schema=SEND_EMAIL_SCHEMA,
        handler=_handle_send_email,
        check_fn=lambda: True,
    )
    registry.register(
        name="request_human",
        toolset="leo-quote",
        schema=REQUEST_HUMAN_SCHEMA,
        handler=_handle_request_human,
        check_fn=lambda: True,
    )
    logger.debug("delivery tools registered")
