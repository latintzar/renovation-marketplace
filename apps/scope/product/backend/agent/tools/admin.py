"""
leo_agent/tools/admin.py — Founder ops and agent self-improvement tools.

Tools: founder_dashboard, propose_skill_change, skill_manage (gated), create_page
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from ..tool_utils import _get_ctx_val, _record_activity, _run_async, _send_indicator

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────

def _skill_payload_from_skill_manage_args(args: dict) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k in ("old_string", "new_string", "file_path", "file_content", "category", "replace_all"):
        if k in args and args[k] is not None:
            out[k] = args[k]
    return out


# ── Handlers ─────────────────────────────────────────────────────────

def _handle_founder_dashboard(args: dict, **kw) -> str:
    """Founder-only: return a full ops snapshot (signups, jobs, pipeline, replies)."""
    _record_activity("founder_dashboard")

    caller_phone = str(_get_ctx_val("lead_phone", "")).replace("whatsapp:", "").lstrip("+").replace(" ", "").replace("-", "")
    from ..peter_notify import FOUNDER_WA_DIGITS
    if caller_phone not in FOUNDER_WA_DIGITS:
        return json.dumps({"ok": False, "error": "This tool is only available to the founder."})

    section = str(args.get("section", "overview")).strip().lower()
    _send_indicator("founder_dashboard", f"_Loading dashboard ({section})…_")

    from core import sb_headers as _sb_headers, sb_key as _sb_key, sb_url as _sb_url
    import httpx as _httpx

    sb_url, sb_key = _sb_url(), _sb_key()

    def _headers(_key: str = "") -> dict:
        return _sb_headers()
    if not sb_url or not sb_key:
        return json.dumps({"ok": False, "error": "Database not configured"})

    result: Dict[str, Any] = {"ok": True, "section": section}

    def _get(table: str, params: dict) -> list:
        try:
            r = _httpx.get(
                f"{sb_url}/rest/v1/{table}",
                params=params,
                headers=_headers(sb_key),
                timeout=10,
            )
            return r.json() if r.status_code == 200 else []
        except Exception as e:
            logger.warning("founder_dashboard: failed to fetch %s: %s", table, e)
            return []

    if section in ("overview", "signups"):
        leads = _get("cs_leads", {
            "select": "id,name,whatsapp,location,audience,source,created_at",
            "order": "created_at.desc",
            "limit": "20",
        })
        result["signups"] = {
            "total": len(leads),
            "recent": [
                {
                    "name": l.get("name") or "(anonymous)",
                    "phone": l.get("whatsapp", ""),
                    "location": l.get("location", ""),
                    "audience": l.get("audience", ""),
                    "source": l.get("source", ""),
                    "when": l.get("created_at", ""),
                }
                for l in leads[:10]
            ],
        }

        landing = _get("landing_leads", {
            "select": "id,job_description,phone,location,created_at",
            "order": "created_at.desc",
            "limit": "10",
        })
        result["landing_leads"] = {
            "total": len(landing),
            "recent": [
                {
                    "description": (l.get("job_description") or "")[:120],
                    "phone": l.get("phone", ""),
                    "location": l.get("location", ""),
                    "when": l.get("created_at", ""),
                }
                for l in landing[:5]
            ],
        }

    if section in ("overview", "pipeline"):
        jobs = _get("jobs", {
            "select": "id,brief,status,outreach_count,outreach_paused,homeowner_phone,created_at",
            "order": "created_at.desc",
            "limit": "20",
        })
        responses = _get("job_responses", {
            "select": "id,job_id,contractor_name,contractor_phone,source,outreach_stage,reaction,voice_transcript,onboarding_complete,houzz_profile_url,created_at",
            "order": "created_at.desc",
            "limit": "100",
        })

        responses_by_job: Dict[str, list] = {}
        for r in responses:
            responses_by_job.setdefault(r.get("job_id", ""), []).append(r)

        pipeline_stages: Dict[str, int] = {}
        for r in responses:
            s = r.get("outreach_stage", "discovered")
            pipeline_stages[s] = pipeline_stages.get(s, 0) + 1

        job_summaries = []
        for j in jobs:
            jid = j["id"]
            brief = j.get("brief") or {}
            resps = responses_by_job.get(jid, [])
            replied = [r for r in resps if r.get("voice_transcript") or r.get("reaction")]
            job_summaries.append({
                "job_id": jid[:8],
                "title": brief.get("title", "Untitled"),
                "location": brief.get("location", ""),
                "status": j.get("status", ""),
                "paused": j.get("outreach_paused", False),
                "outreach_count": j.get("outreach_count", 0),
                "total_responses": len(resps),
                "replied": len(replied),
                "contractors_who_replied": [
                    {
                        "name": r.get("contractor_name", "?"),
                        "source": r.get("source", ""),
                        "stage": r.get("outreach_stage", ""),
                        "snippet": (r.get("reaction") or r.get("voice_transcript") or "")[:80],
                    }
                    for r in replied[:5]
                ],
            })

        result["pipeline"] = {
            "total_jobs": len(jobs),
            "total_outreach": sum(j.get("outreach_count", 0) for j in jobs),
            "total_responses": len(responses),
            "stages": pipeline_stages,
            "jobs": job_summaries[:10],
        }

        try:
            from messaging.frameworks import get_adapter
            _get_ops_token = get_adapter("job_inbox.get_ops_token", required=False)
            if _get_ops_token:
                ops_token = _get_ops_token()
                result["ops_url"] = f"http://127.0.0.1:18260/app/ops/{ops_token}"
        except Exception:
            pass

    if section in ("overview", "conversations"):
        wa_msgs = _get("whatsapp_messages", {
            "select": "phone_number,role,created_at",
            "order": "created_at.desc",
            "limit": "50",
        })
        unique_phones: Dict[str, str] = {}
        for m in wa_msgs:
            ph = m.get("phone_number", "")
            if ph and ph not in unique_phones:
                unique_phones[ph] = m.get("created_at", "")
        result["active_conversations"] = {
            "unique_contacts_last_50_msgs": len(unique_phones),
            "recent_phones": list(unique_phones.items())[:10],
        }

    logger.info("founder_dashboard | section=%s | caller=%s", section, caller_phone[:6])
    return json.dumps(result, ensure_ascii=False, default=str)


def _handle_skill_manage_gated(args: dict, **kw) -> str:
    """skill_manage is gated: proposals go to Supabase + founder WhatsApp."""
    _record_activity("skill_manage")
    from ..peter_notify import notify_founder_skill_proposal, store_skill_proposal

    action = str(args.get("action", "")).strip()
    name = str(args.get("name", "")).strip()
    if not action or not name:
        return json.dumps({"ok": False, "error": "action and name are required"}, ensure_ascii=False)

    reason = (
        "Agent called skill_manage (gated). "
        "Approve via WhatsApp to apply to ~/.hermes/skills."
    )
    content = str(args.get("content", "") or "")
    payload = _skill_payload_from_skill_manage_args(args)
    conv = str(_get_ctx_val("conversation_id", "") or "")

    stored = _run_async(
        store_skill_proposal(
            skill_name=name,
            action=action,
            reason=reason,
            content=content,
            conversation_id=conv,
            skill_payload=payload,
        )
    )
    if not stored.get("ok"):
        return json.dumps({"ok": False, "error": stored.get("error", "store_failed")}, ensure_ascii=False)

    pid = str(stored.get("id", ""))
    pc = int(stored.get("pattern_count") or 1)
    preview = content[:400] if action in ("create", "edit") else ""

    _run_async(
        notify_founder_skill_proposal(
            proposal_id=pid,
            skill_name=name,
            action=action,
            reason=reason,
            pattern_count=pc,
            content_preview=preview,
        )
    )

    return json.dumps(
        {
            "ok": True,
            "message": (
                "Proposal sent to the founder for WhatsApp review. "
                "It will be applied with skill_manage after approval — tell the user nothing is broken."
            ),
            "proposal_id": pid,
        },
        ensure_ascii=False,
    )


def _handle_propose_skill_change(args: dict, **kw) -> str:
    """Explicit skill proposal with a clear reason."""
    _record_activity("propose_skill_change")
    from ..peter_notify import notify_founder_skill_proposal, store_skill_proposal

    proposal_type = str(args.get("proposal_type", "")).strip().lower()
    skill_name = str(args.get("skill_name", "")).strip()
    reason = str(args.get("reason", "")).strip()
    content = str(args.get("proposed_content", "") or "")
    if proposal_type not in ("create", "edit", "patch", "delete", "write_file", "remove_file"):
        return json.dumps(
            {"ok": False, "error": "proposal_type must be create|edit|patch|delete|write_file|remove_file"},
            ensure_ascii=False,
        )
    if not skill_name or not reason:
        return json.dumps({"ok": False, "error": "skill_name and reason are required"}, ensure_ascii=False)

    payload: Dict[str, Any] = {}
    if args.get("patch_old_string") is not None:
        payload["old_string"] = str(args.get("patch_old_string", ""))
    if args.get("patch_new_string") is not None:
        payload["new_string"] = str(args.get("patch_new_string", ""))
    if args.get("file_path"):
        payload["file_path"] = str(args.get("file_path", ""))
    if args.get("file_content") is not None:
        payload["file_content"] = str(args.get("file_content", ""))
    if args.get("category"):
        payload["category"] = str(args.get("category", ""))
    if args.get("replace_all") is not None:
        payload["replace_all"] = bool(args.get("replace_all", False))

    conv = str(_get_ctx_val("conversation_id", "") or "")
    stored = _run_async(
        store_skill_proposal(
            skill_name=skill_name,
            action=proposal_type,
            reason=reason,
            content=content,
            conversation_id=conv,
            skill_payload=payload,
        )
    )
    if not stored.get("ok"):
        return json.dumps({"ok": False, "error": stored.get("error", "store_failed")}, ensure_ascii=False)

    pid = str(stored.get("id", ""))
    pc = int(stored.get("pattern_count") or 1)
    preview = content[:400] if proposal_type in ("create", "edit") else ""

    _run_async(
        notify_founder_skill_proposal(
            proposal_id=pid,
            skill_name=skill_name,
            action=proposal_type,
            reason=reason,
            pattern_count=pc,
            content_preview=preview,
        )
    )

    return json.dumps(
        {
            "ok": True,
            "message": "Proposal recorded and sent to the founder on WhatsApp for approval.",
            "proposal_id": pid,
        },
        ensure_ascii=False,
    )


def _handle_create_page(args: dict, **kw) -> str:
    """Generate an ad-hoc branded HTML page and store it in Supabase."""
    import secrets
    import httpx as _httpx
    import os as _os

    title = str(args.get("title", "Leo — Results")).strip() or "Leo — Results"
    html_body = str(args.get("html_body", "")).strip()
    full_html = str(args.get("full_html", "")).strip()
    expires_days = int(args.get("expires_days", 30))

    if not html_body and not full_html:
        return json.dumps({"ok": False, "error": "html_body or full_html is required"})

    if full_html:
        html_content = full_html
    else:
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@1,8..60,400;0,8..60,400;0,8..60,500&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --terra: #C4602A;
    --ink: #1C1917;
    --cream: #FAF8F4;
    --muted: #78716C;
    --border: #E7E5E4;
    --card: #FFFFFF;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--cream);
    color: var(--ink);
    font-family: 'Inter', sans-serif;
    font-size: 15px;
    line-height: 1.6;
    min-height: 100vh;
  }}
  header {{
    background: var(--ink);
    padding: 1rem 1.5rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }}
  header .logo {{
    font-family: 'Source Serif 4', serif;
    font-style: italic;
    font-size: 1.4rem;
    color: var(--terra);
    line-height: 1;
  }}
  header h1 {{
    font-size: 0.9rem;
    font-weight: 500;
    color: #A8A29E;
    letter-spacing: 0.01em;
  }}
  main {{
    max-width: 860px;
    margin: 0 auto;
    padding: 1.5rem 1rem 3rem;
  }}
  .cards {{ display: flex; flex-direction: column; gap: 0.75rem; }}
  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.25rem;
  }}
  .card a {{ color: var(--terra); text-decoration: none; word-break: break-word; }}
  .card a:hover {{ text-decoration: underline; }}
  .card .card-title {{ font-weight: 600; font-size: 0.95rem; margin-bottom: 0.25rem; }}
  .card .card-meta {{ font-size: 0.8rem; color: var(--muted); margin-bottom: 0.4rem; }}
  .card .card-snippet {{ font-size: 0.88rem; color: #57534E; }}
  .section-title {{ font-weight: 600; font-size: 0.85rem; letter-spacing: 0.05em; text-transform: uppercase; color: var(--muted); margin: 1.5rem 0 0.5rem; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; }}
  th {{ background: var(--ink); color: white; text-align: left; padding: 0.6rem 1rem; font-size: 0.8rem; font-weight: 500; }}
  td {{ padding: 0.6rem 1rem; font-size: 0.85rem; border-bottom: 1px solid var(--border); }}
  tr:last-child td {{ border-bottom: none; }}
  .empty {{ color: var(--muted); font-size: 0.9rem; padding: 1rem 0; }}
  footer {{
    text-align: center;
    font-size: 0.78rem;
    color: var(--muted);
    padding: 2rem 1rem 1rem;
    border-top: 1px solid var(--border);
    margin-top: 2rem;
  }}
</style>
</head>
<body>
<header>
  <span class="logo">Leo</span>
  <h1>{title}</h1>
</header>
<main>
{html_body}
</main>
<footer>Generated by Leo &middot; leo.casa</footer>
</body>
</html>"""

    token = secrets.token_urlsafe(10)

    from datetime import datetime, timezone, timedelta
    expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat()

    sb_url = _os.getenv("SUPABASE_URL") or _os.getenv("NEXT_PUBLIC_SUPABASE_URL") or ""
    sb_key = (
        _os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or _os.getenv("SUPABASE_SERVICE_KEY")
        or ""
    )
    if not sb_url or not sb_key:
        try:
            from config import settings
            sb_url = settings.SUPABASE_URL or ""
            sb_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or ""
        except Exception:
            pass

    if not sb_url or not sb_key:
        return json.dumps({"ok": False, "error": "Supabase credentials not configured"})

    try:
        resp = _httpx.post(
            f"{sb_url}/rest/v1/generated_pages",
            headers={
                "apikey": sb_key,
                "Authorization": f"Bearer {sb_key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json={
                "token": token,
                "title": title,
                "html_content": html_content,
                "expires_at": expires_at,
            },
            timeout=10,
        )
        if resp.status_code not in (200, 201):
            logger.error("create_page Supabase error | status=%d | %s", resp.status_code, resp.text[:200])
            return json.dumps({"ok": False, "error": f"DB write failed: {resp.status_code}"})
    except Exception as exc:
        logger.error("create_page network error: %s", exc)
        return json.dumps({"ok": False, "error": str(exc)})

    page_url = f"http://127.0.0.1:18261/p/{token}"
    logger.info("create_page | token=%s | title=%s | expires=%s | url=%s", token, title, expires_at, page_url)
    _record_activity("create_page", f"Page created: {title}")
    return json.dumps({"ok": True, "url": page_url, "token": token})


# ── Schemas ───────────────────────────────────────────────────────────

FOUNDER_DASHBOARD_SCHEMA = {
    "name": "founder_dashboard",
    "description": (
        "Founder-only: get a full operational snapshot of Leo. "
        "Covers signups, landing leads, contractor pipeline, outreach status, and replies. "
        "Use when Peter asks 'did anyone sign up?', 'how are we doing?', 'any replies?', etc. "
        "Only works for the founder — returns an error for all other callers."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "section": {
                "type": "string",
                "enum": ["overview", "signups", "pipeline", "conversations"],
                "description": (
                    "'overview' (default) = everything, "
                    "'signups' = just cs_leads + landing_leads, "
                    "'pipeline' = jobs + outreach + responses, "
                    "'conversations' = recent WhatsApp activity"
                ),
            },
        },
        "required": [],
    },
}

PROPOSE_SKILL_CHANGE_SCHEMA = {
    "name": "propose_skill_change",
    "description": (
        "Propose creating or changing a Hermes skill (procedural how-to knowledge). "
        "Does NOT apply immediately — the founder approves via WhatsApp, then the system runs skill_manage. "
        "Use when you want a durable playbook for recurring Leo Scope situations. "
        "Prefer this over hoping skill_manage runs unreviewed."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "proposal_type": {
                "type": "string",
                "enum": ["create", "edit", "patch", "delete", "write_file", "remove_file"],
                "description": "Same as skill_manage action",
            },
            "skill_name": {"type": "string", "description": "Skill directory name (lowercase, hyphens ok)"},
            "reason": {"type": "string", "description": "Why this helps homeowners/pros or Leo ops"},
            "proposed_content": {
                "type": "string",
                "description": "Full SKILL.md for create/edit; optional context for other actions",
            },
            "patch_old_string": {"type": "string"},
            "patch_new_string": {"type": "string"},
            "file_path": {"type": "string"},
            "file_content": {"type": "string"},
            "category": {"type": "string"},
            "replace_all": {"type": "boolean"},
        },
        "required": ["proposal_type", "skill_name", "reason"],
    },
}

CREATE_PAGE_SCHEMA = {
    "name": "create_page",
    "description": (
        "Generate a branded HTML page and get a live URL instantly. "
        "No deploy needed — the page is live at http://127.0.0.1:18261/p/<token> the moment this returns. "
        "Use when results are too long for WhatsApp (search results, tables, lists, reports). "
        "Pass `html_body` with the page content as HTML — Leo wraps it in the brand shell. "
        "Or pass `full_html` to supply the entire document. "
        "Pages expire after 30 days by default."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Page title shown in the header and browser tab"},
            "html_body": {
                "type": "string",
                "description": "HTML for the page body. Leo wraps this in the brand shell.",
            },
            "full_html": {
                "type": "string",
                "description": "Complete HTML document (must start with <!DOCTYPE html>).",
            },
            "expires_days": {
                "type": "integer",
                "description": "Days until the page expires (default 30, max 365)",
            },
        },
        "required": ["title"],
    },
}


# ── Registration ──────────────────────────────────────────────────────

def register(registry) -> None:
    registry.register(
        name="founder_dashboard",
        toolset="leo-quote",
        schema=FOUNDER_DASHBOARD_SCHEMA,
        handler=_handle_founder_dashboard,
        check_fn=lambda: True,
    )
    registry.register(
        name="propose_skill_change",
        toolset="leo-quote",
        schema=PROPOSE_SKILL_CHANGE_SCHEMA,
        handler=_handle_propose_skill_change,
        check_fn=lambda: True,
    )
    registry.register(
        name="create_page",
        toolset="leo-quote",
        schema=CREATE_PAGE_SCHEMA,
        handler=_handle_create_page,
        check_fn=lambda: True,
    )
    logger.debug("admin tools registered")


def register_skill_manage(registry) -> None:
    """Register the gated skill_manage tool.

    Called by the host at startup after ``skill_manager_tool`` loads and
    registers its schema under adapter ``skill_manager.schema``.
    """
    from messaging.frameworks import get_adapter

    SKILL_MANAGE_SCHEMA = get_adapter("skill_manager.schema", required=False)
    if SKILL_MANAGE_SCHEMA is None:
        logger.warning(
            "register_skill_manage skipped — no 'skill_manager.schema' adapter registered"
        )
        return

    registry.register(
        name="skill_manage",
        toolset="leo-quote",
        schema=SKILL_MANAGE_SCHEMA,
        handler=_handle_skill_manage_gated,
        check_fn=lambda: True,
    )
    logger.debug("skill_manage (gated) registered")
