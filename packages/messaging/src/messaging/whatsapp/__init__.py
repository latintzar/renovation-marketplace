"""WhatsApp I/O — outbound Meta Cloud API + 24h-window + templates + cold-send budget.

All outbound code paths (agent tools, WA webhook auto-reply, onboarding,
follow-ups, founder notifications, cron delivery) funnel through
:func:`send_wa_message`. It owns: 24h window detection, template routing,
language detection, Meta API call, message storage, cold-send budget
counter, and the structured :class:`SendResult` return contract.
"""

from __future__ import annotations

from .outreach_budget import (
    daily_sent_count,
    enqueue_deferred,
    flush_queue,
    log_send,
    request_quota,
)
from .send import send_wa_message, send_wa_message_sync
from .session import check_24h_window
from .storage import SendResult, store_message
from .templates import (
    TEMPLATES,
    detect_language,
    get_template_name,
)

__all__ = [
    "send_wa_message",
    "send_wa_message_sync",
    "SendResult",
    "check_24h_window",
    "store_message",
    "TEMPLATES",
    "detect_language",
    "get_template_name",
    "daily_sent_count",
    "request_quota",
    "log_send",
    "enqueue_deferred",
    "flush_queue",
]
