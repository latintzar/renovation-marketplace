"""
records — scope-app persistent business records
=================================================

Every Leo-owned fact about the scope app's domain — **users**,
**contractors**, **proposals**, **messages** — that has to survive a
process restart and live longer than a single HTTP request. Moved from
``packages/storage`` in Phase 5 Wave 3 so the shared storage package
stays a pure engine (mem0 + pgvector) with no scope schema leakage.

Five capabilities behind a single import:

- **Leads** — ``cs_leads`` + ``early_access_signups`` writes.
- **Proposals** — ``agent_skill_proposals`` CRUD + founder-reply parsing.
- **Dossier** — per-contractor record merging (``contractors`` + canvas).
- **Conversations** — per-user WhatsApp / web message log.
- **Types** — the record shapes (``Lead``, ``Proposal``, ``Contractor``,
  ``Message``, plus ``*Result`` / ``SkillReplyIntent`` helpers).

Top-level import surface
------------------------

Scope backend code writes::

    from records import (
        save_lead, get_lead_by_phone, patch_lead_structured,
        store_proposal, fetch_pending_proposals, resolve_proposal,
        get_or_create_contractor, add_contractor_source, recompute_canvas,
        add_message, get_recent_window, summarize_recent,
        Lead, Proposal, Contractor, Message,
    )

Submodules remain addressable for advanced usage
(``from records.dossier import _select``) but are not the blessed
surface.

Caller pairing with storage engines
-----------------------------------

``records`` describes *what* scope persists. ``storage`` (in packages/)
provides the generic *engines* — ``storage.remember`` / ``storage.recall``
(mem0) and ``storage.index_text`` / ``storage.search_similar`` (pgvector).
Scope code typically imports both::

    from records import save_lead, add_message  # scope schemas
    from storage import remember, recall       # generic engines

Phase 5 Wave 6 (messaging split) retired the duplicate dossier
implementation that used to live at
``packages/messaging/src/messaging/dossier/contractor.py``; this
module is now the single source of truth for the ``contractors``
table.
"""

from __future__ import annotations

from .types import (
    Contractor,
    Lead,
    LeadSaveResult,
    Message,
    Proposal,
    ProposalResult,
    SkillReplyIntent,
)

from .leads import (
    get_lead_by_phone,
    patch_lead_structured,
    save_lead,
)

from .proposals import (
    fetch_pending_proposals,
    fetch_proposal_by_id,
    get_similar_proposals,
    parse_founder_skill_reply,
    proposal_short_id,
    resolve_proposal,
    resolve_proposal_for_founder,
    store_proposal,
)

from .dossier import (
    add_contractor_source,
    add_conversation_note,
    get_contractor_by_phone,
    get_contractor_by_token,
    get_or_create_contractor,
    recompute_canvas,
    save_and_recompute,
    save_and_recompute_canvas,
    set_contractor_phone,
    update_identity_overrides,
    update_trust_signals,
)

from .conversations import (
    add_message,
    get_messages,
    get_recent_window,
    summarize_recent,
)

__all__ = [
    # --- types (7) ---
    "Lead",
    "LeadSaveResult",
    "Proposal",
    "ProposalResult",
    "SkillReplyIntent",
    "Contractor",
    "Message",
    # --- leads (3) ---
    "save_lead",
    "patch_lead_structured",
    "get_lead_by_phone",
    # --- proposals (8) ---
    "store_proposal",
    "get_similar_proposals",
    "resolve_proposal",
    "fetch_pending_proposals",
    "fetch_proposal_by_id",
    "resolve_proposal_for_founder",
    "parse_founder_skill_reply",
    "proposal_short_id",
    # --- dossier (11) ---
    "get_or_create_contractor",
    "get_contractor_by_phone",
    "get_contractor_by_token",
    "set_contractor_phone",
    "add_contractor_source",
    "update_trust_signals",
    "add_conversation_note",
    "update_identity_overrides",
    "recompute_canvas",
    "save_and_recompute",
    "save_and_recompute_canvas",
    # --- conversations (4) ---
    "add_message",
    "get_messages",
    "get_recent_window",
    "summarize_recent",
]
