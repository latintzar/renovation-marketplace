"""``AgentFramework`` protocol — the swap-point for LLM-agent runtimes.

Historically Leo treated Hermes (``vendor/hermes-agent``) as THE agent
framework. Phase 5 Wave 6 recalibrated: Hermes is **one** framework
provider. Other Leo apps may use different providers — a bespoke
OpenAI tool-calling loop, Anthropic's native tools, LangGraph, Mastra,
a minimal hand-rolled ReAct loop, whatever — as their needs diverge.

This protocol defines the minimum every provider must offer so host
code (Leo persona + tool registration + runtime loop) can swap without
caring about the vendor beneath.

Design note: we do NOT try to make this protocol cover every feature
of every agent framework (Hermes's ephemeral prompts, memory, session
compression, tool_progress callbacks, fallback models, etc.). Instead,
apps-level code (e.g. ``apps/scope/product/backend/agent/leo.py``) owns the
framework-specific orchestration and uses the concrete provider class
directly — the protocol is for the host-side "swap entire agent
framework" decision, not per-call detail. This keeps the interface
small and honest.

Providers live in sibling modules: :mod:`~.hermes` is the first.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AgentFramework(Protocol):
    """Minimum surface every agent-framework provider must implement.

    An ``AgentFramework`` is a *registered capability descriptor* — it
    tells the host what provider is in use and surfaces the provider's
    own session-management / agent-pool machinery behind a stable
    accessor. The actual conversational loop is invoked by app-level
    code that knows the provider's shape.

    Attributes:
        name: Stable provider identifier (``"hermes"``, ``"openai"``,
            ``"anthropic"``, ``"langgraph"``, etc.). Used for logging,
            metrics, and per-provider feature-gating.

        vendor_path: Filesystem-relative path to the vendor directory
            this provider wraps (``"vendor/hermes-agent"`` for Hermes;
            empty string for pure-pip providers). Documentation-only;
            helps ``agents-memory-updater`` and similar tools find the
            vendor boundary.
    """

    name: str
    vendor_path: str

    def is_available(self) -> bool:
        """Return ``True`` if the provider's dependencies are present
        on ``PYTHONPATH`` / installed. Hosts check this before wiring
        tools — an absent provider should degrade gracefully rather
        than crash on first agent call."""
        ...


__all__ = ["AgentFramework"]
