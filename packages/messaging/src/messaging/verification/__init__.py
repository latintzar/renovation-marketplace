"""Verification — NIF/VIES/REA + social-proof checks, plus the Pydantic model set.

Structural purpose: **break the mutual import between
``leo_agent/verification.py`` and ``routes/profile_import.py``.**

Pre-migration the import graph was:

::

    routes/profile_import.py  ──> leo_agent/verification.py   (6 edges)
    leo_agent/verification.py ──> routes/profile_import.py    (1 edge: ProfileResult etc.)

Edge 7 closed the cycle. Python tolerated it at runtime because both sides
load during FastAPI startup before either is called, but:

* mypy/pyright couldn't tell which side was "first"
* Adding a top-level statement that touched ``ProfileResult`` from either
  side gave partially-initialised-module errors.

Post-migration dependency graph (all one-way):

::

    routes/profile_import.py  ──> messaging.verification.types
    routes/profile_import.py  ──> messaging.verification.api
    messaging.verification.api  ──> messaging.verification.types

Zero reverse edges. The cycle is broken at the verification boundary.

Two modules:

* :mod:`~.types` — Pydantic models (``ImportRequest``, ``Review``,
  ``Project``, ``PageChunk``, ``TeamMember``, ``Credential``,
  ``TrustSignals``, ``ProfileResult``). Field order preserved 1:1 with
  pre-migration so ``contractors.canvas_json`` rows stay compatible.
* :mod:`~.api` — verification functions (``validate_nif``, ``check_vies``,
  ``check_rea``, ``run_verification_checks``, ``run_social_proof_checks``,
  ``enrich_contractor_from_phone``, etc.).
"""

from __future__ import annotations

from .api import (
    check_rea,
    check_vies,
    enrich_contractor_from_phone,
    enrich_credentials_from_web,
    expand_fb_queries,
    run_social_proof_checks,
    run_verification_checks,
    search_fb_posts,
    search_forum_posts,
    search_review_signals,
    search_social_proof,
    validate_nif,
)
from .types import (
    Credential,
    ImportRequest,
    PageChunk,
    ProfileResult,
    Project,
    Review,
    TeamMember,
    TrustSignals,
)

__all__ = [
    # Types
    "ImportRequest",
    "Review",
    "Project",
    "PageChunk",
    "TeamMember",
    "Credential",
    "TrustSignals",
    "ProfileResult",
    # API
    "validate_nif",
    "check_vies",
    "check_rea",
    "search_review_signals",
    "search_fb_posts",
    "search_forum_posts",
    "search_social_proof",
    "run_verification_checks",
    "run_social_proof_checks",
    "enrich_contractor_from_phone",
    "enrich_credentials_from_web",
    "expand_fb_queries",
]
