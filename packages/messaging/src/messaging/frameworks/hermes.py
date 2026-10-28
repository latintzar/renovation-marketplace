"""Hermes agent framework provider — wraps ``vendor/hermes-agent``.

This is ONE of potentially several agent-framework providers Leo can
use. Hermes is the default for the scope app (and for experiments
inheriting from scope), but apps are free to pick a different provider
— see the siblings (when added) like ``openai.py`` or ``langgraph.py``.

**What this module IS**: the vendor boundary. It re-exports the
pieces of Hermes that app-level code needs (``AIAgent``, ``SessionDB``,
``tools.registry.registry``, ``toolsets.create_custom_toolset``) under
a stable surface so app code doesn't import from vendor paths directly.

**What this module is NOT**: the Leo persona, Leo's tool handlers, or
the conversation-loop code. All of that is app-specific and lives at
``apps/scope/product/backend/agent/`` — this module just says "here's what the
framework offers, wire your app through it".

Why not a single monolithic ``HermesFramework`` class with
``run_chat(...)``? Because Hermes has enough quirks (ephemeral prompts,
tool_progress callbacks, session DBs, fallback models, platform hints,
skip_context_files, marketplace toolsets) that a lossy abstraction
would hide more than it reveals. App-level orchestration already owns
those knobs — this module just exposes the raw primitives and
documents which provider's being used.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

name: str = "hermes"
vendor_path: str = "vendor/hermes-agent"


def is_available() -> bool:
    """Return True if Hermes's modules can be imported from the current
    ``PYTHONPATH``. Hosts call this at startup to decide whether to
    wire Hermes-dependent tools."""
    try:
        import run_agent  # noqa: F401 — Hermes's AIAgent entry point
        import hermes_state  # noqa: F401 — Hermes's SessionDB
        return True
    except ImportError as exc:
        logger.warning("Hermes framework unavailable: %s", exc)
        return False


def get_ai_agent_class() -> type[Any]:
    """Return the Hermes ``AIAgent`` class (lazy import so we don't
    force ``vendor/hermes-agent`` to be on path at package-import time)."""
    from run_agent import AIAgent
    return AIAgent


def get_session_db_class() -> type[Any]:
    """Return the Hermes ``SessionDB`` class."""
    from hermes_state import SessionDB
    return SessionDB


def get_tool_registry() -> Any:
    """Return the singleton Hermes ``tools.registry.registry``.

    App-level tool-registration code (e.g. Leo's
    ``apps/scope/product/backend/agent/tool_registry.py``) passes this registry
    to its individual tool modules' ``register(registry)`` functions."""
    from tools.registry import registry
    return registry


def get_create_custom_toolset() -> Any:
    """Return the Hermes ``toolsets.create_custom_toolset`` factory.

    Used to bundle a group of registered tools into a named toolset
    (e.g. ``"leo-quote"``)."""
    from toolsets import create_custom_toolset
    return create_custom_toolset


__all__ = [
    "name",
    "vendor_path",
    "is_available",
    "get_ai_agent_class",
    "get_session_db_class",
    "get_tool_registry",
    "get_create_custom_toolset",
]
