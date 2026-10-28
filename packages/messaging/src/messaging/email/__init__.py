"""Email dispatch via Resend.

The single email code path for the Leo codebase. Pre-migration there were
two Resend POST sites (``leo_agent/persistence.py::send_email_resend`` and
``shared/comms.py::_send_email``); they've converged on
:func:`messaging.email.resend.send_email`.
"""

from __future__ import annotations

from .resend import send_email, send_email_resend

__all__ = ["send_email", "send_email_resend"]
