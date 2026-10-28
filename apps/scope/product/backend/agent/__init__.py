"""Scope app — Leo agent (persona, tools, runtime glue).

Moved here from ``packages/messaging/src/messaging/leo_agent/`` in
Phase 5 Wave 6 as part of the architectural recalibration: Leo is
the **scope app's** agent, not a cross-app capability. The shared
``packages/messaging`` provides the *capability* (channels, transport,
media, verification, framework adapter protocol). This module is
where we wire Leo's persona, per-turn context, tools, and founder
notifications.

Typical use from scope routes::

    from agent import (
        run_leo_chat,          # main chat entry (web, email)
        whatsapp_reply,        # WhatsApp-specific reply handler
        evict_stale_agents,    # background TTL eviction
        register_leo_tools,    # tool registration (Hermes today)
        notify_peter,          # founder notifications
    )

Agent framework: today we use **Hermes** (see
:mod:`messaging.frameworks.hermes`), but :mod:`agent.leo` works
against the :class:`messaging.frameworks.AgentFramework` protocol,
so swapping to another provider (OpenAI Agents SDK, LangGraph, a
custom in-house framework) requires only a new adapter alongside
``hermes.py`` — no changes here.
"""

from __future__ import annotations

from .leo import (
    _to_openai_messages,
    evict_stale_agents,
    run_leo_chat,
    whatsapp_reply,
)
from .peter_notify import (
    notify_brief_confirmed,
    notify_founder_improvement_signal,
    notify_founder_skill_proposal,
    notify_peter,
    notify_peter_discovery_complete,
    notify_peter_lead_submitted,
    request_human_escalation,
    save_signup,
    send_email_resend,
    store_skill_proposal,
    try_handle_founder_skill_reply,
    whatsapp_handoff,
)
from .tool_registry import register_leo_tools

__all__ = [
    # Chat runtime
    "run_leo_chat",
    "whatsapp_reply",
    "evict_stale_agents",
    "_to_openai_messages",
    # Tool registration
    "register_leo_tools",
    # Founder notifications / persistence
    "notify_peter",
    "notify_peter_lead_submitted",
    "notify_peter_discovery_complete",
    "notify_brief_confirmed",
    "notify_founder_skill_proposal",
    "notify_founder_improvement_signal",
    "try_handle_founder_skill_reply",
    "request_human_escalation",
    "send_email_resend",
    "save_signup",
    "whatsapp_handoff",
    "store_skill_proposal",
]
