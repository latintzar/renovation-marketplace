"""Messaging — channel-aware transport, media enrichment, verification,
and an agent-framework adapter protocol.

Phase 5 Wave 6 recalibration: the ``messaging`` package now exposes
only **capabilities** — things that can be shared across apps that
talk to humans via WhatsApp, email, or web. Scope-app-specific
policy (Leo's persona, Leo's tools, founder notifications, dossier
records) has moved to the scope backend.

::

    from messaging import (
        # Channel abstraction (shared across all messaging apps)
        Channel, ChannelCapabilities, LeoMessage, MediaAttachment,
        WEB_CAPABILITIES, WHATSAPP_CAPABILITIES, EMAIL_CAPABILITIES,

        # Transport (async)
        send_wa_message, send_email, notify,
        NotifyRequest, NotifyResult, SendResult,

        # Media gateway (audio/pdf/docx/url extraction)
        enrich_message, parse_media, parse_url,

        # Verification (NIF/VIES/REA + social proof)
        ProfileResult, TrustSignals, Credential,
        validate_nif, check_vies, check_rea,
        run_verification_checks, run_social_proof_checks,
        enrich_contractor_from_phone, enrich_credentials_from_web,

        # Agent framework protocol + host-adapter registry
        # (used by any app that wires an AI agent into messaging)
        AgentFramework, register_host_adapter,
    )

What's **not** here (and why):

* **Leo's agent runtime / tools / persona** — these are scope policy
  (``apps/scope/product/backend/agent/``). A future app (e.g. the April 18
  demo deck) can run its own agent, swap the framework provider,
  or skip the agent entirely without touching ``messaging``.
* **Dossier / contractor records** — these are scope business
  records (``apps/scope/product/backend/records/``). Other apps that want
  to track trades will keep records that mean something to them.

Capability boundaries (invariants):

* Audio never decoded inside ``messaging`` — :mod:`voice` owns codecs.
* Route handlers never imported from here — host adapters come in via
  :func:`register_host_adapter` (see :mod:`messaging.frameworks.adapters`).
* ``routes/`` → ``packages/messaging`` is the only allowed arrow.
"""

from __future__ import annotations

from .channel import (
    Channel,
    ChannelCapabilities,
    EMAIL_CAPABILITIES,
    LeoMessage,
    MediaAttachment,
    WEB_CAPABILITIES,
    WHATSAPP_CAPABILITIES,
)
from .comms import NotifyRequest, NotifyResult, notify
from .constants import META_API_BASE, META_API_VERSION
from .email import send_email
from .frameworks import (
    AgentFramework,
    HostAdapterMissing,
    clear_adapters,
    get_adapter,
    has_adapter,
    register_host_adapter,
)
from .media import enrich_message, parse_media, parse_url, transcribe_file
from .media.parse import _extract_docx_sync, _extract_pdf_sync
from .verification import (
    Credential,
    PageChunk,
    Project,
    ProfileResult,
    Review,
    TeamMember,
    TrustSignals,
    check_rea,
    check_vies,
    enrich_contractor_from_phone,
    enrich_credentials_from_web,
    expand_fb_queries,
    run_social_proof_checks,
    run_verification_checks,
    search_fb_posts,
    search_forum_posts,
    search_review_signals,
    search_social_proof,
    validate_nif,
)
from .whatsapp import SendResult, send_wa_message, send_wa_message_sync
from .whatsapp.storage import store_message
from .whatsapp.templates import detect_language as detect_whatsapp_language

__all__ = [
    # Channel
    "Channel",
    "ChannelCapabilities",
    "EMAIL_CAPABILITIES",
    "LeoMessage",
    "MediaAttachment",
    "WEB_CAPABILITIES",
    "WHATSAPP_CAPABILITIES",
    # Comms
    "NotifyRequest",
    "NotifyResult",
    "notify",
    # API constants (Wave 2 — from packages/domain)
    "META_API_BASE",
    "META_API_VERSION",
    # Email
    "send_email",
    # Agent framework protocol + host adapter registry
    "AgentFramework",
    "HostAdapterMissing",
    "clear_adapters",
    "get_adapter",
    "has_adapter",
    "register_host_adapter",
    # Media
    "enrich_message",
    "parse_media",
    "parse_url",
    "transcribe_file",
    "_extract_pdf_sync",
    "_extract_docx_sync",
    # Verification types
    "Credential",
    "PageChunk",
    "Project",
    "ProfileResult",
    "Review",
    "TeamMember",
    "TrustSignals",
    # Verification api
    "check_rea",
    "check_vies",
    "enrich_contractor_from_phone",
    "enrich_credentials_from_web",
    "expand_fb_queries",
    "run_social_proof_checks",
    "run_verification_checks",
    "search_fb_posts",
    "search_forum_posts",
    "search_review_signals",
    "search_social_proof",
    "validate_nif",
    # WhatsApp
    "SendResult",
    "send_wa_message",
    "send_wa_message_sync",
    "store_message",
    "detect_whatsapp_language",
]
