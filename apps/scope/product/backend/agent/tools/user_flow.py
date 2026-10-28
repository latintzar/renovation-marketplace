"""
leo_agent/tools/user_flow.py — User onboarding and job flow tools.

Tools: save_signup, whatsapp_handoff, create_job, start_job_intake
"""

from __future__ import annotations

import json
import logging

from ..tool_utils import (
    _get_ctx_val, _record_activity, _run_async, _send_indicator,
    _create_job_async,
)

logger = logging.getLogger(__name__)


# ── Handlers ─────────────────────────────────────────────────────────

def _handle_save_signup(args: dict, **kw) -> str:
    _record_activity("save_signup")
    from ..peter_notify import save_signup

    raw_history = _get_ctx_val("raw_history", None)
    source_tag = _get_ctx_val("source_tag", "leo_chat")
    result = _run_async(save_signup(
        args.get("name", ""),
        args.get("whatsapp", ""),
        args.get("location", ""),
        source_tag,
        chat_summary=args.get("chat_summary", ""),
        chat_history=raw_history,
    ))
    return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)


def _handle_whatsapp_handoff(args: dict, **kw) -> str:
    _record_activity("whatsapp_handoff")
    from ..peter_notify import whatsapp_handoff

    audience = _get_ctx_val("audience", "homeowner")
    result = _run_async(whatsapp_handoff(
        args.get("name", ""),
        args.get("whatsapp", ""),
        args.get("lang", "es"),
        audience=audience,
    ))
    return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)


def _handle_create_job(args: dict, **kw) -> str:
    """Create a job from a homeowner brief and return the inbox token."""
    _record_activity("create_job")
    brief = args.get("brief", {})
    phone = str(args.get("homeowner_phone", "") or _get_ctx_val("lead_phone", "")).strip()
    user_id = str(args.get("homeowner_user_id", "") or _get_ctx_val("conversation_id", "")).strip()
    photos = args.get("brief_photos", [])

    if not brief or (not brief.get("title") and not brief.get("description")):
        return json.dumps({"ok": False, "error": "brief must have at least title or description"})

    result = _run_async(_create_job_async(
        brief=brief,
        homeowner_phone=phone,
        homeowner_user_id=user_id,
        brief_photos=photos,
    ))
    return json.dumps({
        "ok": True,
        "job_id": result.get("id"),
        "inbox_token": result.get("inbox_token"),
        "inbox_url": f"http://127.0.0.1:18260/app/inbox/{result.get('inbox_token')}",
    }, ensure_ascii=False)


def _handle_start_job_intake(args: dict, **kw) -> str:
    """Homeowner intake pipeline — Bar 1 met, fire discovery + enrichment."""
    _record_activity("start_job_intake")
    brief = args.get("brief", {})
    phone = str(args.get("homeowner_phone", "") or _get_ctx_val("lead_phone", "")).strip()
    photos = args.get("photos") or []

    if not brief:
        return json.dumps({"ok": False, "error": "brief is required"})

    trade = str(brief.get("trade") or brief.get("title") or "").strip()
    location = str(brief.get("location") or "").strip()

    if not trade:
        return json.dumps({"ok": False, "error": "Bar 1 not met — brief.trade (or brief.title) is required"})
    if not location:
        return json.dumps({"ok": False, "error": "Bar 1 not met — brief.location is required"})

    _record_activity(
        "start_job_intake",
        f"Starting intake: {trade} in {location} — creating job, firing discovery + enrichment…",
    )
    _send_indicator(
        "start_job_intake",
        f"_Starting homeowner intake: {trade} in {location} (discovery + enrichment in parallel)…_",
    )

    user_id = str(_get_ctx_val("conversation_id", "") or "").strip()
    try:
        job_row = _run_async(_create_job_async(
            brief=brief,
            homeowner_phone=phone,
            homeowner_user_id=user_id,
            brief_photos=photos,
        ))
    except Exception as exc:
        logger.error("start_job_intake | create_job failed: %s", exc, exc_info=True)
        return json.dumps({"ok": False, "error": f"Failed to create job: {exc}"})

    job_id = job_row.get("id", "")
    inbox_token = job_row.get("inbox_token", "")

    if not job_id:
        return json.dumps({"ok": False, "error": "Job created but no id returned"})

    logger.info("start_job_intake | job created | job=%s", job_id[:8])

    try:
        from messaging.frameworks import get_adapter
        run_brief_intake = get_adapter("workflows.run_brief_intake")
        result = _run_async(run_brief_intake(
            job_id=job_id,
            homeowner_phone=phone,
            brief=brief,
            photos=photos,
        ))
    except Exception as exc:
        logger.error("start_job_intake | brief_intake failed: %s", exc, exc_info=True)
        return json.dumps({
            "ok": False,
            "job_id": job_id,
            "inbox_token": inbox_token,
            "error": f"Intake pipeline failed: {exc}",
        })

    priority = result.enrichment_priority
    from ..ephemeral_context import ENRICHMENT_ASKS
    next_ask = ENRICHMENT_ASKS.get(priority, "") if priority else ""

    logger.info(
        "start_job_intake | DONE | job=%s | discovery_sent=%d | gaps=%s | priority=%s",
        job_id[:8], result.discovery_sent, result.enrichment_gaps, priority,
    )

    return json.dumps({
        "ok": result.ok,
        "job_id": job_id,
        "inbox_token": inbox_token,
        "inbox_url": f"http://127.0.0.1:18260/app/inbox/{inbox_token}",
        "discovery_sent": result.discovery_sent,
        "enrichment_gaps": result.enrichment_gaps,
        "enrichment_priority": priority,
        "next_ask": next_ask,
        "error": result.error or None,
    }, ensure_ascii=False)


# ── Schemas ───────────────────────────────────────────────────────────

SAVE_SIGNUP_SCHEMA = {
    "name": "save_signup",
    "description": (
        "Save the user's early access signup info once you've collected their "
        "name, WhatsApp number, and location. Call this silently."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "User's actual name"},
            "whatsapp": {"type": "string", "description": "WhatsApp number with + prefix"},
            "location": {"type": "string", "description": "Where they live"},
            "chat_summary": {"type": "string", "description": "2-4 sentence handover summary"},
        },
        "required": ["name", "whatsapp", "location", "chat_summary"],
    },
}

WHATSAPP_HANDOFF_SCHEMA = {
    "name": "whatsapp_handoff",
    "description": (
        "Send the user a WhatsApp message so they can continue chatting there. "
        "Call as soon as you have their number. "
        "If result says 'sent', tell them to check WhatsApp. "
        "If result has a wa.me link, include that URL in your reply."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "User's name"},
            "whatsapp": {"type": "string", "description": "Their WhatsApp number (with country code)"},
            "lang": {"type": "string", "description": "Detected language: 'es' or 'en'"},
        },
        "required": ["name", "whatsapp"],
    },
}

CREATE_JOB_SCHEMA = {
    "name": "create_job",
    "description": (
        "Create a new contractor discovery job from a homeowner's brief. "
        "Returns a job_id and an inbox_url the homeowner can use to see responses. "
        "Call this after completing a homeowner brief via update_brief, when they want Leo to find contractors."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "brief": {
                "type": "object",
                "description": "The job brief object (title, description, location, urgency, etc.)",
            },
            "homeowner_phone": {
                "type": "string",
                "description": "Homeowner's phone number (auto-filled from context if available)",
            },
            "homeowner_user_id": {
                "type": "string",
                "description": "Homeowner's user/session ID",
            },
            "brief_photos": {
                "type": "array",
                "items": {"type": "string"},
                "description": "URLs of photos the homeowner shared",
            },
        },
        "required": ["brief"],
    },
}

START_JOB_INTAKE_SCHEMA = {
    "name": "start_job_intake",
    "description": (
        "Homeowner intake pipeline. Call this the MOMENT Bar 1 is met: trade + location known. "
        "DO NOT wait for a complete brief — discovery starts with just trade + location. "
        "Creates the job, fires contractor discovery (Houzz + Facebook) in the background, "
        "and writes enrichment signals so you know what to ask next (photos first, then scope details). "
        "After calling this, continue the conversation naturally — ask for the top enrichment gap. "
        "The brief canvas builds up as the homeowner replies. "
        "Returns: job_id, inbox_token, discovery_sent (contractors contacted), "
        "enrichment_gaps (ordered list of what's still missing), "
        "enrichment_priority (the single most important thing to ask for next), "
        "next_ask (exact suggested prompt for the priority gap)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "brief": {
                "type": "object",
                "description": (
                    "Current brief — MUST have trade/title + location (Bar 1). "
                    "Include any other fields already known (description, urgency, etc.)."
                ),
            },
            "homeowner_phone": {
                "type": "string",
                "description": "Homeowner's E.164 phone number (e.g. '+34612345678'). Optional — inferred from session if absent.",
            },
            "photos": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Any photo URLs already received in this conversation.",
            },
        },
        "required": ["brief"],
    },
}


# ── Registration ──────────────────────────────────────────────────────

def register(registry) -> None:
    registry.register(
        name="save_signup",
        toolset="leo-quote",
        schema=SAVE_SIGNUP_SCHEMA,
        handler=_handle_save_signup,
        check_fn=lambda: True,
    )
    registry.register(
        name="whatsapp_handoff",
        toolset="leo-quote",
        schema=WHATSAPP_HANDOFF_SCHEMA,
        handler=_handle_whatsapp_handoff,
        check_fn=lambda: True,
    )
    registry.register(
        name="create_job",
        toolset="leo-quote",
        schema=CREATE_JOB_SCHEMA,
        handler=_handle_create_job,
        check_fn=lambda: True,
    )
    registry.register(
        name="start_job_intake",
        toolset="leo-quote",
        schema=START_JOB_INTAKE_SCHEMA,
        handler=_handle_start_job_intake,
        check_fn=lambda: True,
    )
    logger.debug("user_flow tools registered")
