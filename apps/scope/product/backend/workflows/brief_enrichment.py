"""
Brief Enrichment Workflow
==========================

Enrichment team pipeline. Runs in parallel with contractor discovery (fired
by brief_intake.run_brief_intake).

Responsibilities
----------------
1. Load the brief + any photos already received.
2. Assess Bar 2 gaps — what's missing to make contractors reply well.
3. Write the enrichment_needed signal to the job row so ephemeral_context.py
   can inject targeted prompts into Hermes's next turn.
4. Return immediately — the actual enrichment happens through conversation
   turns guided by Hermes, not inside this workflow.

This workflow is intentionally thin. It does the assessment and writes the
signal. The conversation that fills the gaps is Hermes's job.

Two bars (defined in brief_intake.py)
--------------------------------------
Bar 1 — Discovery bar: trade + location. Checked in brief_intake BEFORE calling
         this workflow. If we're here, Bar 1 is already met.

Bar 2 — Brief quality bar (this workflow's target):
    - description — at least one substantive sentence
    - photos — highest value (3× contractor response quality)
    - measurements — room/area dimensions
    - urgency — how soon they need it done
    - budget — rough budget indication

Gap priority order (always): photos → description → measurements → urgency → budget.

Workflow signal written to job row
-----------------------------------
    job.enrichment_needed = {
        "gaps": ["photos", "description", "measurements", "urgency", "budget"],
        "priority": "photos",
        "assessed_at": ISO-8601 str,
    }

    job.workflow_signals[-1] = {
        "workflow": "brief_enrichment",
        "job_id": str,
        "gaps": [...],
        "priority": str,
        "completed_at": ISO-8601 str,
    }

Hermes reads enrichment_needed via ephemeral_context.py and injects a targeted
one-liner telling it exactly what to ask next (photos first, then scope details).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ── Gap priority order ────────────────────────────────────────────────
#
# Photos first — research shows photos increase contractor response quality 3×.
# Description second — contractors need to know what the job entails.
# Measurements, urgency, budget are nice-to-have and asked in that order.

ENRICHMENT_GAP_PRIORITY = ["photos", "description", "measurements", "urgency", "budget"]


# ─── Result dataclass ─────────────────────────────────────────────────

@dataclass
class EnrichmentResult:
    ok: bool
    job_id: str = ""
    gaps: list[str] = field(default_factory=list)
    priority: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "job_id": self.job_id,
            "gaps": self.gaps,
            "priority": self.priority,
            "error": self.error,
        }


# ─── Gap assessment ────────────────────────────────────────────────────

def _assess_enrichment_gaps(brief: dict, photos: list) -> list[str]:
    """Assess which Bar 2 gaps remain for this brief.

    Returns priority-ordered list of missing fields.
    Pure function — no I/O.

    Priority order: photos → description → measurements → urgency → budget.
    """
    gaps: list[str] = []

    # Photos — any photos already received?
    has_photos = bool(photos and len(photos) > 0)
    if not has_photos:
        gaps.append("photos")

    # Description — at least one substantive sentence (> 30 chars, not just trade name)
    desc = str(brief.get("description") or "").strip()
    has_description = len(desc) > 30
    if not has_description:
        gaps.append("description")

    # Measurements — rough dimensions / room size
    measurements = str(brief.get("measurements") or "").strip()
    if not measurements:
        gaps.append("measurements")

    # Urgency — how soon they need it done
    urgency = str(brief.get("urgency") or "").strip()
    if not urgency:
        gaps.append("urgency")

    # Budget — rough indication (optional but valuable)
    budget = str(brief.get("budget_indication") or brief.get("budget") or "").strip()
    if not budget:
        gaps.append("budget")

    return gaps


# ─── Main entry point ─────────────────────────────────────────────────

async def run_brief_enrichment(
    job_id: str,
    homeowner_phone: str,
    brief: Optional[dict] = None,
    photos: Optional[list] = None,
) -> EnrichmentResult:
    """Enrichment team pipeline.

    Parameters
    ----------
    job_id:
        The Supabase jobs row ID.
    homeowner_phone:
        Normalised E.164 phone — logged only, not stored again.
    brief:
        Current brief dict (optional — loaded from DB if not provided).
    photos:
        Any photos already received.

    Steps
    -----
    1. Load brief + photos from Supabase if not provided.
    2. Assess Bar 2 gaps (ordered priority list).
    3. Write enrichment_needed signal to job row:
           { gaps: [...], priority: str, assessed_at: ISO str }
    4. Append to workflow_signals.
    5. Return immediately — Hermes drives the conversation from here.
    """
    from routes.job_inbox import get_job_by_id, update_job

    logger.info(
        "BriefEnrichment | START | job=%s phone=%s",
        job_id[:8], (homeowner_phone or "")[:8] + "***",
    )

    # ── Step 1: Load brief if not provided ───────────────────────────
    if not brief:
        job_row = await get_job_by_id(job_id)
        if not job_row:
            logger.error("BriefEnrichment | job not found | job=%s", job_id[:8])
            return EnrichmentResult(ok=False, job_id=job_id, error=f"Job {job_id} not found")
        brief = job_row.get("brief") or {}
        if not photos:
            photos = job_row.get("brief_photos") or []

    # ── Step 2: Assess Bar 2 gaps ─────────────────────────────────────
    gaps = _assess_enrichment_gaps(brief, photos or [])
    priority = gaps[0] if gaps else ""

    logger.info(
        "BriefEnrichment | gaps=%s priority=%s | job=%s",
        gaps, priority, job_id[:8],
    )

    # ── Step 3: Write enrichment_needed to job row ───────────────────
    enrichment_needed = {
        "gaps": gaps,
        "priority": priority,
        "assessed_at": datetime.now(timezone.utc).isoformat(),
    }

    signal = {
        "workflow": "brief_enrichment",
        "job_id": job_id,
        "gaps": gaps,
        "priority": priority,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        job_row = await get_job_by_id(job_id)
        existing_signals = (job_row or {}).get("workflow_signals") or []
        if not isinstance(existing_signals, list):
            existing_signals = []
        existing_signals.append(signal)

        await update_job(job_id, {
            "enrichment_needed": enrichment_needed,
            "workflow_signals": existing_signals,
        })
        logger.info(
            "BriefEnrichment | COMPLETE | job=%s | gaps=%s | priority=%s",
            job_id[:8], gaps, priority,
        )
    except Exception as exc:
        logger.warning(
            "BriefEnrichment | signal write failed (non-fatal) | job=%s | %s", job_id[:8], exc
        )

    return EnrichmentResult(
        ok=True,
        job_id=job_id,
        gaps=gaps,
        priority=priority,
    )
