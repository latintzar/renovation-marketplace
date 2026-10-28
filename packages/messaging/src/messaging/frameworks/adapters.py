"""Host-adapter registry — dependency injection for agent tool handlers.

Agent tool handlers (e.g. ``apps/scope/product/backend/agent/tools/discovery.py``)
need to call back into the host application's routes/workflows
(``routes.job_inbox.create_job``, ``workflows.run_brief_intake``, etc.).
Agent-framework/capability packages **cannot** import from the host —
that breaks the one-way dependency arrow — so instead the host registers
its functions here at startup and tool handlers look them up by name.

Registration (host-side, runs during FastAPI startup). Example
from ``apps/scope/product/backend/main.py``::

    # from messaging.frameworks: register_host_adapter
    # from routes.job_inbox: create_job, get_job_by_id
    register_host_adapter("job_inbox.create_job", create_job)
    register_host_adapter("job_inbox.get_job_by_id", get_job_by_id)

Lookup (from tool handlers in scope app's ``agent/tools/`` dir):

.. code-block:: python

    from messaging.frameworks import get_adapter

    create_job = get_adapter("job_inbox.create_job")
    job_id = await create_job(brief=..., contractor_id=...)

This module was Leo-Agent-specific (lived at
``messaging.leo_agent._adapters``) before Phase 5 Wave 6 — it has been
promoted to a generic capability because the host-adapter-registry
pattern is useful for any agent framework (Hermes or otherwise), not
Leo specifically.
"""

from __future__ import annotations

import logging
from threading import Lock
from typing import Any, Callable

logger = logging.getLogger(__name__)


class HostAdapterMissing(RuntimeError):
    """Raised when a tool handler asks for an adapter the host hasn't registered."""


_ADAPTERS: dict[str, Callable[..., Any]] = {}
_LOCK = Lock()


def register_host_adapter(name: str, fn: Callable[..., Any]) -> None:
    """Register ``fn`` under ``name`` (called by the host at startup)."""
    with _LOCK:
        if name in _ADAPTERS:
            logger.warning("register_host_adapter: overwriting existing adapter %r", name)
        _ADAPTERS[name] = fn
    logger.debug("register_host_adapter | %s", name)


def get_adapter(name: str, *, required: bool = True) -> Callable[..., Any] | None:
    """Look up a host adapter. When ``required`` is True, raises if missing."""
    fn = _ADAPTERS.get(name)
    if fn is None and required:
        raise HostAdapterMissing(
            f"host adapter {name!r} not registered — did the host forget to call "
            f"register_host_adapter({name!r}, ...)?"
        )
    return fn


def has_adapter(name: str) -> bool:
    """True if ``name`` has been registered (useful in tests/dry-runs)."""
    return name in _ADAPTERS


def clear_adapters() -> None:
    """Wipe the registry (only intended for test teardown)."""
    with _LOCK:
        _ADAPTERS.clear()


__all__ = [
    "HostAdapterMissing",
    "register_host_adapter",
    "get_adapter",
    "has_adapter",
    "clear_adapters",
]
