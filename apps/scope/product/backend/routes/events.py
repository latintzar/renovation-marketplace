"""
Events — Activity event ingestion for Customer 360
===================================================

Receives frontend-fired events and persists them to the activity_events table.
This powers the Customer 360 timeline in the admin/support sidebar.

PostHog handles analytics; this table handles the per-user event history that
the Intercom Canvas Kit or Crisp sidebar can query.

Endpoint:
  POST /api/events/track  — Ingest a single event
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core import sb_url, sb_headers
from core import http_client
from core import api_error

logger = logging.getLogger(__name__)
router = APIRouter()




class TrackEventRequest(BaseModel):
    event: str
    user_id: Optional[str] = None
    quote_token: Optional[str] = None
    phone: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    is_sandbox: bool = False


@router.post("/api/events/track")
async def track_event(req: TrackEventRequest):
    """Ingest an activity event from the frontend.

    Stores the event in the activity_events table. This is the data source
    for the Customer 360 aggregation API and the support tool sidebar.

    Fire-and-forget from the frontend — errors are silently swallowed so
    tracking failures never break the user experience.
    """
    if not req.event:
        raise api_error(400, "event name required")

    if not sb_url or not sb_key:
        # Silently succeed if DB isn't configured — tracking should never block UX
        logger.warning("events/track: Supabase not configured — event dropped | event=%s", req.event)
        return {"ok": True, "stored": False}

    row = {
        "event": req.event,
        "user_id": req.user_id or None,
        "quote_token": req.quote_token or None,
        "phone": req.phone or None,
        "properties": req.properties or {},
        "is_sandbox": req.is_sandbox,
    }

    try:
        async with http_client(timeout=5) as client:
            resp = await client.post(
                f"{sb_url()}/activity_events",
                json=row,
                headers=sb_headers(),
            )
        if resp.status_code not in (200, 201):
            logger.warning(
                "events/track insert failed: %d | event=%s user=%s",
                resp.status_code, req.event, (req.user_id or "")[:12],
            )
            return {"ok": True, "stored": False}
    except Exception as exc:
        logger.warning("events/track exception: %s | event=%s", exc, req.event)
        return {"ok": True, "stored": False}

    logger.debug(
        "Event tracked | event=%s user=%s scope=%s sandbox=%s",
        req.event, (req.user_id or "")[:12], (req.quote_token or "")[:8], req.is_sandbox,
    )
    return {"ok": True, "stored": True}
