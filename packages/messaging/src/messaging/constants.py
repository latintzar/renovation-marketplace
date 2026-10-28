"""
messaging.constants — API version pins & transport-layer constants
===================================================================

Constants that describe the external messaging APIs (Meta Graph, in
future Twilio/Vonage/etc). Moved from ``packages/domain/constants.py``
in Phase 5 Wave 2 — these describe *what* the messaging layer talks to,
not *how* the core runtime works, so they belong here with the transport
implementations.

Env-overrideable at process start. Once frozen at import, changing the
env var in-process has no effect.

Tier: leaf. Depends on stdlib only.
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Meta Graph API (WhatsApp Cloud API, Messenger, Instagram)
# ---------------------------------------------------------------------------
# META_API_VERSION is read at import; META_API_BASE is f-string-frozen
# immediately after. Callers that want a runtime override should patch
# META_API_BASE itself.

META_API_VERSION = os.getenv("META_API_VERSION", "v23.0")
"""Meta Graph API version pin. Bumps must be reviewed — breaking changes
are the norm between major versions."""

META_API_BASE = f"https://graph.facebook.com/{META_API_VERSION}"
"""Fully-qualified Graph API base URL. Every Meta-origin HTTP request in
``messaging.whatsapp.*`` and siblings is f-string-interpolated off this
constant."""


__all__ = [
    "META_API_VERSION",
    "META_API_BASE",
]
