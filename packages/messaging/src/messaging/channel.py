"""
messaging.channel — unified Channel enum + ChannelCapabilities + LeoMessage.

Single source of truth for the "which surface am I talking on" concept. Merges
two legacy definitions that drifted pre-migration:

1. ``shared/comms.py::Channel`` — str Enum (whatsapp|email|auto|all) for
   :func:`messaging.comms.notify` dispatch routing.
2. ``leo_agent/channel.py::ChannelCapabilities.channel: str`` — free-string
   field compared against ``"web"``, ``"whatsapp"``, ``"email"`` literals
   throughout the agent runtime.

Convergence rules:

* :class:`Channel` is a ``str`` subclass so legacy string comparisons keep
  working during the caller flip (``channel == "web"`` is still truthy).
* :data:`WEB_CAPABILITIES`, :data:`WHATSAPP_CAPABILITIES`,
  :data:`EMAIL_CAPABILITIES` are the three pre-baked capability profiles.
  Builders that need per-turn tweaks copy-then-mutate via
  :meth:`ChannelCapabilities.copy`.
* :data:`Channel.AUTO` and :data:`Channel.ALL` are routing sentinels
  consumed by :func:`messaging.comms.notify` — they never appear on
  :class:`ChannelCapabilities`.

See ``internal/refactor/packages/messaging/design.md`` §D-MSG-4.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum

__all__ = [
    "Channel",
    "MediaAttachment",
    "LeoMessage",
    "ChannelCapabilities",
    "WEB_CAPABILITIES",
    "WHATSAPP_CAPABILITIES",
    "EMAIL_CAPABILITIES",
]


class Channel(str, Enum):
    """Single source of truth for the target channel of a message.

    ``str`` subclass so ``Channel.WEB == "web"`` during the migration
    (legacy free-string comparisons stay green).
    """

    WEB = "web"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    AUTO = "auto"
    ALL = "all"


@dataclass
class MediaAttachment:
    """One media item attached to a :class:`LeoMessage`.

    Exactly one of ``path`` or ``data`` should be set. ``data`` is the
    base64-encoded payload when the caller ingested the blob directly
    (e.g. Meta webhook base64 images); ``path`` is the local filesystem
    location when the media came from a downloader.
    """

    mime_type: str
    path: str = ""
    data: str = ""
    filename: str = ""
    caption: str = ""


@dataclass
class LeoMessage:
    """Normalised per-turn message — the platform-agnostic shape the agent sees.

    Adapters (WhatsApp webhook, /chat HTTP, email ingestion) convert their
    wire formats into :class:`LeoMessage` before handing the message to
    whatever agent framework the host app wires up (see
    :mod:`messaging.frameworks`).
    """

    role: str
    text: str = ""
    media: list[MediaAttachment] = field(default_factory=list)


@dataclass
class ChannelCapabilities:
    """Declares what the output channel can render.

    ``channel`` is typed as :class:`Channel` (not a free string) — new code
    must use one of the three real channels (``WEB``, ``WHATSAPP``,
    ``EMAIL``), never ``AUTO`` / ``ALL`` (those are :func:`notify` routing
    sentinels only).
    """

    channel: Channel
    can_show_preview: bool = False
    can_show_drawer: bool = False
    can_show_tool_cards: bool = False
    can_render_markdown: bool = False
    can_send_template: bool = False
    can_attach_media: bool = False
    max_reply_length: int | None = None
    locale: str = ""
    user_language_hint: str = ""

    def copy(self, **updates) -> "ChannelCapabilities":
        """Return a new :class:`ChannelCapabilities` with ``updates`` applied.

        Preferred over mutating module-level constants — those are intended
        to be read-only once the package is imported.
        """
        return replace(self, **updates)


WEB_CAPABILITIES = ChannelCapabilities(
    channel=Channel.WEB,
    can_show_preview=True,
    can_show_drawer=True,
    can_show_tool_cards=True,
    can_render_markdown=True,
)

WHATSAPP_CAPABILITIES = ChannelCapabilities(
    channel=Channel.WHATSAPP,
    can_send_template=True,
    can_attach_media=True,
    max_reply_length=800,
)

EMAIL_CAPABILITIES = ChannelCapabilities(
    channel=Channel.EMAIL,
    can_render_markdown=True,
    can_attach_media=True,
)
