"""records.types — scope-app persistent record shapes.

Dataclasses for rows that cross file boundaries inside the scope app's
persistence layer: leads, proposals, contractors, messages. Moved from
``packages/storage/src/storage/types.py`` in Phase 5 Wave 3 — these describe
scope-specific Supabase schemas (``cs_leads``, ``agent_skill_proposals``,
``contractors``, ``messages``) and therefore belong with the scope app, not
with the shared storage engines.

Centralising types here lets ``leads``, ``proposals``, ``dossier``, and
``conversations`` all reference the same shapes without circular imports.
All types are frozen-by-convention wrappers around the rows Supabase
returns.

Design:
- ``@dataclass`` (not frozen) because callers often build these from
  raw dicts and the optional fields get filled incrementally.
- Field types use ``Optional[...]`` + ``default=None`` rather than
  ``Union`` so the public API stays ergonomic from typed callers.
- ``created_at`` / ``updated_at`` are ``datetime`` objects — the Supabase
  REST layer returns ISO-8601 strings; the parsing helpers in each
  module coerce them.

Engine types (``Memory``, ``MigrationResult``, ``Embedding``,
``EmbeddingMatch``) continue to live in ``storage.types`` because they
describe the mem0 / pgvector engines, not scope schemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

__all__ = [
    "Lead",
    "LeadSaveResult",
    "Proposal",
    "ProposalResult",
    "SkillReplyIntent",
    "Contractor",
    "Message",
]


@dataclass
class Lead:
    """A row from ``cs_leads`` (or the ``early_access_signups`` fallback)."""

    id: str
    name: str
    whatsapp: str
    location: str
    source: str
    chat_summary: str
    chat_history: Optional[List[Dict[str, Any]]] = None
    audience: Optional[Literal["homeowner", "professional"]] = None
    created_at: Optional[datetime] = None


@dataclass
class LeadSaveResult:
    """Outcome of :func:`records.save_lead`.

    ``table_written`` distinguishes the primary path from the early-
    access fallback so callers / observability can see which store won.
    """

    ok: bool
    table_written: Optional[Literal["cs_leads", "early_access_signups"]] = None
    lead_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class Proposal:
    """A row from ``agent_skill_proposals``."""

    id: str
    skill_name: str
    action: Literal["create", "update", "delete", "edit", "patch", "write_file", "remove_file"]
    reason: str
    content: Optional[str] = None
    skill_payload: Dict[str, Any] = field(default_factory=dict)
    status: Literal["pending", "approved", "rejected", "draft"] = "pending"
    pattern_count: int = 1
    similar_proposals: List[str] = field(default_factory=list)
    conversation_id: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


@dataclass
class ProposalResult:
    """Outcome of :func:`records.store_proposal`."""

    ok: bool
    id: Optional[str] = None
    pattern_count: int = 0
    error: Optional[str] = None


@dataclass
class SkillReplyIntent:
    """Parsed founder-WA reply.

    ``action`` enumerates the four possible interpretations. ``short_ref``
    is the lowercased 8-hex chunk when the reply targets a specific
    proposal; ``raw`` is the original text (trimmed) for logging.
    """

    action: Literal["approve", "reject", "defer", "unknown"]
    short_ref: Optional[str] = None
    raw: str = ""


@dataclass
class Contractor:
    """A row from ``contractors``.

    ``dossier`` is the internal record (sources + trust signals +
    conversation notes + identity overrides). ``canvas`` is the derived
    public view produced by :func:`records.recompute_canvas`.
    """

    id: str
    canvas_token: str
    name: Optional[str] = None
    phone: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None
    dossier: Dict[str, Any] = field(default_factory=dict)
    canvas: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Message:
    """One turn in a user-scoped conversation log."""

    id: str
    channel: Literal["whatsapp", "web"]
    user_id: str
    role: Literal["user", "assistant", "system"]
    text: str
    media_url: Optional[str] = None
    wa_message_id: Optional[str] = None
    reply_to_wa_id: Optional[str] = None
    reply_to_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
