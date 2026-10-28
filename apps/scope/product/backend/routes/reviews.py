"""
Reviews — Post-completion homeowner review
==========================================

POST /v1/projects/:token/review — Homeowner submits a star rating + optional body
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import CurrentUser, require_auth
from core import sb_headers, sb_url
from core import http_client
from core import api_error
from routes.projects import get_quote

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateReviewBody(BaseModel):
    rating: int
    body: Optional[str] = None


@router.post("/projects/{token}/review")
async def create_review(
    token: str,
    req: CreateReviewBody,
    caller: CurrentUser = Depends(require_auth),
):
    """Homeowner submits a review after job completion."""
    if caller.role != "homeowner":
        raise api_error(403, "Only the homeowner can submit a review")

    if req.rating < 1 or req.rating > 5:
        raise api_error(400, "Rating must be between 1 and 5")

    quote = await get_quote(token)

    # Identity check
    if caller.id != quote.get("homeowner_auth_id") and caller.email != quote.get("homeowner_email"):
        raise api_error(403, "Only the project homeowner can submit reviews")

    if quote.get("status") != "complete":
        raise api_error(400, "Project is not complete yet")

    contractor_id = quote["contractor_id"]

    async with http_client(timeout=10) as client:
        ins_resp = await client.post(
            f"{sb_url()}/reviews",
            json={
                "scope_token": token,
                "contractor_id": contractor_id,
                "homeowner_auth_id": caller.id,
                "rating": req.rating,
                "body": req.body,
            },
            headers=sb_headers(),
        )
    if ins_resp.status_code == 409:
        raise api_error(409, "Review already submitted for this project")
    if ins_resp.status_code not in (200, 201):
        raise api_error(500, "Failed to save review")

    # Recompute contractor avg_rating
    async with http_client(timeout=10) as client:
        reviews_resp = await client.get(
            f"{sb_url()}/reviews",
            params={"contractor_id": f"eq.{contractor_id}", "select": "rating"},
            headers=sb_headers(),
        )
    if reviews_resp.status_code == 200 and reviews_resp.json():
        all_ratings = [r["rating"] for r in reviews_resp.json()]
        avg = round(sum(all_ratings) / len(all_ratings), 2)
        count = len(all_ratings)
        async with http_client(timeout=10) as client:
            await client.patch(
                f"{sb_url()}/contractors",
                params={"id": f"eq.{contractor_id}"},
                json={"avg_rating": avg, "review_count": count},
                headers=sb_headers(),
            )

    return {"ok": True, "message": "Review submitted"}
