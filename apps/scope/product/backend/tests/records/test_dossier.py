"""Tests for :mod:`storage.dossier` — contractors table + canvas.

Covers:

- Idempotent :func:`get_or_create_contractor` — creates, then patches
  on subsequent calls for missing fields; ``canvas_token == id``
  invariant repaired if violated.
- Lookup helpers :func:`get_contractor_by_phone` and
  :func:`get_contractor_by_token`.
- :func:`set_contractor_phone` + :func:`add_conversation_note` +
  :func:`update_identity_overrides` — patch-only writes that preserve
  the dossier-first / identity-second ordering required by the
  409-safe invariant.
- :func:`add_contractor_source` — the two-phase write: the ``dossier``
  patch must succeed even if the ``name``/``phone`` patch fails
  (identity belongs to another contractor, 409). This is load-bearing
  per design D10.
- :func:`recompute_canvas` — pure function; exhaustive coverage of:
  source priority (reviews_count ranking), per-source fields staying
  attributed, merge rules for portfolio/reviews/social mentions,
  override precedence, verified threshold.
- :func:`save_and_recompute_canvas` — read/compute/write wiring.

All Supabase I/O is mocked via :mod:`respx`.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

import httpx
import pytest
import respx

from records.dossier import (
    add_contractor_source,
    add_conversation_note,
    get_contractor_by_phone,
    get_contractor_by_token,
    get_or_create_contractor,
    recompute_canvas,
    save_and_recompute_canvas,
    set_contractor_phone,
    update_identity_overrides,
    update_trust_signals,
)
from records.types import Contractor


SB_BASE = "http://127.0.0.1:54321"
CONTRACTORS_URL = f"{SB_BASE}/rest/v1/contractors"


def _row(**overrides: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "id": "hc-1",
        "canvas_token": "hc-1",
        "name": None,
        "phone": None,
        "provenance": None,
        "dossier": {},
        "canvas": None,
        "created_at": "2026-04-20T12:00:00+00:00",
        "updated_at": "2026-04-20T12:00:00+00:00",
    }
    base.update(overrides)
    return base


# ============================== get_or_create ================================


class TestGetOrCreate:
    @pytest.mark.asyncio
    async def test_creates_new_when_missing(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(201, json=[_row(id="hc-1", name="Pepe")])

        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(return_value=httpx.Response(200, json=[]))
            rx.post(CONTRACTORS_URL).mock(side_effect=_capture)
            contractor = await get_or_create_contractor("hc-1", name="Pepe")
        assert isinstance(contractor, Contractor)
        assert captured["id"] == "hc-1"
        assert captured["canvas_token"] == "hc-1"
        assert captured["name"] == "Pepe"
        assert contractor.id == "hc-1"
        assert contractor.name == "Pepe"

    @pytest.mark.asyncio
    async def test_repairs_bad_canvas_token(self, supabase_env: None) -> None:
        patch_bodies: List[Dict[str, Any]] = []

        def _capture(request: httpx.Request) -> httpx.Response:
            patch_bodies.append(json.loads(request.content.decode()))
            return httpx.Response(200, json=[_row(id="hc-1")])

        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(
                return_value=httpx.Response(
                    200, json=[_row(id="hc-1", canvas_token="NOT-hc-1")]
                )
            )
            rx.patch(CONTRACTORS_URL).mock(side_effect=_capture)
            contractor = await get_or_create_contractor("hc-1")
        assert any(p == {"canvas_token": "hc-1"} for p in patch_bodies)
        assert contractor.canvas_token == "hc-1"

    @pytest.mark.asyncio
    async def test_existing_row_patches_missing_name(
        self, supabase_env: None
    ) -> None:
        patch_bodies: List[Dict[str, Any]] = []

        def _capture(request: httpx.Request) -> httpx.Response:
            patch_bodies.append(json.loads(request.content.decode()))
            return httpx.Response(200, json=[_row(id="hc-1")])

        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(
                return_value=httpx.Response(200, json=[_row(id="hc-1", name=None)])
            )
            rx.patch(CONTRACTORS_URL).mock(side_effect=_capture)
            contractor = await get_or_create_contractor("hc-1", name="Pepe")
        assert {"name": "Pepe"} in patch_bodies
        assert contractor.name == "Pepe"

    @pytest.mark.asyncio
    async def test_existing_name_not_overridden(self, supabase_env: None) -> None:
        # No PATCH should fire when canvas_token + name are already
        # correct. We leave `assert_all_called=False` to permit the
        # zero-PATCH shape without respx flagging an unused route.
        async with respx.mock(assert_all_called=False) as rx:
            rx.get(CONTRACTORS_URL).mock(
                return_value=httpx.Response(
                    200, json=[_row(id="hc-1", name="Original", canvas_token="hc-1")]
                )
            )
            patch_route = rx.patch(CONTRACTORS_URL).mock(
                return_value=httpx.Response(200, json=[_row()])
            )
            contractor = await get_or_create_contractor("hc-1", name="Changed")
        assert not patch_route.called
        assert contractor.name == "Original"


# ============================== lookups ======================================


class TestLookups:
    @pytest.mark.asyncio
    async def test_by_phone_empty_returns_none(self, supabase_env: None) -> None:
        assert await get_contractor_by_phone("") is None

    @pytest.mark.asyncio
    async def test_by_phone_happy(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(
                return_value=httpx.Response(200, json=[_row(phone="+34611")])
            )
            contractor = await get_contractor_by_phone("+34611")
        assert contractor is not None
        assert contractor.phone == "+34611"

    @pytest.mark.asyncio
    async def test_by_phone_not_found(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(return_value=httpx.Response(200, json=[]))
            assert await get_contractor_by_phone("+34611") is None

    @pytest.mark.asyncio
    async def test_by_token_empty_returns_none(self, supabase_env: None) -> None:
        assert await get_contractor_by_token("") is None

    @pytest.mark.asyncio
    async def test_by_token_happy(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(
                return_value=httpx.Response(200, json=[_row(canvas_token="tok-9")])
            )
            contractor = await get_contractor_by_token("tok-9")
        assert contractor is not None
        assert contractor.canvas_token == "tok-9"


# ====================== set_contractor_phone =================================


class TestSetPhone:
    @pytest.mark.asyncio
    async def test_patches_phone(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(200, json=[_row(phone="+34611")])

        async with respx.mock() as rx:
            rx.patch(CONTRACTORS_URL).mock(side_effect=_capture)
            result = await set_contractor_phone("hc-1", "+34611")
        assert result is not None
        assert result.phone == "+34611"
        assert captured == {"phone": "+34611"}


# ====================== add_contractor_source ================================


class TestAddContractorSource:
    @pytest.mark.asyncio
    async def test_appends_new_source(self, supabase_env: None) -> None:
        patch_bodies: List[Dict[str, Any]] = []

        def _capture(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content.decode())
            patch_bodies.append(body)
            return httpx.Response(200, json=[_row()])

        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(
                return_value=httpx.Response(200, json=[_row(dossier={})])
            )
            rx.patch(CONTRACTORS_URL).mock(side_effect=_capture)
            await add_contractor_source(
                "hc-1",
                {
                    "source": "habitissimo",
                    "source_url": "https://h.com/x",
                    "rating": 4.5,
                    "review_count": 30,
                },
            )
        # first PATCH is dossier-only (two-phase invariant)
        assert "dossier" in patch_bodies[0]
        assert "name" not in patch_bodies[0]
        sources = patch_bodies[0]["dossier"]["sources"]
        assert len(sources) == 1
        assert sources[0]["source"] == "habitissimo"
        assert sources[0]["review_count"] == 30
        assert "scraped_at" in sources[0]

    @pytest.mark.asyncio
    async def test_dedupes_by_platform_and_url(self, supabase_env: None) -> None:
        existing_source = {
            "source": "habitissimo",
            "source_url": "https://h.com/x",
            "rating": 4.5,
            "review_count": 20,
            "scraped_at": "2026-01-01T00:00:00+00:00",
        }
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(200, json=[_row()])

        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(
                return_value=httpx.Response(
                    200, json=[_row(dossier={"sources": [existing_source]})]
                )
            )
            rx.patch(CONTRACTORS_URL).mock(side_effect=_capture)
            await add_contractor_source(
                "hc-1",
                {
                    "source": "habitissimo",
                    "source_url": "https://h.com/x",
                    "rating": 4.8,
                    "review_count": 50,
                },
            )
        sources = captured["dossier"]["sources"]
        # dedup: still 1 entry, refreshed with new data
        assert len(sources) == 1
        assert sources[0]["rating"] == 4.8
        assert sources[0]["review_count"] == 50

    @pytest.mark.asyncio
    async def test_two_phase_identity_after_dossier(
        self, supabase_env: None
    ) -> None:
        patch_bodies: List[Dict[str, Any]] = []

        def _capture(request: httpx.Request) -> httpx.Response:
            patch_bodies.append(json.loads(request.content.decode()))
            return httpx.Response(200, json=[_row()])

        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(
                return_value=httpx.Response(200, json=[_row()])
            )
            rx.patch(CONTRACTORS_URL).mock(side_effect=_capture)
            await add_contractor_source(
                "hc-1",
                {
                    "source": "h",
                    "source_url": "u",
                    "name": "Pepe",
                    "phone": "+34611",
                },
            )
        assert len(patch_bodies) == 2
        assert "dossier" in patch_bodies[0]
        assert "name" not in patch_bodies[0]
        assert patch_bodies[1] == {"name": "Pepe", "phone": "+34611"}

    @pytest.mark.asyncio
    async def test_identity_409_does_not_rollback_dossier(
        self, supabase_env: None
    ) -> None:
        # First PATCH (dossier) succeeds; second (identity) fails with 409.
        # Function must still return the Contractor from the dossier result.
        call_count = {"n": 0}

        def _capture(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            if call_count["n"] == 1:
                return httpx.Response(200, json=[_row(name="Pepe")])
            return httpx.Response(409, text="duplicate phone")

        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(
                return_value=httpx.Response(200, json=[_row()])
            )
            rx.patch(CONTRACTORS_URL).mock(side_effect=_capture)
            result = await add_contractor_source(
                "hc-1",
                {
                    "source": "h",
                    "source_url": "u",
                    "name": "Pepe",
                    "phone": "+34611",
                },
            )
        assert result is not None
        assert result.name == "Pepe"


# ====================== trust signals / conversation notes ===================


class TestTrustAndNotes:
    @pytest.mark.asyncio
    async def test_update_trust_signals(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(200, json=[_row()])

        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(
                return_value=httpx.Response(200, json=[_row(dossier={})])
            )
            rx.patch(CONTRACTORS_URL).mock(side_effect=_capture)
            result = await update_trust_signals(
                "hc-1",
                {"trust_score": 80, "nif_valid": True},
            )
        assert result is not None
        assert captured["dossier"]["trust_signals"] == {
            "trust_score": 80,
            "nif_valid": True,
        }

    @pytest.mark.asyncio
    async def test_trust_signals_target_missing_returns_none(
        self, supabase_env: None
    ) -> None:
        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(return_value=httpx.Response(200, json=[]))
            assert await update_trust_signals("missing", {"trust_score": 1}) is None

    @pytest.mark.asyncio
    async def test_add_conversation_note(self, supabase_env: None) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(200, json=[_row()])

        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(
                return_value=httpx.Response(200, json=[_row(dossier={})])
            )
            rx.patch(CONTRACTORS_URL).mock(side_effect=_capture)
            await add_conversation_note("hc-1", "needs weekend slots")
        notes = captured["dossier"]["conversation_notes"]
        assert len(notes) == 1
        assert notes[0]["text"] == "needs weekend slots"
        assert "timestamp" in notes[0]

    @pytest.mark.asyncio
    async def test_update_identity_overrides_also_patches_name(
        self, supabase_env: None
    ) -> None:
        captured: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content.decode()))
            return httpx.Response(200, json=[_row()])

        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(
                return_value=httpx.Response(200, json=[_row(dossier={})])
            )
            rx.patch(CONTRACTORS_URL).mock(side_effect=_capture)
            await update_identity_overrides(
                "hc-1",
                {"name": "Pepa", "nif": "12345678Z"},
            )
        assert captured["name"] == "Pepa"
        assert captured["dossier"]["identity_overrides"]["name"] == "Pepa"
        assert captured["dossier"]["identity_overrides"]["nif"] == "12345678Z"
        assert "updated_at" in captured["dossier"]["identity_overrides"]


# ====================== recompute_canvas (pure) ==============================


class TestRecomputeCanvas:
    def test_empty_dossier_returns_minimal_canvas(self) -> None:
        canvas = recompute_canvas({})
        assert canvas["business_name"] == ""
        assert canvas["trade"] == ""
        assert canvas["verified"] is False
        assert canvas["sources"] == []
        assert canvas["portfolio_images"] == []

    def test_most_reviewed_source_wins(self) -> None:
        dossier = {
            "sources": [
                {
                    "source": "habitissimo",
                    "name": "Biz1",
                    "review_count": 10,
                    "scraped_at": "2026-02-01T00:00:00Z",
                },
                {
                    "source": "google",
                    "name": "Biz2",
                    "review_count": 200,
                    "scraped_at": "2026-01-01T00:00:00Z",
                },
            ],
        }
        canvas = recompute_canvas(dossier)
        assert canvas["business_name"] == "Biz2"

    def test_recency_tiebreaker(self) -> None:
        dossier = {
            "sources": [
                {
                    "source": "a",
                    "name": "OlderBiz",
                    "review_count": 50,
                    "scraped_at": "2025-01-01T00:00:00Z",
                },
                {
                    "source": "b",
                    "name": "NewerBiz",
                    "review_count": 50,
                    "scraped_at": "2026-02-01T00:00:00Z",
                },
            ],
        }
        canvas = recompute_canvas(dossier)
        assert canvas["business_name"] == "NewerBiz"

    def test_overrides_beat_sources(self) -> None:
        dossier = {
            "identity_overrides": {"business_name": "CorrectName"},
            "sources": [
                {"name": "WrongName", "review_count": 100, "source": "x"}
            ],
        }
        canvas = recompute_canvas(dossier)
        assert canvas["business_name"] == "CorrectName"

    def test_portfolio_dedupe(self) -> None:
        dossier = {
            "sources": [
                {
                    "source": "a",
                    "portfolio_images": ["a.jpg", "b.jpg"],
                    "projects": [{"images": ["b.jpg", "c.jpg"]}],
                    "review_count": 10,
                },
            ],
        }
        canvas = recompute_canvas(dossier)
        assert canvas["portfolio_images"] == ["a.jpg", "b.jpg", "c.jpg"]

    def test_portfolio_caps_at_50(self) -> None:
        imgs = [f"img{i}.jpg" for i in range(80)]
        dossier = {
            "sources": [{"source": "a", "portfolio_images": imgs, "review_count": 1}]
        }
        canvas = recompute_canvas(dossier)
        assert len(canvas["portfolio_images"]) == 50

    def test_trust_score_60_marks_verified(self) -> None:
        dossier = {"trust_signals": {"trust_score": 60}}
        assert recompute_canvas(dossier)["verified"] is True

    def test_trust_score_59_marks_unverified(self) -> None:
        dossier = {"trust_signals": {"trust_score": 59}}
        assert recompute_canvas(dossier)["verified"] is False

    def test_reviews_attributed_per_source(self) -> None:
        dossier = {
            "sources": [
                {
                    "source": "a",
                    "review_count": 5,
                    "reviews": [
                        {"reviewer_name": "Juan", "rating": 5, "date": "2026-01-01", "text": "top"}
                    ],
                    "projects": [],
                },
                {
                    "source": "b",
                    "review_count": 7,
                    "reviews": [{"author": "Ana", "rating": 4}],
                    "projects": [],
                },
            ],
        }
        canvas = recompute_canvas(dossier)
        sources_out = canvas["sources"]
        a_src = next(s for s in sources_out if s["platform"] == "a")
        b_src = next(s for s in sources_out if s["platform"] == "b")
        assert a_src["reviews"][0]["author"] == "Juan"
        assert b_src["reviews"][0]["author"] == "Ana"

    def test_services_string_passes_through(self) -> None:
        # Single-line string (no comma) is returned as-is.
        dossier = {
            "sources": [
                {"source": "x", "services": "Plumbing and boilers", "review_count": 1}
            ],
        }
        canvas = recompute_canvas(dossier)
        assert canvas["services"] == "Plumbing and boilers"

    def test_services_comma_converted_to_newlines(self) -> None:
        dossier = {
            "sources": [
                {"source": "x", "services": "Plumbing, Boilers", "review_count": 1}
            ],
        }
        canvas = recompute_canvas(dossier)
        assert canvas["services"] == "Plumbing\nBoilers"

    def test_social_mentions_merged(self) -> None:
        dossier = {
            "trust_signals": {
                "fb_mentions": [
                    {"source_name": "FB Group", "url": "fb.com/x", "snippet": "recommended"}
                ],
                "forum_mentions": [
                    {"forum_name": "Forobots", "url": "f.com/y", "snippet": "bad vibes"}
                ],
            },
            "sources": [],
        }
        canvas = recompute_canvas(dossier)
        assert len(canvas["social_mentions"]) == 2
        sources = {m["source_name"] for m in canvas["social_mentions"]}
        assert "FB Group" in sources
        assert "Forobots" in sources


# ====================== save_and_recompute_canvas =============================


class TestSaveAndRecompute:
    @pytest.mark.asyncio
    async def test_not_found_returns_empty_dict(self, supabase_env: None) -> None:
        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(return_value=httpx.Response(200, json=[]))
            assert await save_and_recompute_canvas("missing") == {}

    @pytest.mark.asyncio
    async def test_happy_path_writes_canvas(self, supabase_env: None) -> None:
        patch_body: Dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            patch_body.update(json.loads(request.content.decode()))
            return httpx.Response(200, json=[_row()])

        async with respx.mock() as rx:
            rx.get(CONTRACTORS_URL).mock(
                return_value=httpx.Response(
                    200,
                    json=[
                        _row(
                            dossier={
                                "sources": [
                                    {
                                        "source": "g",
                                        "name": "Pepito Fontanería",
                                        "review_count": 42,
                                    }
                                ],
                                "trust_signals": {"trust_score": 80},
                            },
                        )
                    ],
                )
            )
            rx.patch(CONTRACTORS_URL).mock(side_effect=_capture)
            canvas = await save_and_recompute_canvas("hc-1")
        assert canvas["business_name"] == "Pepito Fontanería"
        assert canvas["verified"] is True
        assert patch_body["canvas"]["business_name"] == "Pepito Fontanería"
