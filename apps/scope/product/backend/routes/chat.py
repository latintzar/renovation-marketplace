"""
Leo Chat — HTTP route
======================

POST /api/chat — thin FastAPI adapter that normalizes input into LeoMessage,
declares WEB_CAPABILITIES, and delegates to run_leo_chat.

All business logic lives in leo_agent/. This file is ONLY the HTTP adapter.
Legacy alias /api/cs-chat is kept for static HTML pages until next i18n rebuild.
"""

import logging
from typing import Any, Dict, List, Optional

from core import tracker_token_valid
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from messaging import LeoMessage, MediaAttachment, WEB_CAPABILITIES, ChannelCapabilities
from agent import run_leo_chat

logger = logging.getLogger(__name__)
router = APIRouter()

# Peter's Mac-based sales desktop impersonates this phone number when
# the Electron app hits ``/chat`` with ``mode=sales`` + ``audience=agent``
# (see the mode/audience branch below). The tracker-token check is the
# only gate — the number itself is a routing hint for downstream memory/
# conversation scoping.
_FOUNDER_SALES_DESKTOP_PHONE = "00000000000"


@router.post("/chat")
@router.post("/cs-chat")
async def chat(request: Request) -> JSONResponse:
    """
    Body: {
      "messages": [{"role":"user","text":"...","images":[{"data":"b64","media_type":"image/jpeg"}]}, ...],
      "mode": "early_access" | "general" | "scope_intake" | "sales"   (optional),
      "audience": "homeowner" | "agent" | "professional"     (optional, default homeowner),
      "lead_context": "..."                 (optional; location/flow hints),
      "profile_context": "..."              (optional; imported pro profile summary),
      "page_locale": "en" | "es"            (optional),
      "user_language_hint": "en" | "es"     (optional),
      "user_id": "..."                      (optional; phone number or lead_id for mem0)
      "confirmed": bool                     (optional; true after user taps Submit)
    }
    Returns: { "reply": "...", optional brief_update, profile_update, tool_activity }
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    raw_msgs = body.get("messages", [])
    mode = body.get("mode", "early_access")
    audience = body.get("audience", "homeowner")
    lead_context = str(body.get("lead_context") or "").strip()
    profile_context = str(body.get("profile_context") or "").strip()
    user_id = str(body.get("user_id") or "").strip()
    page_locale = str(body.get("page_locale") or body.get("locale") or "").strip()
    user_language_hint = str(body.get("user_language_hint") or body.get("language_hint") or "").strip().lower()
    confirmed = bool(body.get("confirmed", False))
    contractor_id = str(body.get("contractor_id") or "").strip()

    if audience not in ("homeowner", "agent", "professional"):
        audience = "homeowner"
    if not raw_msgs:
        return JSONResponse({"error": "messages required"}, status_code=400)

    # Build LeoMessages with MediaAttachments (thin adapter — no processing)
    leo_messages = _build_leo_messages(raw_msgs)
    if not leo_messages:
        return JSONResponse({"error": "no valid messages"}, status_code=400)

    if not confirmed and raw_msgs:
        last_text = ""
        for m in reversed(raw_msgs):
            if m.get("role") == "user":
                last_text = (m.get("text", "") or m.get("content", "")).strip()
                break
        if last_text in ("[CONFIRMED_BRIEF]", "[CONFIRMED_PROFILE]"):
            confirmed = True

    # Founder identification via passphrase in any message
    _FOUNDER_PASSPHRASE = "cute the beagle"
    all_text = " ".join(
        (m.get("text", "") or m.get("content", "")).strip()
        for m in raw_msgs if m.get("role") == "user"
    ).lower()
    is_founder_web = _FOUNDER_PASSPHRASE in all_text
    if is_founder_web:
        lead_context = (lead_context + "\n" if lead_context else "") + (
            "FOUNDER IDENTIFIED (passphrase confirmed). "
            "This is Peter, the CEO. Treat as founder mode — be direct, technical, "
            "show your work. You can discuss capabilities, limitations, and tools."
        )
        lead_phone_override = _FOUNDER_SALES_DESKTOP_PHONE
    else:
        lead_phone_override = None

    # Leo Sales desktop: mode=sales + audience=agent + X-Tracker-Token
    # (shared secret with the sales-tracker backend on port 8001; validated
    # via ``core.tracker_token_valid`` so both backends read the same env
    # var with matching dev/prod semantics).
    x_tracker = request.headers.get("x-tracker-token") or request.headers.get("X-Tracker-Token")
    if mode == "sales" and audience == "agent":
        if not tracker_token_valid(x_tracker):
            return JSONResponse(
                {"error": "sales mode requires valid X-Tracker-Token (same as sales tracker)"},
                status_code=401,
            )
        if not lead_phone_override:
            lead_phone_override = _FOUNDER_SALES_DESKTOP_PHONE
        if not user_id:
            user_id = "leo-sales-desktop"

    caps = ChannelCapabilities(
        **{**WEB_CAPABILITIES.__dict__,
           "locale": page_locale,
           "user_language_hint": user_language_hint}
    )

    try:
        result = await run_leo_chat(
            messages=[],
            mode=mode,
            raw_history=raw_msgs,
            lead_context=lead_context,
            audience=audience,
            page_locale=page_locale,
            user_language_hint=user_language_hint,
            profile_context=profile_context,
            channel="web",
            lead_phone=lead_phone_override,
            confirmed=confirmed,
            user_id=user_id,
            conversation_id=user_id,
            capabilities=caps,
            leo_messages=leo_messages,
            contractor_id=contractor_id,
        )
        reply = (result.get("reply") or "").strip()
        if not reply:
            reply = _lang_fallback(raw_msgs)

        payload: Dict[str, Any] = {"reply": reply}
        if result.get("brief_update"):
            payload["brief_update"] = result["brief_update"]
        if result.get("profile_update"):
            payload["profile_update"] = result["profile_update"]
        if result.get("quote_update"):
            payload["quote_update"] = result["quote_update"]
        ta = result.get("tool_activity")
        if ta:
            payload["tool_activity"] = ta
        if result.get("show_drawer"):
            payload["show_drawer"] = True
        if result.get("drawer_state"):
            payload["drawer_state"] = result["drawer_state"]
        cost_usd = result.get("cost_usd", 0)
        tokens = result.get("tokens", 0)
        model_used = result.get("model_used", "")
        if cost_usd or tokens:
            payload["cost_usd"] = cost_usd
            payload["tokens"] = tokens
            payload["model_used"] = model_used
        return JSONResponse(payload)
    except Exception as exc:
        logger.error("Chat failed | %s", exc, exc_info=True)
        return JSONResponse({"error": "internal error"}, status_code=500)


def _build_leo_messages(raw_msgs: list[dict]) -> list[LeoMessage]:
    """Convert raw frontend messages to LeoMessages with media attachments."""
    result: list[LeoMessage] = []
    for m in raw_msgs:
        role = m.get("role", "user")
        text = (m.get("text", "") or "").strip()
        content = m.get("content", "")

        media: list[MediaAttachment] = []
        for img in m.get("images", []):
            data = img.get("data", "")
            media_type = img.get("media_type", "image/jpeg")
            if data:
                media.append(MediaAttachment(
                    mime_type=media_type,
                    data=data,
                ))

        if not text and isinstance(content, str):
            text = content.strip()

        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text" and not text:
                        text = (part.get("text", "") or "").strip()
                    elif part.get("type") == "image_url":
                        url = part.get("image_url", {}).get("url", "")
                        if url.startswith("data:") and ";base64," in url:
                            header, b64 = url.split(";base64,", 1)
                            mime_str = header.replace("data:", "")
                            media.append(MediaAttachment(
                                mime_type=mime_str or "image/jpeg",
                                data=b64,
                            ))

        if text or media:
            result.append(LeoMessage(role=role, text=text, media=media))
    return result


def _lang_fallback(msgs: List[Dict[str, str]]) -> str:
    last = (msgs[-1].get("text", "") if msgs else "").lower()
    if any(c in last for c in ["hola", "casa", "reforma"]):
        return "Perdona, hubo un problema. Escr\u00edbeme de nuevo en un momento."
    return "Sorry, something went wrong. Try again in a moment."
