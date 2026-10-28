"""
Brief Intake Workflow
======================

Intake team pipeline. Called by Hermes (via start_job_intake tool) the instant
Bar 1 is met — trade + location known. Does NOT wait for a full brief.

Responsibilities
----------------
1. Confirm Bar 1 fields are present (trade + location).
2. Create the job row in Supabase (if not already created).
3. Fire contractor discovery + brief enrichment in parallel.
4. Write intake_complete workflow_signal to the job row.

Two bars
--------
Bar 1 — Discovery bar (checked here before any work starts):
    - brief.trade or brief.title — non-empty
    - brief.location — non-empty

Bar 2 — Brief quality bar (assessed by brief_enrichment, not here):
    - description, photos, measurements, urgency, budget
    - assessed and written as enrichment_needed signal by run_brief_enrichment

Workflow signal (written to job.workflow_signals on completion)
---------------------------------------------------------------
    {
        "workflow": "brief_intake",
        "job_id": str,
        "discovery": WorkflowResult.to_dict(),
        "enrichment": {"gaps": [...], "priority": str},
        "completed_at": ISO-8601 str,
    }

Hermes reads workflow_signals via ephemeral_context.py and injects them as notes
on the next turn so it knows what to ask for next (guided by enrichment_needed).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Result dataclass ─────────────────────────────────────────────────

@dataclass
class IntakeResult:
    ok: bool
    job_id: str = ""
    discovery_sent: int = 0
    enrichment_gaps: list[str] = None  # type: ignore[assignment]
    enrichment_priority: str = ""
    error: str = ""

    def __post_init__(self):
        if self.enrichment_gaps is None:
            self.enrichment_gaps = []

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "job_id": self.job_id,
            "discovery_sent": self.discovery_sent,
            "enrichment_gaps": self.enrichment_gaps,
            "enrichment_priority": self.enrichment_priority,
            "error": self.error,
        }


# ─── Bar 1 check ──────────────────────────────────────────────────────

def _assess_bar1(brief: dict) -> tuple[bool, str]:
    """Check if Bar 1 (discovery bar) is met.

    Returns (ok, missing_field).
    Pure function — no I/O.

    Bar 1 requires:
        - brief.trade OR brief.title — non-empty
        - brief.location — non-empty
    """
    trade = str(brief.get("trade") or brief.get("title") or "").strip()
    location = str(brief.get("location") or "").strip()

    if not trade:
        return False, "trade"
    if not location:
        return False, "location"
    return True, ""


# ─── Main entry point ─────────────────────────────────────────────────

async def run_brief_intake(
    job_id: str,
    homeowner_phone: str,
    brief: Optional[dict] = None,
    photos: Optional[list] = None,
) -> IntakeResult:
    """Intake team pipeline.

    Parameters
    ----------
    job_id:
        The Supabase jobs row ID — must already exist before calling this
        (created by start_job_intake tool handler before calling this workflow).
    homeowner_phone:
        Normalised E.164 phone number (e.g. "+34612345678").
    brief:
        Current brief dict (optional — loaded from DB if not provided).
    photos:
        Any photos already received.

    Steps
    -----
    1. Load brief from Supabase if not provided — confirm Bar 1 present.
    2. asyncio.gather(
           run_contractor_discovery(job_id),   # existing, untouched
           run_brief_enrichment(job_id, homeowner_phone),  # new
       )
    3. Write intake_complete workflow_signal to job row.
    4. Return IntakeResult.
    """
    from routes.job_inbox import get_job_by_id, update_job
    from workflows.brief_enrichment import run_brief_enrichment
    from workflows.contractor_discovery import run_contractor_discovery

    logger.info("BriefIntake | START | job=%s phone=%s", job_id[:8], (homeowner_phone or "")[:8] + "***")

    # ── Step 1: Load and validate brief ──────────────────────────────
    if not brief:
        job_row = await get_job_by_id(job_id)
        if not job_row:
            logger.error("BriefIntake | job not found | job=%s", job_id[:8])
            return IntakeResult(ok=False, job_id=job_id, error=f"Job {job_id} not found")
        brief = job_row.get("brief") or {}
        if not photos:
            photos = job_row.get("brief_photos") or []

    bar1_ok, missing = _assess_bar1(brief)
    if not bar1_ok:
        logger.warning(
            "BriefIntake | Bar 1 not met | missing=%s | job=%s", missing, job_id[:8]
        )
        return IntakeResult(
            ok=False,
            job_id=job_id,
            error=f"Bar 1 not met — missing: {missing}",
        )

    trade = str(brief.get("trade") or brief.get("title") or "").strip()
    location = str(brief.get("location") or "").strip()
    logger.info(
        "BriefIntake | Bar 1 met | trade=%s location=%s | job=%s",
        trade, location, job_id[:8],
    )

    # ── Step 2: Fire discovery + enrichment in parallel ──────────────
    discovery_result = None
    enrichment_result = None

    try:
        discovery_result, enrichment_result = await asyncio.gather(
            run_contractor_discovery(job_id),
            run_brief_enrichment(job_id, homeowner_phone, brief=brief, photos=photos or []),
            return_exceptions=False,
        )
    except Exception as exc:
        logger.error("BriefIntake | parallel phase failed | job=%s | %s", job_id[:8], exc, exc_info=True)
        return IntakeResult(
            ok=False,
            job_id=job_id,
            error=f"Parallel phase failed: {exc}",
        )

    # ── Step 3: Write intake_complete signal ──────────────────────────
    signal = {
        "workflow": "brief_intake",
        "job_id": job_id,
        "discovery": discovery_result.to_dict() if discovery_result else {},
        "enrichment": {
            "gaps": enrichment_result.gaps if enrichment_result else [],
            "priority": enrichment_result.priority if enrichment_result else "",
        },
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Append to existing workflow_signals array in the job row
        job_row = await get_job_by_id(job_id)
        existing_signals = (job_row or {}).get("workflow_signals") or []
        if not isinstance(existing_signals, list):
            existing_signals = []
        existing_signals.append(signal)
        await update_job(job_id, {"workflow_signals": existing_signals, "status": "active"})
        logger.info(
            "BriefIntake | COMPLETE | job=%s | discovery_sent=%d | enrichment_gaps=%s",
            job_id[:8],
            discovery_result.sent if discovery_result else 0,
            enrichment_result.gaps if enrichment_result else [],
        )
    except Exception as exc:
        logger.warning("BriefIntake | signal write failed (non-fatal) | job=%s | %s", job_id[:8], exc)

    return IntakeResult(
        ok=True,
        job_id=job_id,
        discovery_sent=discovery_result.sent if discovery_result else 0,
        enrichment_gaps=enrichment_result.gaps if enrichment_result else [],
        enrichment_priority=enrichment_result.priority if enrichment_result else "",
    )
