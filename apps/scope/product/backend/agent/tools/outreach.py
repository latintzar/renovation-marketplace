"""
leo_agent/tools/outreach.py — Contractor outreach and pipeline control tools.

Tools: outreach_contractor, batch_outreach, control_outreach, rank_job_responses
"""

from __future__ import annotations

import json
import logging
import os

from ..tool_utils import (
    _get_ctx_val, _record_activity, _run_async, _send_indicator,
    _get_job_by_id_async, _update_job_async, _rank_responses_async,
)

logger = logging.getLogger(__name__)


# ── Shared helpers ────────────────────────────────────────────────────

def _notify_founder_outreach(
    contractor_name: str,
    phone: str,
    source: str,
    title: str,
    location: str,
    job_id: str = "",
) -> None:
    """Send Peter a WhatsApp heads-up when an outreach message goes out."""
    ops_link = ""
    try:
        from messaging.frameworks import get_adapter
        _get_ops_token = get_adapter("job_inbox.get_ops_token", required=False)
        if _get_ops_token:
            ops_token = _get_ops_token()
            ops_link = f"\n\nhttp://127.0.0.1:18260/app/ops/{ops_token}"
    except Exception:
        pass

    note = (
        f"Outreach sent\n"
        f"{contractor_name or 'Unknown'} ({phone})\n"
        f"via {source} for: {title} in {location}"
        f"{ops_link}"
    )
    peter_phone = os.getenv("PETER_WHATSAPP", '')
    from messaging.whatsapp import send_wa_message_sync
    try:
        send_wa_message_sync(peter_phone, note, purpose="internal", do_store=False, skip_window_check=True)
    except Exception as e:
        logger.debug("Founder outreach notification failed (non-fatal): %s", e)


# ── Handlers ─────────────────────────────────────────────────────────

def _handle_outreach_contractor(args: dict, **kw) -> str:
    """Send a single WhatsApp cold outreach message to a contractor about a job."""
    phone = str(args.get("phone", "")).strip()
    contractor_name = str(args.get("contractor_name", "")).strip()
    job_id = str(args.get("job_id", "")).strip()
    source = str(args.get("source", "direct")).strip()

    if not phone or not job_id:
        return json.dumps({"ok": False, "error": "phone and job_id are required"})

    phone_digits = phone.lstrip("+").replace(" ", "").replace("-", "")
    if len(phone_digits) < 7:
        return json.dumps({"ok": False, "error": f"Invalid phone: {phone}"})

    who = contractor_name or phone_digits
    _record_activity("outreach_contractor", f"Contacting {who}…")
    _send_indicator("outreach_contractor", f"_Contacting {who} about job {job_id}…_")

    job = _run_async(_get_job_by_id_async(job_id))
    if not job:
        return json.dumps({"ok": False, "error": "Job not found"})

    brief = job.get("brief", {})

    from messaging.frameworks import get_adapter
    _send_single_outreach = get_adapter("workflows.send_single_outreach")
    _humanize_brief = get_adapter("workflows.humanize_brief")
    from messaging.whatsapp import detect_language

    lang = detect_language(phone_digits)
    humanized = _run_async(_humanize_brief(brief, lang))

    candidate = {
        "name": contractor_name,
        "telephone": phone_digits,
        "address": "",
        "profile_url": str(args.get("profile_url", "")) or None,
        "area_served": str(brief.get("location", "")),
        "source": source,
        "_digits": phone_digits,
    }

    hc_id, ok = _run_async(_send_single_outreach(
        candidate=candidate,
        job_id=job_id,
        brief=brief,
        humanized_summary=humanized,
        lang=lang,
    ))

    if ok:
        _notify_founder_outreach(
            contractor_name=contractor_name,
            phone=phone_digits,
            source=source,
            title=str(brief.get("title", "project")),
            location=str(brief.get("location", "")),
        )
        return json.dumps({
            "ok": True,
            "message": f"Message sent to {contractor_name or phone_digits}",
            "hc_id": hc_id,
        })
    else:
        return json.dumps({
            "ok": False,
            "error": "WhatsApp send failed",
            "hc_id": hc_id,
        })


def _handle_batch_outreach(args: dict, **kw) -> str:
    """Run full contractor discovery + outreach pipeline for a job."""
    _record_activity("batch_outreach")
    job_id = str(args.get("job_id", "")).strip()
    max_send = int(args.get("max_send", 0))

    if not job_id:
        return json.dumps({"ok": False, "error": "job_id is required"})

    job = _run_async(_get_job_by_id_async(job_id))
    if not job:
        return json.dumps({"ok": False, "error": "Job not found"})

    brief = job.get("brief", {})
    _trade = str(brief.get("trade", "") or brief.get("title", "")).strip()
    _loc = str(brief.get("location", "")).strip()
    _desc = f"{_trade}{f' in {_loc}' if _loc else ''}" or job_id
    _record_activity("batch_outreach", f"Discovering contractors: {_desc}…")
    _send_indicator("batch_outreach", f"_Discovering contractors: {_desc} (Houzz + Facebook)…_")

    if job.get("outreach_paused"):
        return json.dumps({"ok": False, "error": "Outreach is paused for this job. Use control_outreach to resume."})

    try:
        from messaging.frameworks import get_adapter
        run_contractor_discovery = get_adapter("workflows.run_contractor_discovery")
        result = _run_async(run_contractor_discovery(job_id=job_id, max_send=max_send))
    except Exception as e:
        logger.error("batch_outreach workflow failed: %s", e, exc_info=True)
        return json.dumps({"ok": False, "error": str(e)})

    if not result.ok and not result.sent:
        return json.dumps({
            "ok": False,
            "error": result.error or "No candidates found",
            "candidates_found": result.candidates_found,
        })

    _notify_founder_outreach(
        contractor_name=f"{result.sent} contractors (batch)",
        phone=f"{result.sent}/{result.candidates_found} sent",
        source="batch",
        title=str(job.get("brief", {}).get("title", "project")),
        location=str(job.get("brief", {}).get("location", "")),
    )

    logger.info("Batch outreach done | job=%s sent=%d failed=%d", job_id[:8], result.sent, result.failed)
    return json.dumps({
        "ok": True,
        "sent": result.sent,
        "failed": result.failed,
        "candidates_found": result.candidates_found,
        "hc_ids": result.hc_ids[:10],
    }, ensure_ascii=False)


def _handle_control_outreach(args: dict, **kw) -> str:
    """Pause, resume, or stop outreach for a specific job or all jobs."""
    _record_activity("control_outreach")
    action = str(args.get("action", "")).strip().lower()
    job_id = str(args.get("job_id", "")).strip()

    if action not in ("pause", "resume", "stop", "status"):
        return json.dumps({"ok": False, "error": "action must be one of: pause, resume, stop, status"})

    from core import sb_headers as _sb_headers, sb_key as _sb_key, sb_url as _sb_url
    import httpx as _httpx
    sb_url, sb_key = _sb_url(), _sb_key()

    def _headers(_key: str = "") -> dict:
        return _sb_headers()

    if action == "status":
        resp = _httpx.get(
            f"{sb_url}/rest/v1/jobs",
            params={"select": "id,brief,status,outreach_paused,outreach_count", "order": "created_at.desc", "limit": "20"},
            headers=_headers(sb_key),
            timeout=10,
        )
        jobs = resp.json() if resp.status_code == 200 else []
        summary = []
        for j in jobs:
            brief = j.get("brief", {})
            summary.append({
                "job_id": j["id"],
                "title": brief.get("title", "Untitled"),
                "status": j.get("status"),
                "paused": j.get("outreach_paused", False),
                "outreach_count": j.get("outreach_count", 0),
            })
        return json.dumps({"ok": True, "action": "status", "jobs": summary}, ensure_ascii=False)

    if action == "stop":
        update = {"outreach_paused": True, "status": "closed"}
    elif action == "pause":
        update = {"outreach_paused": True}
    else:
        update = {"outreach_paused": False}

    if job_id:
        resp = _httpx.patch(
            f"{sb_url}/rest/v1/jobs?id=eq.{job_id}",
            headers={**_headers(sb_key), "Prefer": "return=minimal"},
            json=update,
            timeout=10,
        )
        affected = 1 if resp.status_code in (200, 204) else 0
    else:
        filter_params = {"status": "in.(collecting,ready)"}
        resp = _httpx.patch(
            f"{sb_url}/rest/v1/jobs",
            params=filter_params,
            headers={**_headers(sb_key), "Prefer": "return=representation"},
            json=update,
            timeout=10,
        )
        affected = len(resp.json()) if resp.status_code == 200 else 0

    verb = {"pause": "Paused", "resume": "Resumed", "stop": "Stopped"}[action]
    scope = f"job {job_id[:8]}" if job_id else "all active jobs"
    logger.info("Outreach %s | %s | affected=%d", action, scope, affected)
    return json.dumps({
        "ok": True,
        "action": action,
        "affected": affected,
        "message": f"{verb} outreach for {scope} ({affected} job{'s' if affected != 1 else ''}).",
    })


def _handle_rank_job_responses(args: dict, **kw) -> str:
    """AI-rank all contractor responses for a job."""
    _record_activity("rank_job_responses")
    job_id = str(args.get("job_id", "")).strip()
    if not job_id:
        return json.dumps({"ok": False, "error": "job_id is required"})

    _send_indicator("rank_job_responses", "_Ranking contractor responses…_")

    ranked = _run_async(_rank_responses_async(job_id))
    return json.dumps({
        "ok": True,
        "ranked_count": len(ranked),
        "top_pick": ranked[0].get("contractor_name", "?") if ranked else None,
    }, ensure_ascii=False)


# ── Schemas ───────────────────────────────────────────────────────────

OUTREACH_CONTRACTOR_SCHEMA = {
    "name": "outreach_contractor",
    "description": (
        "Send a WhatsApp cold outreach message to a contractor about a job. "
        "Creates a job_response record and sends the intro message. "
        "Use after find_houzz_contractors to contact promising candidates."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "phone": {"type": "string", "description": "Contractor's phone number (with country code, no +)"},
            "contractor_name": {"type": "string", "description": "Contractor's business or personal name"},
            "job_id": {"type": "string", "description": "Job ID this outreach is for"},
            "brief_summary": {"type": "string", "description": "One-line summary of the job"},
            "source": {
                "type": "string",
                "enum": ["houzz", "facebook", "direct", "habitissimo"],
                "description": "Where we found this contractor",
            },
        },
        "required": ["phone", "job_id"],
    },
}

BATCH_OUTREACH_SCHEMA = {
    "name": "batch_outreach",
    "description": (
        "Run the full contractor discovery + outreach pipeline for a job. "
        "This is the main sales engine. Given a job_id, it: "
        "(1) searches Houzz with nearby-city expansion + multi-slug matching, "
        "(2) scrapes Facebook group posts AND comments for phone numbers and business names, "
        "(3) merges and deduplicates all candidates, "
        "(4) creates HC records with full provenance, "
        "(5) humanizes the brief for a natural WhatsApp template, "
        "(6) sends outreach messages with staggered timing. "
        "You do NOT need to call find_houzz_contractors or search_fb_groups first. "
        "Just provide the job_id."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job ID to run discovery + outreach for"},
            "max_send": {"type": "integer", "description": "Maximum number of messages to send (default: 25)"},
        },
        "required": ["job_id"],
    },
}

CONTROL_OUTREACH_SCHEMA = {
    "name": "control_outreach",
    "description": (
        "Pause, resume, or stop contractor outreach. "
        "Can target a specific job or all active jobs. "
        "'stop' pauses AND closes the job. 'pause' just pauses (can resume later). "
        "'status' shows which jobs are active/paused."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["pause", "resume", "stop", "status"],
                "description": "What to do",
            },
            "job_id": {
                "type": "string",
                "description": "Specific job ID to target (optional — omit to affect ALL active jobs)",
            },
        },
        "required": ["action"],
    },
}

RANK_JOB_RESPONSES_SCHEMA = {
    "name": "rank_job_responses",
    "description": (
        "AI-rank all contractor responses for a job. Analyzes voice transcripts, "
        "profiles, and onboarding status against the brief. Updates ai_rank and "
        "ai_commentary on each response. Call after collecting responses."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job ID to rank responses for"},
        },
        "required": ["job_id"],
    },
}


# ── Registration ──────────────────────────────────────────────────────

def register(registry) -> None:
    registry.register(
        name="outreach_contractor",
        toolset="leo-quote",
        schema=OUTREACH_CONTRACTOR_SCHEMA,
        handler=_handle_outreach_contractor,
        check_fn=lambda: True,
    )
    registry.register(
        name="batch_outreach",
        toolset="leo-quote",
        schema=BATCH_OUTREACH_SCHEMA,
        handler=_handle_batch_outreach,
        check_fn=lambda: True,
    )
    registry.register(
        name="control_outreach",
        toolset="leo-quote",
        schema=CONTROL_OUTREACH_SCHEMA,
        handler=_handle_control_outreach,
        check_fn=lambda: True,
    )
    registry.register(
        name="rank_job_responses",
        toolset="leo-quote",
        schema=RANK_JOB_RESPONSES_SCHEMA,
        handler=_handle_rank_job_responses,
        check_fn=lambda: True,
    )
    logger.debug("outreach tools registered")
