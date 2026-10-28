"""
Job Inbox — Contractor Discovery Concierge
============================================

Manages jobs (homeowner briefs sent out for contractor discovery) and the
token-accessed inbox that homeowners use to see ranked contractor responses.

Tables: jobs, job_responses (created via Supabase management API).
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import bedrock_client
from core import sb_url, sb_headers, sb_key
from core import http_client
from core import api_error

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Supabase helpers ─────────────────────────────────────────────────



# ── Data Models ──────────────────────────────────────────────────────

class CreateJobRequest(BaseModel):
    brief: Dict[str, Any]
    homeowner_phone: str = ""
    homeowner_user_id: str = ""
    brief_photos: List[str] = []


class AddResponseRequest(BaseModel):
    contractor_phone: str
    contractor_name: str = ""
    source: str = "direct"
    houzz_profile_url: str = ""
    voice_note_url: str = ""
    voice_transcript: str = ""
    reaction: str = ""
    site_visit_needs: str = ""
    availability: str = ""
    profile: Dict[str, Any] = {}
    onboarding_complete: bool = False


class RankRequest(BaseModel):
    pass  # no body needed — uses the job's brief + existing responses


# ── Job CRUD ─────────────────────────────────────────────────────────

def _generate_inbox_token() -> str:
    return secrets.token_urlsafe(16)


async def create_job(
    brief: Dict[str, Any],
    homeowner_phone: str = "",
    homeowner_user_id: str = "",
    brief_photos: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a new job and return the row including inbox_token."""
    if not sb_url or not sb_key:
        raise api_error(500, "Database not configured")

    token = _generate_inbox_token()
    row = {
        "brief": brief,
        "homeowner_phone": homeowner_phone or None,
        "homeowner_user_id": homeowner_user_id or None,
        "brief_photos": brief_photos or [],
        "inbox_token": token,
        "status": "collecting",
    }

    async with http_client(timeout=12) as client:
        resp = await client.post(
            f"{sb_url()}/jobs",
            headers={**sb_headers(), "Prefer": "return=representation"},
            json=row,
        )
        if resp.status_code not in (200, 201):
            logger.error("create_job failed | status=%s body=%s", resp.status_code, resp.text[:300])
            raise api_error(500, "Failed to create job")
        rows = resp.json()
        created = rows[0] if isinstance(rows, list) and rows else rows
        logger.info("Job created | id=%s token=%s phone=%s", created.get("id", "?")[:8], token[:8], homeowner_phone[:8] if homeowner_phone else "?")
        return created


async def get_job_by_token(token: str) -> Optional[Dict[str, Any]]:
    if not sb_url or not sb_key:
        return None
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/jobs",
            params={"inbox_token": f"eq.{token}", "select": "*", "limit": "1"},
            headers=sb_headers(),
        )
        if resp.status_code == 200:
            rows = resp.json()
            return rows[0] if rows else None
    return None


async def get_job_by_id(job_id: str) -> Optional[Dict[str, Any]]:
    if not sb_url or not sb_key:
        return None
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/jobs",
            params={"id": f"eq.{job_id}", "select": "*", "limit": "1"},
            headers=sb_headers(),
        )
        if resp.status_code == 200:
            rows = resp.json()
            return rows[0] if rows else None
    return None


async def update_job(job_id: str, updates: Dict[str, Any]) -> bool:
    if not sb_url or not sb_key:
        return False
    async with http_client(timeout=10) as client:
        resp = await client.patch(
            f"{sb_url()}/jobs?id=eq.{job_id}",
            headers={**sb_headers(), "Prefer": "return=minimal"},
            json=updates,
        )
        return resp.status_code in (200, 204)


async def get_active_job_for_phone(homeowner_phone: str) -> Optional[Dict[str, Any]]:
    """Return the most recent active job for a homeowner phone number.

    Used by the WhatsApp webhook to inject enrichment_needed signals into
    the ephemeral context for homeowner conversation turns.

    Returns None if no active job is found or on any error.
    """
    if not homeowner_phone:
        return None
    if not sb_url or not sb_key:
        return None
    # Normalise: strip leading + and whitespace for comparison robustness
    phone_digits = homeowner_phone.lstrip("+").replace(" ", "").replace("-", "")
    try:
        async with http_client(timeout=8) as client:
            resp = await client.get(
                f"{sb_url()}/jobs",
                params={
                    "homeowner_phone": f"eq.{homeowner_phone}",
                    "status": "in.(collecting,active)",
                    "select": "id,brief,enrichment_needed,status,created_at",
                    "order": "created_at.desc",
                    "limit": "1",
                },
                headers=sb_headers(),
            )
            if resp.status_code == 200:
                rows = resp.json()
                if rows:
                    return rows[0]
    except Exception as exc:
        logger.debug("get_active_job_for_phone | %s | %s", homeowner_phone[:8] + "***", exc)
    return None




async def add_response(job_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    if not sb_url or not sb_key:
        raise api_error(500, "Database not configured")

    row = {
        "job_id": job_id,
        "contractor_phone": data.get("contractor_phone", ""),
        "contractor_name": data.get("contractor_name", ""),
        "source": data.get("source", "direct"),
        "houzz_profile_url": data.get("houzz_profile_url", ""),
        "voice_note_url": data.get("voice_note_url") or None,
        "voice_transcript": data.get("voice_transcript") or None,
        "reaction": data.get("reaction") or None,
        "site_visit_needs": data.get("site_visit_needs") or None,
        "availability": data.get("availability") or None,
        "profile": data.get("profile", {}),
        "onboarding_complete": data.get("onboarding_complete", False),
        "outreach_stage": data.get("outreach_stage", "discovered"),
        "followup_count": data.get("followup_count", 0),
        "last_outreach_at": data.get("last_outreach_at") or None,
    }

    async with http_client(timeout=10) as client:
        resp = await client.post(
            f"{sb_url()}/job_responses",
            headers={**sb_headers(), "Prefer": "return=representation"},
            json=row,
        )
        if resp.status_code not in (200, 201):
            logger.error("add_response failed | status=%s body=%s", resp.status_code, resp.text[:300])
            raise api_error(500, "Failed to add response")
        rows = resp.json()
        result = rows[0] if isinstance(rows, list) and rows else rows
        logger.info("Response added | job=%s contractor=%s source=%s", job_id[:8], data.get("contractor_phone", "?")[:8], data.get("source"))
        return result


async def update_response(response_id: str, updates: Dict[str, Any]) -> bool:
    if not sb_url or not sb_key:
        return False
    async with http_client(timeout=10) as client:
        resp = await client.patch(
            f"{sb_url()}/job_responses?id=eq.{response_id}",
            headers={**sb_headers(), "Prefer": "return=minimal"},
            json=updates,
        )
        return resp.status_code in (200, 204)


async def get_responses_for_job(job_id: str) -> List[Dict[str, Any]]:
    if not sb_url or not sb_key:
        return []
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/job_responses",
            params={
                "job_id": f"eq.{job_id}",
                "select": "*",
                "order": "ai_rank.asc.nullslast,created_at.asc",
            },
            headers=sb_headers(),
        )
        if resp.status_code == 200:
            return resp.json() or []
    return []


async def find_response_by_phone(job_id: str, phone: str) -> Optional[Dict[str, Any]]:
    """Find an existing response for a contractor phone on a job."""
    if not sb_url or not sb_key:
        return None
    clean = phone.strip().lstrip("+").replace(" ", "").replace("-", "")
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/job_responses",
            params={
                "job_id": f"eq.{job_id}",
                "contractor_phone": f"like.*{clean}",
                "select": "*",
                "limit": "1",
            },
            headers=sb_headers(),
        )
        if resp.status_code == 200:
            rows = resp.json()
            return rows[0] if rows else None
    return None


async def find_job_for_contractor_phone(phone: str) -> Optional[Dict[str, Any]]:
    """Find the most recent active job that has an outreach to this contractor."""
    if not sb_url or not sb_key:
        return None
    clean = phone.strip().lstrip("+").replace(" ", "").replace("-", "")
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/job_responses",
            params={
                "contractor_phone": f"like.*{clean}",
                "select": "id,job_id,contractor_phone,source,onboarding_complete",
                "order": "created_at.desc",
                "limit": "1",
            },
            headers=sb_headers(),
        )
        if resp.status_code == 200:
            rows = resp.json()
            if rows:
                job = await get_job_by_id(rows[0]["job_id"])
                if job and job.get("status") in ("collecting", "ready"):
                    return {**rows[0], "job": job}
    return None


# ── AI Ranking ───────────────────────────────────────────────────────

async def rank_responses(job_id: str) -> List[Dict[str, Any]]:
    """AI-rank all responses for a job against the brief. Returns updated responses."""
    job = await get_job_by_id(job_id)
    if not job:
        raise api_error(404, "Job not found")

    responses = await get_responses_for_job(job_id)
    if not responses:
        return []

    brief = job.get("brief", {})

    candidates = []
    for r in responses:
        info = {
            "id": r["id"],
            "name": r.get("contractor_name") or "Unknown",
            "phone": r.get("contractor_phone", ""),
            "source": r.get("source", "direct"),
            "voice_transcript": r.get("voice_transcript") or "",
            "profile": r.get("profile") or {},
            "houzz_profile_url": r.get("houzz_profile_url") or "",
            "onboarding_complete": r.get("onboarding_complete", False),
        }
        candidates.append(info)

    prompt = f"""You are ranking contractor responses for a homeowner's job brief.

## Job Brief
{json.dumps(brief, ensure_ascii=False, indent=2)}

## Contractor Responses ({len(candidates)} total)
{json.dumps(candidates, ensure_ascii=False, indent=2)}

Rank these contractors from best to worst fit for this job. Consider:
1. Relevance of their trade/experience to the job
2. Quality and enthusiasm of their voice note response
3. Whether they completed onboarding (profile import)
4. Their online presence (Houzz ratings, reviews)
5. Availability and willingness

Return a JSON array with one object per contractor:
[{{"id": "response-uuid", "rank": 1, "commentary": "One sentence explaining why"}}]

Return ONLY the JSON array, no other text."""

    try:
        client = bedrock_client("eu-west-1")
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}],
        })
        resp = client.invoke_model(modelId="eu.anthropic.claude-sonnet-4-20250514-v1:0", body=body)
        result_text = json.loads(resp["body"].read())["content"][0]["text"]

        start = result_text.find("[")
        end = result_text.rfind("]") + 1
        if start >= 0 and end > start:
            rankings = json.loads(result_text[start:end])
        else:
            logger.warning("rank_responses: could not parse JSON from LLM response")
            return responses

        for ranking in rankings:
            rid = ranking.get("id")
            rank_num = ranking.get("rank")
            commentary = ranking.get("commentary", "")
            if rid and rank_num is not None:
                await update_response(rid, {"ai_rank": rank_num, "ai_commentary": commentary})

        return await get_responses_for_job(job_id)

    except Exception as exc:
        logger.error("rank_responses failed | %s", exc, exc_info=True)
        return responses


# ── API Routes ───────────────────────────────────────────────────────

@router.post("/jobs")
async def api_create_job(req: CreateJobRequest):
    job = await create_job(
        brief=req.brief,
        homeowner_phone=req.homeowner_phone,
        homeowner_user_id=req.homeowner_user_id,
        brief_photos=req.brief_photos,
    )
    return {
        "ok": True,
        "job_id": job.get("id"),
        "inbox_token": job.get("inbox_token"),
        "inbox_url": f"http://127.0.0.1:18260/app/inbox/{job.get('inbox_token')}",
    }


@router.get("/inbox/{token}")
async def api_get_inbox(token: str):
    job = await get_job_by_token(token)
    if not job:
        raise api_error(404, "Job not found")

    responses = await get_responses_for_job(job["id"])

    return {
        "job": {
            "id": job["id"],
            "brief": job.get("brief", {}),
            "brief_photos": job.get("brief_photos", []),
            "status": job.get("status"),
            "outreach_count": job.get("outreach_count", 0),
            "created_at": job.get("created_at"),
        },
        "responses": [
            {
                "id": r["id"],
                "contractor_name": r.get("contractor_name") or "Contractor",
                "contractor_phone": r.get("contractor_phone", ""),
                "source": r.get("source", "direct"),
                "houzz_profile_url": r.get("houzz_profile_url"),
                "voice_transcript": r.get("voice_transcript"),
                "reaction": r.get("reaction"),
                "site_visit_needs": r.get("site_visit_needs"),
                "availability": r.get("availability"),
                "profile": r.get("profile", {}),
                "ai_rank": r.get("ai_rank"),
                "ai_commentary": r.get("ai_commentary"),
                "onboarding_complete": r.get("onboarding_complete", False),
                "created_at": r.get("created_at"),
            }
            for r in responses
        ],
        "total_responses": len(responses),
    }


@router.post("/jobs/{job_id}/responses")
async def api_add_response(job_id: str, req: AddResponseRequest):
    job = await get_job_by_id(job_id)
    if not job:
        raise api_error(404, "Job not found")

    result = await add_response(job_id, req.model_dump())
    return {"ok": True, "response_id": result.get("id")}


@router.patch("/jobs/{job_id}/responses/{response_id}")
async def api_update_response(job_id: str, response_id: str, updates: Dict[str, Any]):
    safe_fields = {
        "contractor_name", "voice_note_url", "voice_transcript",
        "reaction", "site_visit_needs", "availability",
        "profile", "onboarding_complete", "houzz_profile_url",
        "outreach_stage", "followup_count", "last_outreach_at",
    }
    filtered = {k: v for k, v in updates.items() if k in safe_fields}
    if not filtered:
        raise api_error(400, "No valid fields to update")

    ok = await update_response(response_id, filtered)
    if not ok:
        raise api_error(500, "Update failed")
    return {"ok": True}


@router.post("/jobs/{job_id}/rank")
async def api_rank_responses(job_id: str):
    ranked = await rank_responses(job_id)
    return {"ok": True, "ranked_count": len(ranked)}


@router.patch("/jobs/{job_id}")
async def api_update_job(job_id: str, updates: Dict[str, Any]):
    safe_fields = {"status", "houzz_candidates", "fb_candidates", "outreach_count"}
    filtered = {k: v for k, v in updates.items() if k in safe_fields}
    if not filtered:
        raise api_error(400, "No valid fields to update")

    ok = await update_job(job_id, filtered)
    if not ok:
        raise api_error(500, "Update failed")
    return {"ok": True}


# ── Ops token (founder-only) ─────────────────────────────────────────
# A fixed secret token for the ops monitoring page. Generated once,
# stored in env. If not set, falls back to a hash of the service role key.

def _get_ops_token() -> str:
    explicit = os.getenv("OPS_MONITOR_TOKEN", "")
    if explicit:
        return explicit
    if key:
        import hashlib
        return hashlib.sha256(f"ops-{key[:20]}".encode()).hexdigest()[:24]
    return "ops-fallback-token"


@router.post("/inbox/{token}/approve-outreach")
async def api_approve_outreach(token: str):
    """
    Homeowner approves a contractor's outreach — marks the job as 'contractor_selected'
    and updates the job status so the contractor knows they were chosen.
    Called from the homeowner inbox when they tap "Approve" on a response.
    """
    job = await get_job_by_token(token)
    if not job:
        raise api_error(404, "Job not found")

    if not sb_url or not sb_key:
        raise api_error(500, "Database not configured")

    async with http_client(timeout=10) as client:
        resp = await client.patch(
            f"{sb_url()}/jobs",
            params={"id": f"eq.{job['id']}"},
            headers={**sb_headers(), "Prefer": "return=minimal"},
            json={"status": "contractor_selected"},
        )
        if resp.status_code not in (200, 204):
            logger.error(
                "approve-outreach patch failed | job=%s status=%s body=%s",
                job["id"][:8], resp.status_code, resp.text[:200]
            )
            raise api_error(500, "Failed to update job status")

    logger.info("Homeowner approved outreach | job=%s token=%s", job["id"][:8], token)
    return {"ok": True, "job_id": job["id"], "status": "contractor_selected"}


@router.get("/ops/{token}")
async def api_ops_dashboard(token: str):
    """Founder-only ops view: all jobs, all outreach, all responses."""
    if token != _get_ops_token():
        raise api_error(403, "Invalid ops token")

    if not sb_url or not sb_key:
        raise api_error(500, "Database not configured")

    async with http_client(timeout=15) as client:
        jobs_resp = await client.get(
            f"{sb_url()}/jobs",
            params={"select": "*", "order": "created_at.desc", "limit": "50"},
            headers=sb_headers(),
        )
        jobs = jobs_resp.json() if jobs_resp.status_code == 200 else []

        all_responses_resp = await client.get(
            f"{sb_url()}/job_responses",
            params={"select": "*", "order": "created_at.desc", "limit": "200"},
            headers=sb_headers(),
        )
        all_responses = all_responses_resp.json() if all_responses_resp.status_code == 200 else []

    responses_by_job: Dict[str, list] = {}
    for r in all_responses:
        jid = r.get("job_id", "")
        responses_by_job.setdefault(jid, []).append(r)

    result = []
    for job in jobs:
        jid = job["id"]
        brief = job.get("brief", {})
        resps = responses_by_job.get(jid, [])

        responded = [r for r in resps if r.get("voice_transcript")]
        onboarded = [r for r in resps if r.get("onboarding_complete")]

        stages = {}
        for r in resps:
            s = r.get("outreach_stage", "discovered")
            stages[s] = stages.get(s, 0) + 1

        result.append({
            "id": jid,
            "title": brief.get("title", "Untitled"),
            "location": brief.get("location", ""),
            "status": job.get("status", ""),
            "homeowner_phone": job.get("homeowner_phone", ""),
            "inbox_token": job.get("inbox_token", ""),
            "inbox_url": f"http://127.0.0.1:18260/app/inbox/{job.get('inbox_token', '')}",
            "outreach_count": job.get("outreach_count", 0),
            "total_responses": len(resps),
            "responded": len(responded),
            "onboarded": len(onboarded),
            "pipeline": stages,
            "created_at": job.get("created_at"),
            "contractors": [
                {
                    "id": r["id"],
                    "name": r.get("contractor_name") or "?",
                    "phone": r.get("contractor_phone", ""),
                    "source": r.get("source", ""),
                    "has_voice": bool(r.get("voice_transcript")),
                    "reaction": (r.get("reaction") or "")[:100],
                    "availability": r.get("availability") or "",
                    "onboarded": r.get("onboarding_complete", False),
                    "ai_rank": r.get("ai_rank"),
                    "ai_commentary": (r.get("ai_commentary") or "")[:120],
                    "houzz_url": r.get("houzz_profile_url") or "",
                    "outreach_stage": r.get("outreach_stage", "discovered"),
                    "followup_count": r.get("followup_count", 0),
                    "created_at": r.get("created_at"),
                }
                for r in resps
            ],
        })

    overall_pipeline = {}
    for r in all_responses:
        s = r.get("outreach_stage", "discovered")
        overall_pipeline[s] = overall_pipeline.get(s, 0) + 1

    return {
        "ops_token": token,
        "total_jobs": len(jobs),
        "total_outreach": sum(j.get("outreach_count", 0) for j in jobs),
        "total_responses": len(all_responses),
        "pipeline": overall_pipeline,
        "jobs": result,
    }
