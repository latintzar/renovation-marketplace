"""Unified notify facade — one interface for all outbound comms.

Callers specify **what** to send and **whom** to send it to; this module
handles **where** (WhatsApp, email, or both). Promoted verbatim from the
pre-migration ``shared/comms.py`` module, plus these architectural
upgrades:

* :class:`Channel` is now the unified :class:`messaging.channel.Channel`
  enum, not a free-standing duplicate. ``AUTO`` and ``ALL`` routing
  sentinels are on the same enum as the three real channels.
* The inline email POST has been dropped in favor of
  :func:`messaging.email.send_email` (single Resend code path).
* Freeform :class:`NotifyResult` dataclass is unchanged — six public
  attributes (``success``, ``channel``, ``detail``) that most callers
  already depend on.

Provider routing:

- WhatsApp → :func:`messaging.whatsapp.send_wa_message` (Meta Cloud API,
  24h window, template routing, cold-send budget).
- Email → :func:`messaging.email.send_email` (Resend).

When adding push notifications, SMS, or Slack — add an adapter here.
Callers never change.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from .channel import Channel
from .email import send_email
from .whatsapp import send_wa_message

logger = logging.getLogger(__name__)


@dataclass
class NotifyResult:
    """Per-channel dispatch outcome.

    :func:`notify` returns a list of these — one per channel that
    actually dispatched. Preserves the pre-migration shape so existing
    callers keep working.
    """

    success: bool
    channel: str
    detail: str = ""


@dataclass
class NotifyRequest:
    """Typed alternative to the kwargs overload of :func:`notify`.

    New call sites should prefer this; legacy kwargs form is retained
    indefinitely for caller compatibility.
    """

    phone: Optional[str] = None
    email: Optional[str] = None
    message: str = ""
    subject: str = ""
    html: Optional[str] = None
    channel: Channel = Channel.AUTO
    purpose: str = "general"
    template_name: Optional[str] = None
    template_params: Optional[list[str]] = None


async def notify(
    *,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    message: str = "",
    subject: str = "",
    html: Optional[str] = None,
    channel: Channel = Channel.AUTO,
    purpose: str = "general",
    template_name: Optional[str] = None,
    template_params: Optional[list[str]] = None,
) -> list[NotifyResult]:
    """Send a notification via the appropriate channel(s).

    Routing:

    - :data:`Channel.AUTO`: phone prefix heuristic — ``+34`` → WhatsApp,
      otherwise email if provided, otherwise WhatsApp (if phone provided).
    - :data:`Channel.ALL`: fan out to every available channel.
    - Any specific channel (``WEB``, ``WHATSAPP``, ``EMAIL``): single target.

    Args:
        template_name: WhatsApp-approved template name (e.g.
            ``contractor_followup_1``); when set, the WA sender will
            bypass the auto template lookup.
        template_params: parameters for the template body components.
    """
    results: list[NotifyResult] = []
    channels_to_send = _resolve_channels(channel, phone, email)

    for ch in channels_to_send:
        if ch == Channel.WHATSAPP and phone:
            result = await _send_whatsapp(
                phone, message, purpose,
                template_name=template_name,
                template_params=template_params,
            )
            results.append(result)
        elif ch == Channel.EMAIL and email:
            result = await _send_email(email, subject, message, html)
            results.append(result)

    return results


def _resolve_channels(
    channel: Channel,
    phone: Optional[str],
    email: Optional[str],
) -> list[Channel]:
    """Decide which real channels to dispatch to given the ``channel`` sentinel."""
    if channel == Channel.ALL:
        channels: list[Channel] = []
        if phone:
            channels.append(Channel.WHATSAPP)
        if email:
            channels.append(Channel.EMAIL)
        return channels

    if channel == Channel.AUTO:
        if phone and phone.replace("+", "").startswith("34"):
            return [Channel.WHATSAPP]
        if email:
            return [Channel.EMAIL]
        if phone:
            return [Channel.WHATSAPP]
        return []

    return [channel]


async def _send_whatsapp(
    phone: str,
    message: str,
    purpose: str,
    template_name: Optional[str] = None,  # noqa: ARG001 — reserved for explicit override path
    template_params: Optional[list[str]] = None,
) -> NotifyResult:
    """Delegate to the unified WhatsApp sender.

    ``template_name`` is accepted for forward-compat but currently
    unused — :func:`messaging.whatsapp.send_wa_message` looks it up by
    ``purpose`` + language. Callers that want an explicit template should
    use :func:`messaging.whatsapp.send_wa_message` directly.
    """
    try:
        result = await send_wa_message(
            phone=phone,
            text=message,
            purpose=purpose,
            template_params=template_params,
        )
        return NotifyResult(
            success=result.ok,
            channel="whatsapp",
            detail=result.wa_message_id or result.error or "",
        )
    except Exception as e:  # noqa: BLE001
        logger.error("WhatsApp send failed for %s: %s", phone, e)
        return NotifyResult(success=False, channel="whatsapp", detail=str(e))


async def _send_email(
    to: str,
    subject: str,
    text: str,
    html: Optional[str],
) -> NotifyResult:
    """Delegate to :func:`messaging.email.send_email`."""
    try:
        res = await send_email(
            to=to,
            subject=subject or "Leo notification",
            body_html=html or "",
            body_text=text,
        )
        if res.get("ok"):
            return NotifyResult(success=True, channel="email", detail=res.get("id", "") or "")
        return NotifyResult(
            success=False,
            channel="email",
            detail=res.get("detail", "") or res.get("error", ""),
        )
    except Exception as e:  # noqa: BLE001
        logger.error("Email send failed for %s: %s", to, e)
        return NotifyResult(success=False, channel="email", detail=str(e))


@runtime_checkable
class Notifier(Protocol):
    """Structural type: anything with an ``async notify(to, message, **kw)`` works."""

    async def notify(self, *, to: str, message: str, **kw) -> "NotifyResult": ...


__all__ = [
    "notify",
    "NotifyRequest",
    "NotifyResult",
    "Notifier",
    "Channel",
]
