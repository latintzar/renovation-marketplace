"""
Profile Import Workflow
========================

Deterministic pipeline: scrape a tradesperson profile URL → cross-pollinate
other platforms → verify identity + reputation → write to dossier → recompute
canvas.

This workflow wraps existing functions from:
    routes/profile_import.py   — scrapers, cross_pollinate, enrich_credentials_from_web
    leo_agent/verification.py  — run_verification_checks
    leo_agent/contractor_dossier.py — add_source, update_trust_signals, save_and_recompute

Calling Hermes is not required. The entire pipeline is synchronous Python
run in a thread executor so it can be called from async contexts without
blocking the event loop.

Entry points
------------
run_profile_import(contractor_id, source_url)
    Full pipeline for a known contractor (HC record already exists).
    Returns a ProfileImportResult.

run_profile_import_for_phone(phone, source_url, name, trade, city)
    Convenience wrapper that looks up or creates the contractor record by
    phone before running the import. Used by enrich_contractor Hermes tool.

Workflow signal (written to dossier.workflow_signals on completion)
-------------------------------------------------------------------
    {
        "workflow": "profile_import",
        "contractor_id": str,
        "source_url": str,
        "trust_score": int | None,
        "canvas_token": str | None,
        "completed_at": ISO-8601 str,
        "status": "ok" | "partial" | "failed",
    }

Hermes picks this up on the next turn via ephemeral_context.py:
    "Profile import complete for hc-abc123. Trust score: 78/100.
     Canvas ready at leo.casa/canvas/xyz. Share when the moment is right."
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
class ProfileImportResult:
    ok: bool
    contractor_id: str = ""
    trust_score: Optional[int] = None
    canvas_token: Optional[str] = None
    source_url: str = ""
    platform: str = ""
    name: str = ""
    error: str = ""
    partial: bool = False

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "contractor_id": self.contractor_id,
            "trust_score": self.trust_score,
            "canvas_token": self.canvas_token,
            "source_url": self.source_url,
            "platform": self.platform,
            "name": self.name,
            "error": self.error,
            "partial": self.partial,
        }


# ─── Main entry point ─────────────────────────────────────────────────

async def run_profile_import(
    contractor_id: str,
    source_url: str,
) -> ProfileImportResult:
    """Full Profile Import pipeline for a known contractor.

    Steps:
    1. Detect platform from URL.
    2. Scrape the profile (run in thread executor — all scrapers are sync).
    3. Cross-pollinate: discover other platform profiles for the same person.
    4. Enrich credentials from web (NIF/CIF, registrations, via SearXNG).
    5. Run verification checks (NIF checksum, VIES, REA, reviews, social proof).
    6. Write scraped data to dossier.sources[].
    7. Write trust signals to dossier.trust_signals.
    8. Recompute canvas from dossier.
    9. Write workflow signal (Hermes notification).
    10. Return ProfileImportResult.
    """
    loop = asyncio.get_event_loop()
    now = datetime.now(timezone.utc).isoformat()

    from routes.profile_import import (
        detect_platform,
        cross_pollinate,
        enrich_credentials_from_web,
        scrape_habitissimo,
        scrape_houzz,
        scrape_cronoshare,
        scrape_hogami,
        scrape_website,
        structure_profile_with_llm,
        _deduplicate_portfolio,
    )
    from messaging import run_verification_checks
    from records.dossier import (
        get_or_create,
        add_source,
        update_trust_signals,
        save_and_recompute,
        _select,
    )

    platform = detect_platform(source_url)
    logger.info(
        "ProfileImport | id=%s platform=%s url=%s",
        contractor_id[:12], platform, source_url[:60],
    )

    # ── Step 1: Scrape ────────────────────────────────────────────────
    try:
        if platform == "habitissimo":
            profile = await loop.run_in_executor(
                None,
                lambda: scrape_habitissimo(source_url, merge_external_site=True),
            )
        elif platform == "houzz":
            profile = await loop.run_in_executor(None, scrape_houzz, source_url)
        elif platform == "hogami":
            profile = await loop.run_in_executor(None, scrape_hogami, source_url)
        elif platform == "cronoshare":
            profile = await loop.run_in_executor(None, scrape_cronoshare, source_url)
        elif platform == "webel":
            return ProfileImportResult(
                ok=False,
                contractor_id=contractor_id,
                source_url=source_url,
                platform=platform,
                error="AppWebel/Webel import not supported (datacenter IP blocked).",
            )
        else:
            profile = await loop.run_in_executor(None, scrape_website, source_url)

        _deduplicate_portfolio(profile)
        logger.info(
            "ProfileImport | scraped | id=%s name=%s platform=%s reviews=%d",
            contractor_id[:12],
            (profile.name or "?")[:30],
            platform,
            profile.review_count or 0,
        )
    except Exception as e:
        logger.error("ProfileImport | scrape failed | id=%s: %s", contractor_id[:12], e)
        return ProfileImportResult(
            ok=False,
            contractor_id=contractor_id,
            source_url=source_url,
            platform=platform,
            error=f"Scrape failed: {e}",
        )

    # ── Step 2: LLM structuring (website-sourced profiles only) ───────
    if platform == "website" and profile.page_chunks:
        try:
            profile = await loop.run_in_executor(None, structure_profile_with_llm, profile)
        except Exception as e:
            logger.warning("ProfileImport | LLM structuring failed (non-fatal): %s", e)

    # ── Step 3: Cross-pollinate ───────────────────────────────────────
    try:
        profile = await loop.run_in_executor(None, cross_pollinate, profile)
    except Exception as e:
        logger.warning("ProfileImport | cross-pollination failed (non-fatal): %s", e)

    # ── Step 4: Web credential enrichment ────────────────────────────
    try:
        await loop.run_in_executor(None, enrich_credentials_from_web, profile)
    except Exception as e:
        logger.warning("ProfileImport | credential enrichment failed (non-fatal): %s", e)

    # ── Step 5: Verification (NIF, VIES, REA, reviews, social proof) ──
    try:
        await loop.run_in_executor(None, run_verification_checks, profile)
    except Exception as e:
        logger.warning("ProfileImport | verification failed (non-fatal): %s", e)

    # ── Step 6: Write source to dossier ──────────────────────────────
    source_data = profile.model_dump()
    source_data["workflow"] = "profile_import"

    partial = False
    try:
        await add_source(contractor_id, source_data)
    except Exception as e:
        logger.error("ProfileImport | dossier.add_source failed | id=%s: %s", contractor_id[:12], e)
        partial = True

    # ── Step 7: Write trust signals ───────────────────────────────────
    trust_score = None
    if profile.trust_signals:
        try:
            signals = profile.trust_signals.model_dump()
            await update_trust_signals(contractor_id, signals)
            trust_score = signals.get("trust_score")
        except Exception as e:
            logger.error(
                "ProfileImport | trust_signals write failed | id=%s: %s",
                contractor_id[:12], e,
            )
            partial = True

    # ── Step 8: Recompute canvas ──────────────────────────────────────
    canvas_token = None
    try:
        canvas = await save_and_recompute(contractor_id)
        row = await _select("id", contractor_id)
        canvas_token = row.get("canvas_token") if row else None
    except Exception as e:
        logger.error(
            "ProfileImport | canvas recompute failed | id=%s: %s",
            contractor_id[:12], e,
        )
        partial = True

    # ── Step 9: Write workflow signal for Hermes ──────────────────────
    await _write_workflow_signal(
        contractor_id=contractor_id,
        source_url=source_url,
        trust_score=trust_score,
        canvas_token=canvas_token,
        status="partial" if partial else "ok",
    )

    logger.info(
        "ProfileImport | complete | id=%s score=%s canvas=%s partial=%s",
        contractor_id[:12],
        trust_score,
        canvas_token,
        partial,
    )

    return ProfileImportResult(
        ok=True,
        contractor_id=contractor_id,
        trust_score=trust_score,
        canvas_token=canvas_token,
        source_url=source_url,
        platform=platform,
        name=profile.name or "",
        partial=partial,
    )


# ─── Convenience wrapper for phone-based lookup ───────────────────────

async def run_profile_import_for_phone(
    phone: str,
    source_url: str,
    name: str = "",
    trade: str = "",
    city: str = "",
) -> ProfileImportResult:
    """Look up or create a contractor record by phone, then run Profile Import.

    Used by the enrich_contractor Hermes tool when it wants the full
    pipeline instead of just the phone-based verification.
    """
    import uuid as _uuid
    from records.dossier import get_by_phone, get_or_create

    digits = phone.strip().lstrip("+").replace(" ", "").replace("-", "")

    row = await get_by_phone(digits)
    if row:
        contractor_id = row["id"]
    else:
        contractor_id = f"hc-{_uuid.uuid4()}"
        await get_or_create(contractor_id, name=name, phone=digits)

    return await run_profile_import(contractor_id, source_url)


# ─── Workflow signal ──────────────────────────────────────────────────

async def _write_workflow_signal(
    contractor_id: str,
    source_url: str,
    trust_score: Optional[int],
    canvas_token: Optional[str],
    status: str,
) -> None:
    """Append a workflow_signal to the contractor dossier.

    ephemeral_context.py reads dossier.workflow_signals and injects
    the latest signal as a "note passed to Hermes" on the next turn.
    """
    from records.dossier import _select, _patch

    try:
        row = await _select("id", contractor_id)
        if not row:
            return
        dossier = row.get("dossier") or {}
        signals = dossier.get("workflow_signals") or []
        signals.append({
            "workflow": "profile_import",
            "contractor_id": contractor_id,
            "source_url": source_url,
            "trust_score": trust_score,
            "canvas_token": canvas_token,
            "canvas_url": f"leo.casa/canvas/{canvas_token}" if canvas_token else None,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
        })
        # Keep last 10 signals — avoid unbounded growth
        dossier["workflow_signals"] = signals[-10:]
        await _patch(contractor_id, {"dossier": dossier})
        logger.debug(
            "ProfileImport | workflow_signal written | id=%s status=%s",
            contractor_id[:12], status,
        )
    except Exception as e:
        logger.warning("ProfileImport | workflow_signal write failed: %s", e)
