"""Habitissimo session refresh + cache (scaffolded).

Consolidates the three pre-migration login implementations (audit
Smell B): ``get_phones._fresh_login``,
``scripts/refresh_habitissimo_session.py``, and
``routes/profile_import._habi_refresh_session_if_needed``.

Session file shape (``/tmp/habitissimo_session.json``):

.. code-block:: json

    {
        "jwt": "eyJ...",
        "awsalb": "abcd...",
        "php_session": "5a...",
        "created_at": 1234567890
    }

Wave-9 scope: the public API is declared with ``NotImplementedError``
bodies so callers can type-check against the canonical shape. Full
implementation in Phase 5 (post network-and-session parity).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

__all__ = [
    "HABITISSIMO_SESSION_FILE",
    "HABITISSIMO_SESSION_TTL",
    "refresh_session",
    "get_session",
]


HABITISSIMO_SESSION_FILE: Path = Path("/tmp/habitissimo_session.json")
"""Canonical session cache path. One writer: :func:`refresh_session`."""


HABITISSIMO_SESSION_TTL: float = 5400.0
"""Session TTL in seconds (90 min). Corrected from the pre-migration
5-h literal (audit §1.7 I2) — matches the actual Habitissimo JWT
``exp`` claim we've observed in production."""


async def refresh_session(
    *,
    username: Optional[str] = None,
    password: Optional[str] = None,
    force: bool = False,
) -> dict[str, Any]:
    """Log in via Playwright and write ``HABITISSIMO_SESSION_FILE``.

    :param force: Refresh even if the cached session is younger than
        :data:`HABITISSIMO_SESSION_TTL`.
    :returns: The session dict (``jwt``, ``awsalb``, ``php_session``,
        ``created_at``).

    .. note::
       **Wave-9 scope**: this is a stub. Full implementation ports
       the three pre-migration login paths into one. See
       ``internal/refactor/packages/scraping/design.md`` §D5.
    """

    raise NotImplementedError(
        "scrapers.habitissimo.session.refresh_session is scaffolded "
        "for Wave 9; full implementation in Phase 5. "
        "See internal/refactor/packages/scraping/design.md §D5."
    )


async def get_session() -> dict[str, Any]:
    """Return the cached session, refreshing if expired.

    Lazy — never called at module import. Fixes audit Smell I
    (import-time network in the pre-migration ``get_phones.py``).

    .. note::
       **Wave-9 scope**: stub. See :func:`refresh_session`.
    """

    raise NotImplementedError(
        "scrapers.habitissimo.session.get_session is scaffolded "
        "for Wave 9; full implementation in Phase 5."
    )
