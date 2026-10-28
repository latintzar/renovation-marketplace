"""``messaging.frameworks`` — agent-framework providers + host-adapter glue.

This subpackage is the messaging capability's AGENT-LAYER seam. It
defines what an agent-framework provider looks like (:class:`AgentFramework`
protocol), ships the first concrete provider (:mod:`~.hermes`, wrapping
``vendor/hermes-agent``), and hosts the cross-cutting host-adapter
registry (:func:`register_host_adapter`) that lets tool handlers call
back into app routes without breaking the one-way dep arrow.

Canonical imports:

.. code-block:: python

    # Protocol + adapter registry (always available, pure-Python):
    from messaging.frameworks import (
        AgentFramework,
        HostAdapterMissing,
        register_host_adapter,
        get_adapter,
        has_adapter,
        clear_adapters,
    )

    # Hermes provider (requires vendor/hermes-agent on PYTHONPATH):
    from messaging.frameworks import hermes
    assert hermes.is_available()
    AIAgent = hermes.get_ai_agent_class()

Adding a new provider (e.g. "mastra"):

1.  Create ``packages/messaging/src/messaging/frameworks/mastra.py``
    with module-level ``name``, ``vendor_path``, ``is_available()``,
    and any provider-specific accessors (``get_X_class()``).
2.  Optionally add ``packages/messaging/tests/test_frameworks_mastra.py``
    that validates the provider satisfies :class:`AgentFramework`.
3.  Use it from an app's agent layer
    (e.g. ``apps/mynewapp/backend/agent/``) by importing
    ``from messaging.frameworks import mastra``.

No import-time coupling — each provider is lazy-importable and absent
ones fail loudly with ``HostAdapterMissing``-style errors, not crashes.
"""

from __future__ import annotations

from .adapters import (
    HostAdapterMissing,
    clear_adapters,
    get_adapter,
    has_adapter,
    register_host_adapter,
)
from .protocol import AgentFramework

__all__ = [
    "AgentFramework",
    "HostAdapterMissing",
    "clear_adapters",
    "get_adapter",
    "has_adapter",
    "register_host_adapter",
]
