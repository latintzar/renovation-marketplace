"""
leo_agent/tool_utils.py — Shared utilities for all tool domain modules.

Provides:
  - AgentTurnState: typed dataclass for per-turn agent state
  - Thread-local context (leo_ctx, _get_state, _get_ctx_val)
  - Activity + WhatsApp indicator helpers (_record_activity, _send_indicator)
  - Async bridge (_run_async)
  - Tool output compression (_compact_tool_result)
  - Async wrappers for job_inbox (lazily imported to avoid circular deps)

All tool domain modules in leo_agent/tools/ import from here.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_TOOL_OUTPUT_CHARS = 1500  # ~375 tokens — above this we truncate

leo_ctx = threading.local()


# ---------------------------------------------------------------------------
# Typed agent turn state
# ---------------------------------------------------------------------------

@dataclass
class AgentTurnState:
    """Typed container for per-turn agent output state.

    Replaces the ad-hoc dict that was previously stored in leo_ctx.state.
    Use .to_dict() to get the legacy-compatible dict for the response builder.
    """
    brief_update: Optional[dict] = None
    profile_update: Optional[dict] = None
    quote_update: Optional[dict] = None
    tool_activity: List[dict] = field(default_factory=list)
    show_drawer: bool = False
    drawer_state: Optional[dict] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brief_update": self.brief_update,
            "profile_update": self.profile_update,
            # Expose as both "quote_update" (new) and "quote_update" (legacy compat)
            "quote_update": self.quote_update,
            "quote_update": self.quote_update,
            "tool_activity": self.tool_activity,
            "show_drawer": self.show_drawer,
            "drawer_state": self.drawer_state,
        }


def _new_state() -> Dict[str, Any]:
    """Return a fresh state dict using AgentTurnState defaults."""
    return AgentTurnState().to_dict()


def _compact_tool_result(tool_name: str, result: dict) -> dict:
    """Trim verbose tool outputs before they enter the context window."""
    output_str = json.dumps(result, ensure_ascii=False)
    if len(output_str) <= MAX_TOOL_OUTPUT_CHARS:
        return result

    list_key = None
    for key in ("results", "candidates", "data"):
        if isinstance(result.get(key), list):
            list_key = key
            break

    if list_key is None:
        logger.debug("_compact_tool_result: %s output is %d chars but no list field to trim",
                     tool_name, len(output_str))
        return result

    full_list = result[list_key]
    trimmed = full_list[:5]
    compacted = {k: v for k, v in result.items() if k != list_key}
    compacted[list_key] = trimmed
    compacted["truncated"] = True
    compacted["total_found"] = len(full_list)
    compacted["note"] = (
        f"Showing {len(trimmed)}/{len(full_list)} results. "
        "Full data is stored in Supabase/dossier."
    )
    new_size = len(json.dumps(compacted, ensure_ascii=False))
    logger.debug("_compact_tool_result: %s compressed %d → %d chars (%d→%d items)",
                 tool_name, len(output_str), new_size, len(full_list), len(trimmed))
    return compacted


def _get_state() -> Dict[str, Any]:
    """Return the thread-local state dict, creating it if needed."""
    if not hasattr(leo_ctx, "state"):
        leo_ctx.state = _new_state()
    return leo_ctx.state


def _get_ctx_val(key: str, default: Any = "") -> Any:
    """Read a value from the thread-local context (set by run_leo_chat)."""
    if not hasattr(leo_ctx, "ctx"):
        return default
    return leo_ctx.ctx.get(key, default)


def _record_activity(name: str, label: str = "") -> None:
    labels = {
        "update_brief": "Updating brief…",
        "update_profile": "Updating profile…",
        "update_quote": "Updating quote…",
        "save_signup": "Saving signup…",
        "whatsapp_handoff": "Connecting WhatsApp…",
        "send_whatsapp": "Sending WhatsApp message…",
        "send_email": "Sending email…",
        "lookup_price": "Searching pricing data…",
        "lookup_product": "Searching product catalog…",
        "search_spanish_law": "Searching Spanish legislation…",
        "get_boe_norm_text": "Fetching BOE text…",
        "search_eu_law": "Searching EU legislation…",
        "create_job": "Creating job…",
        "start_job_intake": "Starting homeowner intake…",
        "find_houzz_contractors": "Searching Houzz…",
        "batch_outreach": "Running contractor discovery…",
        "outreach_contractor": "Sending outreach message…",
        "control_outreach": "Updating outreach…",
        "founder_dashboard": "Loading dashboard…",
        "rank_job_responses": "Ranking contractor responses…",
        "enrich_contractor": "Enriching contractor profile…",
        "create_page": "Creating page…",
        "search_fb_groups": "Searching Facebook groups…",
        "search_forums": "Searching forums…",
        "propose_skill_change": "Proposing skill change…",
        "skill_manage": "Managing skills…",
        "request_human": "Escalating to human…",
        "set_drawer": "Updating drawer…",
    }
    _get_state().setdefault("tool_activity", []).append(
        {"tool": name, "label": label or labels.get(name, f"Running {name}…")}
    )


def _send_indicator(tool_name: str, message: str = "") -> None:
    """Send a human-readable italic indicator via WhatsApp (once per turn).

    On web the label is shown in the tool_activity panel; on WhatsApp we send
    an italic message so the user sees what Leo is doing while tools run.
    Only fires once per Hermes turn (deduplicated by _indicator_sent flag).
    """
    state = _get_state()
    if state.get("_indicator_sent"):
        return
    state["_indicator_sent"] = True

    ctx = getattr(leo_ctx, "ctx", {})
    phone = ctx.get("lead_phone", "")
    if not phone:
        return

    defaults = {
        "lookup_price": "_Checking pricing data…_",
        "lookup_product": "_Searching product catalog…_",
        "search_spanish_law": "_Searching Spanish legislation…_",
        "search_eu_law": "_Searching EU legislation…_",
        "find_houzz_contractors": "_Searching Houzz directory…_",
        "search_fb_groups": "_Searching Facebook groups…_",
        "search_forums": "_Searching Forocoches, Mediavida, Reddit…_",
        "batch_outreach": "_Running contractor discovery…_",
        "start_job_intake": "_Starting homeowner intake (discovery + enrichment)…_",
        "enrich_contractor": "_Enriching contractor profile…_",
        "rank_job_responses": "_Ranking contractor responses…_",
        "founder_dashboard": "_Loading dashboard…_",
        "outreach_contractor": "_Contacting contractor…_",
    }
    msg_text = message or defaults.get(tool_name)
    if not msg_text:
        return

    from messaging.whatsapp import send_wa_message_sync
    try:
        send_wa_message_sync(phone, msg_text, purpose="internal", do_store=False, skip_window_check=True)
        logger.debug("Sent indicator | tool=%s | phone=%s", tool_name, phone[:8])
    except Exception as e:
        logger.debug("Indicator send failed (non-fatal) | %s", e)


def _send_searching_indicator(tool_name: str) -> None:
    """Backward-compatible alias for _send_indicator."""
    _send_indicator(tool_name)


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _run_async(coro):
    """Run an async coroutine from a sync Hermes tool handler."""
    from core.resilience import run_sync
    return run_sync(coro, timeout=30)


# ── Async wrappers for job_inbox (lookup via host adapter registry) ──
# The host app registers these functions at startup; see
# :mod:`._adapters`.

async def _create_job_async(**kwargs):
    from messaging.frameworks import get_adapter
    return await get_adapter("job_inbox.create_job")(**kwargs)

async def _get_job_by_id_async(job_id: str):
    from messaging.frameworks import get_adapter
    return await get_adapter("job_inbox.get_job_by_id")(job_id)

async def _update_job_async(job_id: str, updates: dict):
    from messaging.frameworks import get_adapter
    return await get_adapter("job_inbox.update_job")(job_id, updates)

async def _add_response_async(job_id: str, data: dict):
    from messaging.frameworks import get_adapter
    return await get_adapter("job_inbox.add_response")(job_id, data)

async def _rank_responses_async(job_id: str):
    from messaging.frameworks import get_adapter
    rank_responses = get_adapter("job_inbox.rank_responses")
    return await rank_responses(job_id)
