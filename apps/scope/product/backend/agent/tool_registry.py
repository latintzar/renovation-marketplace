"""Register Leo's scope tools into the agent-framework tool registry.

Moved from ``packages/messaging/src/messaging/leo_agent/hermes_tools.py``
in Phase 5 Wave 6. Tool handlers are scope-specific policy that lives
next to the Leo persona in ``apps/scope/product/backend/agent/`` — the shared
``packages/messaging`` package stopped hosting Leo-specific code in
the same wave.

This module is framework-shaped (takes a ``registry`` + optional
``create_custom_toolset``) but not vendor-shaped — callers pass in
whatever the active :mod:`messaging.frameworks` provider exposes
(Hermes by default, other providers if/when added). See the Hermes
accessors at :mod:`messaging.frameworks.hermes`.

All tool handlers live in :mod:`~.tools` (canonical location) and
shared utilities in :mod:`~.tool_utils`. This file's only job is
binding the tools to a registry + creating the ``leo-quote`` toolset.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

_LEO_TOOL_NAMES: tuple[str, ...] = (
    "update_quote", "update_profile", "save_signup",
    "whatsapp_handoff", "send_whatsapp", "set_drawer",
    "search_spanish_law", "get_boe_norm_text", "search_eu_law",
    "propose_skill_change", "send_email", "request_human",
    "create_job", "start_job_intake", "find_houzz_contractors", "outreach_contractor",
    "batch_outreach", "control_outreach", "founder_dashboard",
    "rank_job_responses", "search_fb_groups", "search_forums",
    "lookup_price", "lookup_product", "estimate_cost", "enrich_contractor", "create_page",
)

_LEO_TOOLSET_DESC = (
    "Leo Quote tools: contractor quotes, profiles, signups, WhatsApp (unified send), email, "
    "human escalation, Spanish law (BOE), EU law (LexAPI), contractor discovery "
    "(Houzz, outreach, ranking), Habitissimo pricing, contractor verification "
    "(VIES, NIF, REA, reviews, social proof), Spanish forums (Forocoches, Mediavida, Reddit ES)"
)


def register_leo_tools(
    registry: Any,
    create_custom_toolset: Callable[..., Any] | None = None,
) -> None:
    """Register the leo-quote tool handlers + toolset.

    Args:
        registry: The active framework's tool registry
            (``messaging.frameworks.hermes.get_tool_registry()`` for
            Hermes; siblings when new providers are added).
        create_custom_toolset: The active framework's toolset factory
            (``messaging.frameworks.hermes.get_create_custom_toolset()``
            for Hermes). When ``None`` the toolset is not created
            (tools are still registered individually — useful for
            testing).
    """
    from .tools import admin, canvas, delivery, discovery, legal, outreach, pricing, user_flow

    canvas.register(registry)
    user_flow.register(registry)
    delivery.register(registry)
    legal.register(registry)
    pricing.register(registry)
    discovery.register(registry)
    outreach.register(registry)
    admin.register(registry)
    admin.register_skill_manage(registry)

    if create_custom_toolset is not None:
        create_custom_toolset(
            name="leo-quote",
            description=_LEO_TOOLSET_DESC,
            tools=list(_LEO_TOOL_NAMES),
            includes=["web", "skills", "memory"],
        )

    logger.info(
        "Leo Quote tools registered (leo-quote + web + skills + memory; "
        "update_quote exposed; estimate_cost added; skill_manage gated; unified WA send; "
        "forums: Forocoches + Mediavida + Reddit ES; start_job_intake: homeowner intake pipeline)"
    )


__all__ = ["register_leo_tools"]
