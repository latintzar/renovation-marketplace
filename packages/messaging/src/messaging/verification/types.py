"""Pydantic models shared by ``routes/profile_import`` and the agent runtime.

Extracted verbatim from ``routes/profile_import.py`` lines 101-194 to
break the mutual-import cycle with ``leo_agent/verification.py``.

Field order is an **invariant**: the contractor dossier writes
``ProfileResult(**source).model_dump()`` into ``contractors.canvas_json``
as JSON and historical rows rely on v1 field ordering. Changing this
order silently corrupts comparison logic in
:func:`messaging.dossier.recompute_canvas`. Do not reorder fields
without a schema migration.

Pydantic version: v1 field-order-as-declared (v2 migration tracked
separately; until then we keep the declaration order exactly as it was
in the legacy ``routes/profile_import.py``).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

__all__ = [
    "ImportRequest",
    "Review",
    "Project",
    "PageChunk",
    "TeamMember",
    "Credential",
    "TrustSignals",
    "ProfileResult",
]


class ImportRequest(BaseModel):
    """Request payload for ``POST /api/profile-import``."""

    url: str
    contractor_id: str = ""


class Review(BaseModel):
    """One review signal pulled from a scrape source."""

    author: str = ""
    rating: Optional[float] = None
    text: str = ""
    date: str = ""


class Project(BaseModel):
    """One project row from a contractor's portfolio."""

    title: str = ""
    description: str = ""
    images: list[str] = []
    url: str = ""


class PageChunk(BaseModel):
    """One crawled page — text + images with source provenance."""

    url: str
    text: str = ""
    image_urls: list[str] = []


class TeamMember(BaseModel):
    """Contractor team member when surfaced by the site."""

    name: str = ""
    role: str = ""
    bio: str = ""
    image_url: str = ""


class Credential(BaseModel):
    """One license / accreditation / certification entry."""

    type: str = ""
    label: str = ""
    value: str = ""
    verified: bool = False


class TrustSignals(BaseModel):
    """Aggregate signals (VIES, REA, reviews, socials) — stored on :class:`ProfileResult`."""

    nif_valid: Optional[bool] = None
    nif_value: str = ""
    vies_valid: Optional[bool] = None
    vies_company_name: str = ""
    vies_address: str = ""
    rea_registered: Optional[bool] = None
    rea_status: str = ""
    review_sources: list[dict] = []
    review_avg_rating: Optional[float] = None
    review_total_count: int = 0
    fb_mentions: list[dict] = []
    fb_mention_count: int = 0
    forum_mentions: list[dict] = []
    forum_mention_count: int = 0
    trust_score: Optional[int] = None
    last_checked_at: str = ""


class ProfileResult(BaseModel):
    """Composite scrape result: signals + credentials + reviews + chunks.

    The canonical in-memory representation of everything we know about a
    contractor from public sources. Persists to
    ``contractors.canvas_json`` via :func:`messaging.dossier.add_source`.
    """

    source: str  # "habitissimo" | "houzz" | "hogami" | "website"
    source_url: str
    name: str = ""
    description: str = ""
    location: str = ""
    trade: str = ""
    rating: Optional[float] = None
    review_count: int = 0
    years_experience: Optional[int] = None
    phone: str = ""
    phone_source: str = ""
    email: str = ""
    website: str = ""
    avatar_url: str = ""
    cover_images: list[str] = []
    portfolio_images: list[str] = []
    projects: list[Project] = []
    reviews: list[Review] = []
    services: list[str] = []
    people: list[TeamMember] = []
    credentials: list[Credential] = []
    address: str = ""
    typical_job_cost: str = ""
    qa_pairs: list[dict] = []
    raw_about: str = ""
    page_chunks: list[PageChunk] = []
    merged_from_websites: list[str] = []
    review_summary: str = ""
    trust_signals: Optional[TrustSignals] = None
