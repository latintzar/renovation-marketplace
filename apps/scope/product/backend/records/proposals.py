"""records.proposals — ``agent_skill_proposals`` table owner.

The agent-self-improvement workflow: Leo detects a gap in its skills,
stores a proposal row, and Peter approves or rejects via WhatsApp.
This module owns storage + parsing. The *sending* of the approval
request and the *execution* of an approved proposal live in
``packages/messaging`` (the messaging layer reads proposals from here).

Public API:

- :func:`store_proposal` — insert + auto-cluster by (skill_name,
  action).
- :func:`get_similar_proposals` — list pending + draft clones.
- :func:`resolve_proposal` — set status + resolved_at.
- :func:`fetch_pending_proposals` — list all pending, newest first.
- :func:`fetch_proposal_by_id` — single proposal by uuid.
- :func:`resolve_proposal_for_founder` — pick the proposal matching
  a short-ref (8-hex) in a founder's WA reply.
- :func:`parse_founder_skill_reply` — pure parser: "yes abc12345" →
  ``SkillReplyIntent(action="approve", short_ref="abc12345")``.
- :func:`proposal_short_id` — first 8 hex of a uuid.

Moved from ``packages/storage/src/storage/proposals.py`` in Phase 5
Wave 3 because Proposal and the ``agent_skill_proposals`` table are
scope-specific schemas (scope's agent-self-improvement workflow), not
shared storage engines.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from core import http_client, sb_headers, sb_key, sb_url

from .types import Proposal, ProposalResult, SkillReplyIntent

logger = logging.getLogger(__name__)

_ACTION_VALUES: tuple[str, ...] = (
    "create",
    "update",
    "delete",
    "edit",
    "patch",
    "write_file",
    "remove_file",
)


async def store_proposal(
    skill_name: str,
    action: Literal["create", "update", "delete", "edit", "patch", "write_file", "remove_file"],
    reason: str,
    *,
    content: Optional[str] = None,
    skill_payload: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None,
) -> ProposalResult:
    """Insert a proposal row.

    Clusters with existing pending/draft proposals for the same
    ``(skill_name, action)`` — ``pattern_count`` is set to ``max(similar
    pattern_counts) + 1`` so repeated observations of the same gap
    surface visibly.

    Never raises. Errors surface via :attr:`ProposalResult.ok`.
    """

    url = sb_url()
    key = sb_key()
    if not url or not key:
        logger.error("Supabase credentials missing for store_proposal")
        return ProposalResult(ok=False, error="db_not_configured")

    similar = await get_similar_proposals(skill_name, action)
    pattern_count = 1
    similar_ids: List[str] = []
    for s in similar:
        if s.id:
            similar_ids.append(s.id)
        pattern_count = max(pattern_count, (s.pattern_count or 0) + 1)

    row: Dict[str, Any] = {
        "skill_name": skill_name,
        "action": action,
        "reason": reason,
        "content": (content[:10000] if content else None),
        "skill_payload": skill_payload or {},
        "status": "pending",
        "pattern_count": pattern_count,
        "similar_proposals": similar_ids,
        "conversation_id": conversation_id or None,
    }

    try:
        async with http_client(timeout=10) as client:
            resp = await client.post(
                f"{url}/agent_skill_proposals",
                headers={**sb_headers(), "Prefer": "return=representation"},
                json=row,
            )
            if resp.status_code in (200, 201):
                rows = resp.json()
                stored = rows[0] if isinstance(rows, list) and rows else rows
                pid = str(stored.get("id")) if isinstance(stored, dict) else None
                logger.info(
                    "Skill proposal stored | skill=%s action=%s pattern=%d",
                    skill_name, action, pattern_count,
                )
                return ProposalResult(
                    ok=True,
                    id=pid,
                    pattern_count=pattern_count,
                )
            logger.error(
                "Skill proposal insert failed | status=%s body=%s",
                resp.status_code, resp.text[:200],
            )
            return ProposalResult(
                ok=False,
                error=f"insert_failed_{resp.status_code}",
            )
    except Exception as exc:
        logger.error("Skill proposal store error | %s", exc, exc_info=True)
        return ProposalResult(ok=False, error=str(exc))


async def get_similar_proposals(
    skill_name: str,
    action: Literal["create", "update", "delete", "edit", "patch", "write_file", "remove_file"],
) -> List[Proposal]:
    """Fetch pending + draft proposals for the same ``(skill_name, action)``.

    Sorted newest-first; capped at 10 (cluster detection doesn't need more).
    """

    url = sb_url()
    key = sb_key()
    if not url or not key:
        return []
    try:
        async with http_client(timeout=8) as client:
            resp = await client.get(
                f"{url}/agent_skill_proposals",
                params={
                    "skill_name": f"eq.{skill_name}",
                    "action": f"eq.{action}",
                    "status": "in.(pending,draft)",
                    "select": "id,skill_name,action,reason,content,skill_payload,status,pattern_count,similar_proposals,conversation_id,created_at,resolved_at",
                    "order": "created_at.desc",
                    "limit": "10",
                },
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
            )
            if resp.status_code == 200:
                return [_row_to_proposal(r) for r in (resp.json() or [])]
    except Exception as exc:
        logger.debug("get_similar_proposals error (non-fatal) | %s", exc)
    return []


async def resolve_proposal(
    proposal_id: str,
    status: Literal["approved", "rejected", "draft"],
) -> bool:
    """Set ``status`` + ``resolved_at`` (``None`` if ``status="draft"``).

    Returns ``True`` on HTTP 200/204, ``False`` otherwise (including
    when the row doesn't exist).
    """

    url = sb_url()
    key = sb_key()
    if not url or not key or not proposal_id:
        return False
    try:
        payload: Dict[str, Any] = {"status": status}
        if status == "draft":
            payload["resolved_at"] = None
        else:
            payload["resolved_at"] = datetime.now(timezone.utc).isoformat()

        async with http_client(timeout=8) as client:
            resp = await client.patch(
                f"{url}/agent_skill_proposals",
                params={"id": f"eq.{proposal_id}"},
                headers={**sb_headers(), "Prefer": "return=minimal"},
                json=payload,
            )
            if resp.status_code in (200, 204):
                logger.info(
                    "Skill proposal resolved | id=%s status=%s",
                    proposal_id[:8], status,
                )
                return True
            logger.warning(
                "Skill proposal resolve failed | status=%s", resp.status_code,
            )
    except Exception as exc:
        logger.warning("Skill proposal resolve error | %s", exc)
    return False


async def fetch_pending_proposals(limit: int = 40) -> List[Proposal]:
    """List pending proposals, newest first."""

    url = sb_url()
    key = sb_key()
    if not url or not key:
        return []
    try:
        async with http_client(timeout=10) as client:
            resp = await client.get(
                f"{url}/agent_skill_proposals",
                params={
                    "status": "eq.pending",
                    "select": "*",
                    "order": "created_at.desc",
                    "limit": str(limit),
                },
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
            )
            if resp.status_code == 200:
                return [_row_to_proposal(r) for r in (resp.json() or [])]
    except Exception as exc:
        logger.warning("fetch_pending_proposals | %s", exc)
    return []


async def fetch_proposal_by_id(proposal_id: str) -> Optional[Proposal]:
    """Single proposal by full id. ``None`` if not found."""

    url = sb_url()
    key = sb_key()
    if not url or not key or not proposal_id:
        return None
    try:
        async with http_client(timeout=8) as client:
            resp = await client.get(
                f"{url}/agent_skill_proposals",
                params={
                    "id": f"eq.{proposal_id}",
                    "select": "*",
                    "limit": "1",
                },
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
            )
            if resp.status_code == 200:
                rows = resp.json() or []
                return _row_to_proposal(rows[0]) if rows else None
    except Exception as exc:
        logger.warning("fetch_proposal_by_id | %s", exc)
    return None


async def resolve_proposal_for_founder(short_opt: Optional[str]) -> Optional[Proposal]:
    """Pick the pending proposal whose short-ref matches ``short_opt``.

    If ``short_opt`` is empty/``None``, returns the latest pending.
    If ``short_opt`` is provided but no match found, returns ``None``.
    """

    pending = await fetch_pending_proposals()
    if not pending:
        return None
    if short_opt:
        s = short_opt.lower().strip()
        for row in pending:
            if proposal_short_id(row.id) == s:
                return row
        return None
    return pending[0]


def parse_founder_skill_reply(text: str) -> SkillReplyIntent:
    """Pure parser. Classifies a founder's WA reply into one of four
    :class:`SkillReplyIntent.action` values.

    Supported shapes (case-insensitive, ``*`` and smart-quotes stripped):

    - ``yes [ref]`` / ``approve`` / ``ok`` / ``yep`` / ``apply`` → approve
    - ``no [ref]`` / ``reject`` / ``nope`` / ``deny`` → reject
    - ``wait [ref]`` / ``draft`` / ``hold`` / ``later`` / ``pause`` /
      ``not yet [ref]`` → defer
    - everything else → unknown

    ``short_ref`` is the 8-hex chunk when present. Max input length
    is 120 chars; above that, returns ``unknown`` with ``raw`` preserved.
    """

    raw_input = text or ""
    raw = raw_input.strip().replace("*", "").replace("\u201c", "").replace("\u201d", "").strip().lower()
    if not raw:
        return SkillReplyIntent(action="unknown", raw=raw_input)
    if len(raw) > 120:
        return SkillReplyIntent(action="unknown", raw=raw_input)

    if raw.startswith("not yet"):
        tail = raw[len("not yet"):].strip().split()
        ref_ny: Optional[str] = None
        if tail and re.match(r"^[a-f0-9]+$", tail[0]) and len(tail[0]) <= 8:
            ref_ny = tail[0]
        return SkillReplyIntent(action="defer", short_ref=ref_ny, raw=raw_input)

    parts = raw.split()
    head = parts[0]
    ref: Optional[str] = None
    if len(parts) >= 2 and len(parts[1]) <= 8 and re.match(r"^[a-f0-9]+$", parts[1]):
        ref = parts[1]

    if head in ("yes", "approve", "ok", "yep", "apply"):
        return SkillReplyIntent(action="approve", short_ref=ref, raw=raw_input)
    if head in ("no", "reject", "nope", "deny"):
        return SkillReplyIntent(action="reject", short_ref=ref, raw=raw_input)
    if head in ("wait", "draft", "hold", "later", "pause"):
        return SkillReplyIntent(action="defer", short_ref=ref, raw=raw_input)
    return SkillReplyIntent(action="unknown", raw=raw_input)


def proposal_short_id(full_id: str) -> str:
    """First 8 hex of a UUID (dashes stripped, lowercased).

    Used in founder-WA reply shortrefs. Returns an empty string on
    empty input.
    """

    return (full_id or "").replace("-", "").lower()[:8]


def _row_to_proposal(row: Dict[str, Any]) -> Proposal:
    action = row.get("action") or "create"
    if action not in _ACTION_VALUES:
        action = "create"

    status = row.get("status") or "pending"
    if status not in ("pending", "approved", "rejected", "draft"):
        status = "pending"

    similar = row.get("similar_proposals") or []
    if not isinstance(similar, list):
        similar = []

    return Proposal(
        id=str(row.get("id", "")),
        skill_name=str(row.get("skill_name") or ""),
        action=action,
        reason=str(row.get("reason") or ""),
        content=row.get("content"),
        skill_payload=_as_dict(row.get("skill_payload")),
        status=status,
        pattern_count=int(row.get("pattern_count") or 1),
        similar_proposals=[str(x) for x in similar],
        conversation_id=row.get("conversation_id"),
        created_at=_parse_ts(row.get("created_at")),
        resolved_at=_parse_ts(row.get("resolved_at")),
    )


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _parse_ts(raw: Any) -> Optional[datetime]:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


__all__ = [
    "store_proposal",
    "get_similar_proposals",
    "resolve_proposal",
    "fetch_pending_proposals",
    "fetch_proposal_by_id",
    "resolve_proposal_for_founder",
    "parse_founder_skill_reply",
    "proposal_short_id",
]
