"""scrapers.habitissimo — Habitissimo directory + RFQ adapter (scope scrapers).

robots-policy: ignore. Uses authenticated session and undocumented
``/v1/serviceRequest`` API.

Scope (Wave 9 stub): the public surface — :func:`search`,
:func:`reveal_phone`, :func:`refresh_session`, :func:`submit_rfq`,
:func:`list_companies`, :func:`build_submissions`, :data:`AJAX_JS` —
is declared here so consumers compile against stable imports while
the network-and-session wiring is completed in Phase 5. Calling any
of the I/O functions raises :class:`NotImplementedError` with a
pointer to the migration plan.

Session semantics (preserved from audit §1.7):

* JWT + AWSALB + PHP session cookie.
* Refreshed via Playwright login (``session.refresh_session``).
* TTL 90 min (corrected from the pre-migration 5 h — audit §1.7 I2).
* File-cached at ``/tmp/habitissimo_session.json``.
"""
from __future__ import annotations

from .session import (
    HABITISSIMO_SESSION_FILE,
    HABITISSIMO_SESSION_TTL,
    get_session,
    refresh_session,
)
from .phones import AJAX_JS, HABITISSIMO_PROXY_PREFIX, reveal_phone
from .blast import build_submissions, submit_rfq
from .search import list_companies, search  # last: ``search`` is both a submodule and a function; function wins

__all__ = [
    "refresh_session",
    "get_session",
    "HABITISSIMO_SESSION_FILE",
    "HABITISSIMO_SESSION_TTL",
    "reveal_phone",
    "AJAX_JS",
    "HABITISSIMO_PROXY_PREFIX",
    "list_companies",
    "search",
    "submit_rfq",
    "build_submissions",
]
