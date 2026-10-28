"""
Leo Quote agent — persistent Hermes AIAgent pool.

Each conversation (keyed by phone number or lead_id) gets a long-lived
AIAgent instance. This enables Hermes's built-in context compression,
prompt caching, and session tracking instead of rebuilding from scratch
on every message.

LLM MODEL REFERENCE — use these IDs, never invent model names.

Bedrock (primary):
  Claude Sonnet 4.6  →  "us.anthropic.claude-sonnet-4-6"           (CS chat, WA auto-reply)
  Claude Opus 4.6    →  "us.anthropic.claude-opus-4-6-v1"           (image analysis, translations)
  Claude Haiku 4.5   →  "us.anthropic.claude-haiku-4-5-20251001-v1:0"  (fallback, transcript polish default)
  DeepSeek V3.2      →  "deepseek.v3.2"                             (profile structuring, 128k ctx, cheap)
  Qwen3 80B          →  "qwen.qwen3-next-80b-a3b"                   (large context text)
  Qwen3 32B          →  "qwen.qwen3-32b-v1:0"                       (cheap text formatting, 32k ctx)
  DeepSeek R1        →  "deepseek.r1-v1:0"                          (reasoning-heavy, chain-of-thought)
  Qwen3 VL 235B      →  "qwen.qwen3-vl-235b-a22b"                   (vision + text)

Gemini (via gemini_client.py aliases):
  "pro"        →  gemini-3.1-pro-preview   (complex reasoning, photo analysis)
  "flash"      →  gemini-3-flash-preview   (fast text)
  "flash-lite" →  gemini-2.5-flash-lite    (simple tasks)
  "pro-image"  →  gemini-2.5-flash-image   (image generation)

  DOES NOT EXIST: gemini-2.0-pro, gemini-2.0-flash, gemini-2.5-pro-preview

Transcript polish (transcript_polish.py): default = Claude Haiku 4.5 via invoke_model.
  Override with TRANSCRIPT_POLISH_MODEL env var. Other Bedrock models use Converse API.

Gemini auth: key file fifth-incentive-471523-b1-09ed26b7c011.json (project root).
  Project: fifth-incentive-471523-b1, Location: us-central1.
  Env vars: GOOGLE_CLOUD_PROJECT_ID, GOOGLE_CLOUD_LOCATION, GOOGLE_APPLICATION_CREDENTIALS.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

from messaging import (
    ChannelCapabilities,
    LeoMessage,
    MediaAttachment,
    WEB_CAPABILITIES,
    WHATSAPP_CAPABILITIES,
)
from .ephemeral_context import build_turn_context

logger = logging.getLogger(__name__)

LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL", "http://127.0.0.1:4000/v1")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "sk-litellm-local")
PRIMARY_MODEL = os.getenv("LEO_PRIMARY_MODEL", "anthropic/claude-sonnet-4.6")
FALLBACK_MODEL = os.getenv("LEO_FALLBACK_MODEL", "anthropic/claude-haiku-4.5")
MAX_ITERATIONS = int(os.getenv("LEO_MAX_ITERATIONS", "15"))
MAX_TOKENS = int(os.getenv("LEO_CS_MAX_TOKENS", "1024"))

# ── SOUL.md (static personality, cached once per session) ────────────
_soul_content: str | None = None


def _load_soul() -> str:
    """Read ~/.hermes/SOUL.md once and cache it. Hermes uses this as slot #1
    in _build_system_prompt when skip_context_files=False, but we set
    skip_context_files=True to avoid injecting dev context files (AGENTS.md,
    .cursorrules) into customer chats. So we load SOUL.md ourselves and pass
    it via system_message (slot #4, cached on first turn)."""
    global _soul_content
    if _soul_content is not None:
        return _soul_content
    from pathlib import Path
    soul_path = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")) / "SOUL.md"
    if soul_path.is_file():
        _soul_content = soul_path.read_text(encoding="utf-8").strip()
        logger.info("Loaded SOUL.md (%d chars) from %s", len(_soul_content), soul_path)
    else:
        logger.warning("SOUL.md not found at %s — agent will use Hermes default identity", soul_path)
        _soul_content = ""
    return _soul_content

# ── Agent pool ──────────────────────────────────────────────────────
# Keyed by conversation_id (phone number or lead_id).
# Tuple: (AIAgent instance, last-used unix timestamp)

_agent_pool: Dict[str, tuple] = {}
_pool_lock = threading.Lock()
AGENT_TTL_SECS = 3600

# Safe toolsets that the marketplace page can enable for customer-facing use.
# Anything NOT in this set is blocked even if someone edits the config file.
_SAFE_ADDON_TOOLSETS = frozenset([
    "code_execution", "delegation", "tts", "session_search",
    "image_gen", "cronjob", "vision",
])


def _get_enabled_toolsets() -> list[str]:
    """Read marketplace_config.json and merge enabled toolsets with leo-quote.

    Only toolsets in _SAFE_ADDON_TOOLSETS are allowed — terminal, file, and
    browser are blocked for customer-facing agents regardless of config."""
    from pathlib import Path
    toolsets = ["leo-quote"]
    cfg_path = Path(__file__).parent / "marketplace_config.json"
    if cfg_path.exists():
        try:
            import json as _json
            enabled = _json.loads(cfg_path.read_text()).get("enabled_toolsets", [])
            for ts in enabled:
                if ts in _SAFE_ADDON_TOOLSETS and ts not in toolsets:
                    toolsets.append(ts)
            if len(toolsets) > 1:
                logger.info("Marketplace toolsets: %s", toolsets)
        except Exception as exc:
            logger.warning("Could not read marketplace_config.json: %s", exc)
    return toolsets

# Per-conversation asyncio locks to serialise turns on the same agent
_conversation_locks: Dict[str, asyncio.Lock] = {}
_conv_lock_mutex = asyncio.Lock()


async def _get_conversation_lock(conversation_id: str) -> asyncio.Lock:
    async with _conv_lock_mutex:
        if conversation_id not in _conversation_locks:
            _conversation_locks[conversation_id] = asyncio.Lock()
        return _conversation_locks[conversation_id]


def evict_stale_agents() -> int:
    """Remove agents idle longer than AGENT_TTL_SECS. Returns count evicted."""
    now = time.time()
    with _pool_lock:
        stale = [k for k, (_, ts) in _agent_pool.items() if now - ts > AGENT_TTL_SECS]
        for k in stale:
            del _agent_pool[k]
    if stale:
        logger.info("Evicted %d stale agents from pool", len(stale))
    return len(stale)


def _get_or_create_agent(
    conversation_id: str,
    channel: str = "web",
    model: str | None = None,
):
    """Return existing agent for this conversation, or create a new one.

    Architecture (per Hermes docs — Prompt Assembly):
    - skip_context_files=True: prevents AGENTS.md/.cursorrules from CWD
      leaking into customer chats. SOUL.md is passed via system_message instead.
    - system_message: SOUL.md content (slot #4, cached on first turn)
    - ephemeral_system_prompt: per-turn dynamic context (set before each
      run_conversation call, appended at API-call time, never cached)
    - platform: "whatsapp" or None — triggers Hermes's native PLATFORM_HINTS
    """
    from messaging.frameworks import hermes as _hermes
    AIAgent = _hermes.get_ai_agent_class()
    SessionDB = _hermes.get_session_db_class()
    from . import tool_registry  # noqa: F401 — registers tools on import
    import uuid
    from datetime import datetime

    os.environ.setdefault("HERMES_GATEWAY_SESSION", "leo-quote-backend")

    with _pool_lock:
        if conversation_id in _agent_pool:
            agent, _ = _agent_pool[conversation_id]
            _agent_pool[conversation_id] = (agent, time.time())
            logger.debug("Reusing pooled agent for %s", conversation_id[:12])
            return agent, False  # (agent, is_new)

    session_db = SessionDB()

    hermes_session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    platform = "whatsapp" if channel == "whatsapp" else None

    # Leo's own tools record their own activity (with context-aware labels) inside
    # their handlers. Skip the pre-fire for these to avoid duplicate trace entries.
    _SELF_REPORTING_TOOLS = {
        "update_brief", "update_profile", "update_quote", "set_drawer",
        "save_signup", "whatsapp_handoff", "create_job", "rank_job_responses",
        "batch_outreach", "outreach_contractor", "control_outreach",
        "enrich_contractor", "founder_dashboard", "create_page",
        "lookup_price", "lookup_product", "search_spanish_law", "get_boe_norm_text",
        "search_eu_law", "find_houzz_contractors", "search_fb_groups", "search_forums",
        "send_whatsapp", "send_email", "start_job_intake",
    }

    def _tool_progress(tool_name: str, preview: str, args: dict) -> None:
        """Fires before any Hermes tool call. Skipped for Leo tools that self-report."""
        if tool_name in _SELF_REPORTING_TOOLS:
            return
        from .tool_utils import _record_activity, _send_indicator
        messages = {
            "web_search": lambda a: f"_Searching the web: {a.get('query', '')}…_",
            "web_extract": lambda a: f"_Reading page: {str(a.get('urls', a.get('url', '')))[:60]}…_",
            "memory": lambda a: "_Recalling memories…_",
            "skills_list": lambda a: "_Checking available skills…_",
            "skill_view": lambda a: f"_Reading skill: {a.get('skill_name', '')}…_",
        }
        _record_activity(tool_name, preview or f"Running {tool_name}…")
        if tool_name in messages:
            _send_indicator(tool_name, messages[tool_name](args))

    agent = AIAgent(
        model=model or PRIMARY_MODEL,
        api_key=LITELLM_API_KEY,
        base_url=LITELLM_BASE_URL,
        provider="openrouter",
        max_iterations=MAX_ITERATIONS,
        quiet_mode=True,
        verbose_logging=False,
        enabled_toolsets=_get_enabled_toolsets(),
        platform=platform,
        skip_context_files=True,
        skip_memory=False,
        session_id=hermes_session_id,
        session_db=session_db,
        tool_progress_callback=_tool_progress,
        fallback_model={
            "provider": "openrouter",
            "model": FALLBACK_MODEL,
            "base_url": LITELLM_BASE_URL,
            "api_key_env": "LITELLM_API_KEY",
        },
    )

    with _pool_lock:
        _agent_pool[conversation_id] = (agent, time.time())
    logger.info("Created new pooled agent for %s", conversation_id[:12])
    return agent, True  # (agent, is_new)


# ── Message format conversion ───────────────────────────────────────
# Single-step: frontend/WhatsApp {role, text, images} → OpenAI format.
# Replaces the old two-step Bedrock intermediate conversion.

def _to_openai_messages(history: list[dict], *, strip_images: bool = False) -> list[dict]:
    """Convert frontend/WhatsApp message format directly to OpenAI format.
    
    Idempotent: if messages are already in OpenAI format (content is str or
    list of typed parts), they pass through without losing image_url parts.
    
    strip_images: if True, remove all image_url parts and convert multipart
    messages to text-only. Use when the target model doesn't support vision.
    """
    msgs: list[dict] = []
    for m in history:
        role = m.get("role", "user")

        # Already in OpenAI format? Pass through (with optional image stripping).
        content = m.get("content")
        if content is not None and "text" not in m and "images" not in m:
            if isinstance(content, str):
                if content.strip():
                    msgs.append({"role": role, "content": content})
                continue
            if isinstance(content, list):
                if any(isinstance(p, dict) for p in content):
                    if strip_images:
                        text_parts = [
                            p.get("text", "") for p in content
                            if isinstance(p, dict) and p.get("type") == "text"
                        ]
                        combined = " ".join(t for t in text_parts if t).strip()
                        has_images = any(
                            p.get("type") == "image_url" for p in content if isinstance(p, dict)
                        )
                        if has_images and not combined:
                            combined = "(I sent a photo earlier)"
                        if combined:
                            msgs.append({"role": role, "content": combined})
                    else:
                        msgs.append({"role": role, "content": content})
                    continue

        # Raw format conversion
        raw_content = m.get("text", "") or m.get("content", "")
        if isinstance(raw_content, list):
            text = " ".join(
                part.get("text", "") for part in raw_content
                if isinstance(part, dict) and part.get("type") == "text"
            ).strip()
        else:
            text = str(raw_content).strip()
        images = m.get("images", [])
        if not text and not images:
            continue

        if images and not strip_images:
            parts: list[dict] = []
            if text:
                parts.append({"type": "text", "text": text})
            for img in images:
                data = img.get("data", "")
                media_type = img.get("media_type", "image/jpeg")
                if data:
                    parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{data}"},
                    })
            if parts:
                msgs.append({"role": role, "content": parts})
        else:
            if not text and images:
                text = "(I sent a photo earlier)"
            if text:
                msgs.append({"role": role, "content": text})
    return msgs


def _extract_text(openai_content: str | list) -> str:
    """Pull plain text from an OpenAI message content field."""
    if isinstance(openai_content, str):
        return openai_content
    if isinstance(openai_content, list):
        return " ".join(
            p["text"] for p in openai_content if p.get("type") == "text"
        ).strip()
    return str(openai_content)


def _last_msg_has_images(raw_msgs: list[dict]) -> bool:
    """Check if the last message has images (raw format or OpenAI multipart format)."""
    if not raw_msgs:
        return False
    last = raw_msgs[-1]
    # Raw format: {"images": [{"data": "...", "media_type": "..."}]}
    imgs = last.get("images", [])
    if imgs and any(img.get("data") for img in imgs):
        return True
    # OpenAI multipart format: {"content": [{"type": "image_url", ...}]}
    content = last.get("content", "")
    if isinstance(content, list):
        return any(part.get("type") == "image_url" for part in content if isinstance(part, dict))
    return False


def _pick_model(mode: str) -> str | None:
    """Sales mode gets Sonnet 4.6 (founder tool, worth the cost).
    All other modes use the default PRIMARY_MODEL (Sonnet 4.6)."""
    if mode == "sales":
        return FALLBACK_MODEL
    return None


def _resolve_capabilities(
    channel: str,
    caps: ChannelCapabilities | None,
    page_locale: str = "",
    user_language_hint: str = "",
) -> ChannelCapabilities:
    """Resolve a ChannelCapabilities from either an explicit object or a channel string."""
    if caps is not None:
        if page_locale and not caps.locale:
            caps.locale = page_locale
        if user_language_hint and not caps.user_language_hint:
            caps.user_language_hint = user_language_hint
        return caps
    if channel == "whatsapp":
        base = ChannelCapabilities(**WHATSAPP_CAPABILITIES.__dict__)
    else:
        base = ChannelCapabilities(**WEB_CAPABILITIES.__dict__)
    base.locale = page_locale
    base.user_language_hint = user_language_hint
    return base


def _legacy_msgs_to_leo_messages(raw_msgs: list[dict]) -> list[LeoMessage]:
    """Convert legacy frontend format {role, text, images} to LeoMessage list."""
    result: list[LeoMessage] = []
    for m in raw_msgs:
        role = m.get("role", "user")
        text = m.get("text", "") or ""
        content = m.get("content", "")
        if not text and isinstance(content, str):
            text = content

        media: list[MediaAttachment] = []
        for img in m.get("images", []):
            data = img.get("data", "")
            media_type = img.get("media_type", "image/jpeg")
            if data:
                media.append(MediaAttachment(
                    mime_type=media_type,
                    data=data,
                ))

        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        if not text:
                            text = part.get("text", "")
                    elif part.get("type") == "image_url":
                        url = part.get("image_url", {}).get("url", "")
                        if url.startswith("data:"):
                            mime_str, b64 = "", ""
                            if ";base64," in url:
                                header, b64 = url.split(";base64,", 1)
                                mime_str = header.replace("data:", "")
                            media.append(MediaAttachment(
                                mime_type=mime_str or "image/jpeg",
                                data=b64,
                            ))

        if text or media:
            result.append(LeoMessage(role=role, text=text.strip(), media=media))
    return result


def _extract_all_tool_calls(messages: list[dict]) -> list[str]:
    """Extract every tool name the agent called from the full Hermes message history."""
    tools: list[str] = []
    for msg in messages:
        if msg.get("role") == "assistant":
            for tc in msg.get("tool_calls", []):
                fn = tc.get("function", {})
                name = fn.get("name", "")
                if name:
                    tools.append(name)
    return tools


def _extract_improvement_signals(messages: list[dict]) -> list[str]:
    """
    Scan Hermes message history for memory tool calls containing IMPROVEMENT_SIGNAL.
    Returns a list of signal descriptions.
    """
    signals: list[str] = []
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            if fn.get("name") != "memory":
                continue
            args_raw = fn.get("arguments", "")
            if isinstance(args_raw, str):
                try:
                    args_raw = json.loads(args_raw)
                except Exception:
                    continue
            content = str(args_raw.get("content", ""))
            if "IMPROVEMENT_SIGNAL:" in content:
                sig = content.split("IMPROVEMENT_SIGNAL:", 1)[1].strip()
                if sig:
                    signals.append(sig)
    return signals


def _phone_key(phone: str | None) -> str:
    """Normalise a phone to bare digits (no +, spaces, dashes)."""
    if not phone:
        return ""
    return (phone or "").replace("whatsapp:", "").lstrip("+").replace(" ", "").replace("-", "")


# ── Convenience wrapper for WhatsApp callers ────────────────────────

async def whatsapp_reply(
    messages: list[dict],
    mode: str = "early_access",
    raw_history: list | None = None,
    lead_context: str = "",
    audience: str = "homeowner",
    page_locale: str = "",
    user_language_hint: str = "",
    profile_context: str = "",
    lead_phone: str | None = None,
    conversation_id: str = "",
    capabilities: ChannelCapabilities | None = None,
    enrichment_needed: dict | None = None,
) -> dict:
    """WhatsApp channel wrapper: runs Hermes with WhatsApp formatting + capabilities."""
    out = await run_leo_chat(
        messages,
        mode=mode,
        raw_history=raw_history,
        lead_context=lead_context,
        audience=audience,
        page_locale=page_locale,
        user_language_hint=user_language_hint,
        profile_context=profile_context,
        channel="whatsapp",
        lead_phone=lead_phone,
        conversation_id=conversation_id,
        user_id=conversation_id or (lead_phone or ""),
        capabilities=capabilities or WHATSAPP_CAPABILITIES,
        enrichment_needed=enrichment_needed,
    )
    return {
        "reply": (out.get("reply") or "").strip(),
        "tool_activity": out.get("tool_activity", []),
        "tokens": out.get("tokens", 0),
        "input_tokens": out.get("input_tokens", 0),
        "output_tokens": out.get("output_tokens", 0),
        "cache_read_tokens": out.get("cache_read_tokens", 0),
        "cost_usd": out.get("cost_usd", 0),
        "cost_status": out.get("cost_status", "unknown"),
        "model_used": out.get("model_used", ""),
        "api_calls": out.get("api_calls", 0),
        "all_tools_used": out.get("all_tools_used", []),
    }


# ── Main entry point ────────────────────────────────────────────────

_EMPTY_RESULT: Dict[str, Any] = {
    "reply": "", "brief_update": None, "profile_update": None,
    # "quote_update" is the canonical key; "quote_update" preserved for backward compat
    "quote_update": None, "quote_update": None,
    "tool_activity": [], "show_drawer": False, "drawer_state": None,
    "cost_usd": 0, "tokens": 0, "model_used": "",
}


def _leo_messages_to_openai(leo_msgs: list[LeoMessage]) -> list[dict]:
    """Convert enriched LeoMessages to OpenAI format for Hermes.
    After enrichment, messages should be text-only (media already converted)."""
    result: list[dict] = []
    for m in leo_msgs:
        text = (m.text or "").strip()
        if not text:
            continue
        result.append({"role": m.role, "content": text})
    return result


async def run_leo_chat(
    messages: List[Dict[str, Any]],
    mode: str = "early_access",
    raw_history: list | None = None,
    lead_context: str = "",
    audience: str = "homeowner",
    page_locale: str = "",
    user_language_hint: str = "",
    profile_context: str = "",
    channel: str = "web",
    lead_phone: str | None = None,
    source_tag: str = "leo_chat",
    confirmed: bool = False,
    user_id: str = "",
    conversation_id: str = "",
    capabilities: ChannelCapabilities | None = None,
    leo_messages: list[LeoMessage] | None = None,
    contractor_id: str = "",
    enrichment_needed: dict | None = None,
) -> Dict[str, Any]:
    """
    Run one agent turn using a pooled Hermes AIAgent.

    Accepts either:
    - leo_messages + capabilities (new Hermes-native path)
    - messages as list[dict] + channel string (legacy path, auto-converted)

    Media enrichment runs inside this function — adapters just attach raw
    media and the engine handles vision/transcription/extraction.
    """
    caps = _resolve_capabilities(channel, capabilities, page_locale, user_language_hint)

    # ── Convert legacy messages to LeoMessage if needed ──
    if leo_messages is None:
        leo_messages = _legacy_msgs_to_leo_messages(messages)
    if not leo_messages:
        return dict(_EMPTY_RESULT)

    # ── Enrich media on the last user message (Hermes gateway pattern) ──
    last_user_idx = None
    for i in range(len(leo_messages) - 1, -1, -1):
        if leo_messages[i].role == "user" and leo_messages[i].media:
            last_user_idx = i
            break

    if last_user_idx is not None:
        from messaging.media.enrich import enrich_message
        leo_messages[last_user_idx] = await enrich_message(leo_messages[last_user_idx])

    # ── Build OpenAI messages from enriched LeoMessages ──
    all_openai = _leo_messages_to_openai(leo_messages)
    if not all_openai:
        return dict(_EMPTY_RESULT)

    last_content = all_openai[-1].get("content", "")
    user_message = _extract_text(last_content)

    # After enrichment, media is already text — no raw images reach the agent
    has_images = False
    history_for_agent = all_openai[:-1]
    image_user_message = None
    # ── mem0: retrieve memories before building prompt ──
    memory_context = ""
    if user_id:
        try:
            from storage.semantic import get_user_context, is_mem0_configured
            if is_mem0_configured():
                last_user_msg = ""
                for m in reversed(raw_history or []):
                    if m.get("role") == "user":
                        last_user_msg = m.get("text", "") or m.get("content", "")
                        break
                memory_context = await get_user_context(user_id, last_user_msg)
                if memory_context:
                    logger.debug("mem0 injecting %d chars of memory context", len(memory_context))
        except Exception as e:
            logger.warning("mem0 retrieval failed (non-fatal): %s", e)

    effective_lead_context = lead_context
    if memory_context:
        effective_lead_context = f"{memory_context}\n\n{lead_context}" if lead_context else memory_context

    turn_context = build_turn_context(
        mode=mode,
        audience=audience,
        lead_context=effective_lead_context,
        page_locale=caps.locale or page_locale,
        user_language_hint=caps.user_language_hint or user_language_hint,
        profile_context=profile_context,
        channel=caps.channel,
        confirmed=confirmed,
        lead_phone=lead_phone or "",
        capabilities=caps,
        enrichment_needed=enrichment_needed,
    )

    if not user_message:
        return dict(_EMPTY_RESULT)

    # Resolve conversation_id for the agent pool
    conv_id = conversation_id or user_id or ""

    from .tool_utils import leo_ctx

    def _run_agent():
        """Synchronous AIAgent call, runs in thread executor."""
        from .tool_utils import _new_state
        leo_ctx.state = _new_state()
        leo_ctx.ctx = {
            "raw_history": raw_history,
            "audience": audience,
            "source_tag": source_tag,
            "lead_phone": lead_phone,
            "conversation_id": conv_id,
            "capabilities": caps,
            "contractor_id": contractor_id,
            "mode": mode,
        }

        # Set session env vars so Hermes tools (especially cronjob) know
        # the origin platform and chat_id for delivery routing.
        if caps.channel == "whatsapp" and lead_phone:
            phone_digits = lead_phone.replace("whatsapp:", "").lstrip("+").replace(" ", "").replace("-", "")
            os.environ["HERMES_SESSION_PLATFORM"] = "whatsapp"
            os.environ["HERMES_SESSION_CHAT_ID"] = phone_digits
        elif caps.channel == "web" and conv_id:
            os.environ["HERMES_SESSION_PLATFORM"] = "web"
            os.environ["HERMES_SESSION_CHAT_ID"] = conv_id

        chosen_model = _pick_model(mode)
        soul = _load_soul()

        if conv_id:
            agent, is_new = _get_or_create_agent(conv_id, channel=caps.channel, model=chosen_model)
            agent.ephemeral_system_prompt = turn_context
            # Always pass conversation history — Hermes's internal session DB is not
            # reliable across threads/restarts. The Supabase history is the source of
            # truth. Passing it every turn ensures the agent always has context even
            # if the session state was lost or the agent was evicted and recreated.
            conv_history = history_for_agent
        else:
            agent, is_new = _get_or_create_agent(
                f"ephemeral-{threading.get_ident()}-{time.time()}",
                channel=caps.channel,
                model=chosen_model,
            )
            agent.ephemeral_system_prompt = turn_context
            conv_history = history_for_agent

        # Snapshot cumulative counters BEFORE this turn so we can compute deltas
        pre_input = getattr(agent, 'session_input_tokens', 0) or 0
        pre_output = getattr(agent, 'session_output_tokens', 0) or 0
        pre_cache_read = getattr(agent, 'session_cache_read_tokens', 0) or 0
        pre_cost = getattr(agent, 'session_estimated_cost_usd', 0) or 0
        pre_api_calls = getattr(agent, 'session_api_calls', 0) or 0

        effective_user_message = user_message

        logger.info(
            "Hermes run_conversation | conv=%s | is_new=%s | history_msgs=%d | user_msg=%s",
            (conv_id or "ephemeral")[:12],
            is_new if conv_id else True,
            len(conv_history) if conv_history else 0,
            effective_user_message[:80],
        )

        result = agent.run_conversation(
            user_message=effective_user_message,
            system_message=soul or None,
            conversation_history=conv_history,
        )

        state = leo_ctx.state
        model_used = result.get("model", "")
        cost_usd = result.get("estimated_cost_usd", 0) or 0

        msgs = result.get("messages", []) or []
        all_tools = _extract_all_tool_calls(msgs)

        # Per-turn deltas (Hermes counters are cumulative across pooled agent lifetime)
        turn_input = max(0, (result.get("input_tokens", 0) or 0) - pre_input)
        turn_output = max(0, (result.get("output_tokens", 0) or 0) - pre_output)
        turn_cache_read = max(0, (result.get("cache_read_tokens", 0) or 0) - pre_cache_read)
        turn_cost = max(0, cost_usd - pre_cost)
        turn_api_calls = max(0, (result.get("api_calls", 0) or 0) - pre_api_calls)

        return {
            "reply": result.get("final_response", ""),
            "brief_update": state.get("brief_update"),
            "profile_update": state.get("profile_update"),
            # Expose both keys for backward compat; quote_update is canonical
            "quote_update": state.get("quote_update") or state.get("quote_update"),
            "quote_update": state.get("quote_update") or state.get("quote_update"),
            "tool_activity": state.get("tool_activity", []),
            "show_drawer": state.get("show_drawer", False),
            "drawer_state": state.get("drawer_state"),
            "cost_usd": round(turn_cost, 6),
            "tokens": turn_input + turn_output,
            "input_tokens": turn_input,
            "output_tokens": turn_output,
            "cache_read_tokens": turn_cache_read,
            "cost_status": result.get("cost_status", "unknown"),
            "model_used": model_used,
            "completed": result.get("completed", True),
            "api_calls": turn_api_calls,
            "all_tools_used": all_tools,
            "hermes_messages": msgs,
        }

    # Serialise turns for the same conversation to prevent races
    if conv_id:
        conv_lock = await _get_conversation_lock(conv_id)
    else:
        conv_lock = asyncio.Lock()

    async with conv_lock:
        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, _run_agent),
                timeout=180,
            )
        except asyncio.TimeoutError:
            logger.error("AIAgent timed out after 180s | mode=%s aud=%s", mode, audience)
            # Give a useful message that explains what was happening and what to do.
            # The most common cause is a search tool (forums, Facebook, Houzz) hanging
            # on blocked proxies or a slow external API. The tool_activity list in state
            # often shows what was running — include it if available.
            try:
                last_activity = (leo_ctx.state or {}).get("tool_activity", [])
                last_tool = last_activity[-1]["label"] if last_activity else None
            except Exception:
                last_tool = None
            if last_tool:
                timeout_msg = (
                    f"Timed out while {last_tool.lower().rstrip('…')} — that took longer than 3 minutes. "
                    "The search probably hit a slow external service. Try again and it should be faster "
                    "(each retry uses a fresh IP)."
                )
            else:
                timeout_msg = (
                    "Timed out after 3 minutes — a tool (probably a search) got stuck on a slow external service. "
                    "Try again; retries use fresh IPs and are usually much faster."
                )
            return {
                **_EMPTY_RESULT,
                "reply": timeout_msg,
            }
        except Exception as exc:
            logger.error("AIAgent run failed | %s", exc, exc_info=True)
            return dict(_EMPTY_RESULT)

        # If the agent returned empty, retry with a fresh agent
        reply_text = (result.get("reply") or "").strip()
        if not reply_text:
            logger.warning("Empty reply — retrying with fresh agent | conv=%s", (conv_id or "ephemeral")[:12])
            if conv_id:
                with _pool_lock:
                    _agent_pool.pop(conv_id, None)

            def _run_agent_retry():
                from .tool_utils import _new_state
                leo_ctx.state = _new_state()
                leo_ctx.ctx = {"raw_history": raw_history, "audience": audience, "source_tag": source_tag, "lead_phone": lead_phone, "conversation_id": conv_id, "capabilities": caps, "contractor_id": contractor_id}
                soul = _load_soul()
                agent2, _ = _get_or_create_agent(conv_id or f"retry-{threading.get_ident()}", channel=caps.channel)
                agent2.ephemeral_system_prompt = turn_context
                r2 = agent2.run_conversation(user_message=user_message, system_message=soul or None, conversation_history=all_openai[:-1])
                msgs2 = r2.get("messages", []) or []
                _q = leo_ctx.state.get("quote_update") or leo_ctx.state.get("quote_update")
                return {
                    "reply": r2.get("final_response", ""), "brief_update": leo_ctx.state.get("brief_update"),
                    "profile_update": leo_ctx.state.get("profile_update"),
                    "quote_update": _q, "quote_update": _q,
                    "tool_activity": leo_ctx.state.get("tool_activity", []),
                    "show_drawer": leo_ctx.state.get("show_drawer", False), "drawer_state": leo_ctx.state.get("drawer_state"),
                    "cost_usd": round(r2.get("estimated_cost_usd", 0) or 0, 6),
                    "tokens": (r2.get("input_tokens", 0) or 0) + (r2.get("output_tokens", 0) or 0),
                    "input_tokens": r2.get("input_tokens", 0) or 0, "output_tokens": r2.get("output_tokens", 0) or 0,
                    "cache_read_tokens": r2.get("cache_read_tokens", 0) or 0, "cost_status": r2.get("cost_status", "unknown"),
                    "model_used": r2.get("model", ""), "completed": r2.get("completed", True),
                    "api_calls": r2.get("api_calls", 0) or 0, "all_tools_used": _extract_all_tool_calls(msgs2), "hermes_messages": msgs2,
                }

            try:
                result = await asyncio.wait_for(loop.run_in_executor(None, _run_agent_retry), timeout=180)
                if (result.get("reply") or "").strip():
                    logger.info("Retry succeeded | conv=%s", (conv_id or "ephemeral")[:12])
            except Exception as retry_exc:
                logger.error("Retry also failed | %s", retry_exc, exc_info=True)

    cost = result.get("cost_usd", 0)
    tokens = result.get("tokens", 0)
    model = result.get("model_used", "")
    logger.info(
        "Leo agent turn | mode=%s aud=%s model=%s tokens=%s cost=$%s calls=%s conv=%s",
        mode, audience, model, tokens,
        f"{cost:.6f}" if isinstance(cost, (int, float)) else cost,
        result.get("api_calls", "?"),
        (conv_id or "ephemeral")[:12],
    )

    # ── Improvement signals → founder WhatsApp (skip Peter's own chats) ──
    try:
        from .peter_notify import FOUNDER_WA_DIGITS, notify_founder_improvement_signal

        sigs = _extract_improvement_signals(result.get("hermes_messages", []) or [])
        phone_k = _phone_key(lead_phone)
        if sigs and phone_k not in FOUNDER_WA_DIGITS and caps.channel in ("whatsapp", "web"):
            body = "\n---\n".join(sigs)
            asyncio.create_task(
                notify_founder_improvement_signal(body, conv_id or phone_k or user_id or "")
            )
    except Exception as exc:
        logger.debug("improvement signal notify skipped | %s", exc)

    # ── mem0: store conversation after Hermes reply ──
    reply = (result.get("reply") or "").strip()
    if user_id and reply:
        try:
            from types import SimpleNamespace

            from storage.semantic import is_mem0_configured, remember
            if is_mem0_configured():
                mem0_msgs: list[Any] = []
                for m in (raw_history or []):
                    role = m.get("role", "user")
                    content = m.get("text", "") or m.get("content", "")
                    if content and role in ("user", "assistant"):
                        mem0_msgs.append(SimpleNamespace(role=role, text=content))
                mem0_msgs.append(SimpleNamespace(role="assistant", text=reply))
                asyncio.create_task(
                    remember(
                        user_id,
                        mem0_msgs,
                        metadata={"audience": audience, "mode": mode, "channel": caps.channel},
                    )
                )
        except Exception as e:
            logger.warning("mem0 storage failed (non-fatal): %s", e)

    return result
