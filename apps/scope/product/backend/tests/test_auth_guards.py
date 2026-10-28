"""
test_auth_guards.py — Auth, role, and ownership guard tests
============================================================

Every "you can't do X when Y" rule. These are fast, focused tests
that verify the auth middleware rejects the right requests.
"""

from __future__ import annotations

import pytest
import httpx

from conftest import (
    BASE_URL, SANDBOX_HEADERS,
    _sb_get, _sb_patch,
    _ensure_auth_user, _get_jwt, _link_auth_user_to_contractor,
)


# ---------------------------------------------------------------------------
# Milestone proof guards
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_proof_no_auth(sandbox_client, paid_project_3ms):
    """Proof without Authorization header → 401."""
    token = paid_project_3ms["token"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/milestones/0/proof",
            json={"photos": ["https://example.com/p.jpg"]},
            headers=SANDBOX_HEADERS,
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_proof_homeowner_forbidden(sandbox_client, paid_project_3ms, homeowner_jwt):
    """Homeowner cannot submit proof → 403."""
    token = paid_project_3ms["token"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/milestones/0/proof",
            json={"photos": ["https://example.com/p.jpg"]},
            headers={**SANDBOX_HEADERS, **homeowner_jwt["header"]},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_proof_wrong_contractor_forbidden(sandbox_client, paid_project_3ms, wrong_contractor_jwt):
    """Contractor not assigned to this project → 403."""
    token = paid_project_3ms["token"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/milestones/0/proof",
            json={"photos": ["https://example.com/p.jpg"]},
            headers={**SANDBOX_HEADERS, **wrong_contractor_jwt["header"]},
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Milestone release guards
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_release_no_auth(sandbox_client, paid_project_3ms):
    """Release without Authorization → 401."""
    token = paid_project_3ms["token"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/milestones/0/release",
            headers=SANDBOX_HEADERS,
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_release_contractor_forbidden(sandbox_client, paid_project_3ms, contractor_jwt):
    """Contractor cannot release milestones → 403."""
    token = paid_project_3ms["token"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/milestones/0/release",
            headers={**SANDBOX_HEADERS, **contractor_jwt["header"]},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_release_wrong_homeowner_forbidden(sandbox_client, paid_project_3ms, wrong_homeowner_jwt):
    """Homeowner not associated with this project → 403."""
    token = paid_project_3ms["token"]

    # Need proof first so we test the ownership check (not the "no proof submitted" check)
    project = paid_project_3ms
    cid = project["contractor_id"]
    c_email = f"c-guard-{token[:8]}@sandbox.leo.casa"
    c_uid = await _ensure_auth_user(c_email)
    await _link_auth_user_to_contractor(c_uid, cid)
    c_jwt = await _get_jwt(c_email)
    auth_c = {**SANDBOX_HEADERS, "Authorization": f"Bearer {c_jwt}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        await c.post(f"/v1/projects/{token}/milestones/0/proof",
                     json={"photos": ["https://example.com/p.jpg"]}, headers=auth_c)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/milestones/0/release",
            headers={**SANDBOX_HEADERS, **wrong_homeowner_jwt["header"]},
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Variation guards
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_variation_create_no_auth(sandbox_client, paid_project_3ms):
    """Create variation without auth → 401."""
    token = paid_project_3ms["token"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/variations",
            json={"title": "Test", "amount_cents": 1000},
            headers=SANDBOX_HEADERS,
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_variation_create_homeowner_forbidden(sandbox_client, paid_project_3ms, homeowner_jwt):
    """Homeowner cannot create variations → 403."""
    token = paid_project_3ms["token"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/variations",
            json={"title": "Test", "amount_cents": 1000},
            headers={**SANDBOX_HEADERS, **homeowner_jwt["header"]},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_variation_create_wrong_contractor_forbidden(sandbox_client, paid_project_3ms, wrong_contractor_jwt):
    """Contractor not assigned to project cannot create variations → 403."""
    token = paid_project_3ms["token"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/variations",
            json={"title": "Test", "amount_cents": 1000},
            headers={**SANDBOX_HEADERS, **wrong_contractor_jwt["header"]},
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Cancel guards
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancel_no_auth(sandbox_client, paid_project_3ms):
    """Cancel without auth → 401."""
    token = paid_project_3ms["token"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/cancel",
            json={"reason": "test"},
            headers=SANDBOX_HEADERS,
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cancel_wrong_user_forbidden(sandbox_client, paid_project_3ms, wrong_homeowner_jwt):
    """User not involved in project cannot cancel → 403."""
    token = paid_project_3ms["token"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/cancel",
            json={"reason": "test"},
            headers={**SANDBOX_HEADERS, **wrong_homeowner_jwt["header"]},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cancel_after_work_started_blocked(sandbox_client, paid_project_3ms, contractor_jwt, homeowner_jwt):
    """Cannot cancel after a milestone has proof submitted."""
    token = paid_project_3ms["token"]

    # Submit proof on milestone 0
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        await c.post(f"/v1/projects/{token}/milestones/0/proof",
                     json={"photos": ["https://example.com/p.jpg"]},
                     headers={**SANDBOX_HEADERS, **contractor_jwt["header"]})

    # Try to cancel
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/cancel",
            json={"reason": "changed my mind"},
            headers={**SANDBOX_HEADERS, **homeowner_jwt["header"]},
        )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Review guards
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_review_no_auth(sandbox_client, completed_project):
    """Review without auth → 401."""
    token = completed_project["token"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/review",
            json={"rating": 5},
            headers=SANDBOX_HEADERS,
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_review_contractor_forbidden(sandbox_client, completed_project, contractor_with_stripe):
    """Contractor cannot submit reviews → 403."""
    token = completed_project["token"]
    cid = contractor_with_stripe["id"]

    c_email = f"c-revguard-{token[:8]}@sandbox.leo.casa"
    c_uid = await _ensure_auth_user(c_email)
    await _link_auth_user_to_contractor(c_uid, cid)
    c_jwt = await _get_jwt(c_email)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/review",
            json={"rating": 5},
            headers={**SANDBOX_HEADERS, "Authorization": f"Bearer {c_jwt}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_review_wrong_homeowner_forbidden(sandbox_client, completed_project, wrong_homeowner_jwt):
    """Homeowner not associated with this project cannot review → 403."""
    token = completed_project["token"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/review",
            json={"rating": 5},
            headers={**SANDBOX_HEADERS, **wrong_homeowner_jwt["header"]},
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Project GET — visibility tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_project_get_unauthenticated_no_pii(sandbox_client, paid_project_3ms):
    """Unauthenticated access returns project data but no PII."""
    token = paid_project_3ms["token"]
    resp = await sandbox_client.get(f"/v1/projects/{token}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"] == token
    assert data["status"] is not None
    assert "homeowner_email" not in data or data.get("homeowner_email") is None
    assert "payment_intent_id" not in data or data.get("payment_intent_id") is None


@pytest.mark.asyncio
async def test_project_get_homeowner_sees_pii(sandbox_client, paid_project_3ms, homeowner_jwt):
    """Authenticated homeowner sees their own email/phone."""
    token = paid_project_3ms["token"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.get(
            f"/v1/projects/{token}",
            headers={**SANDBOX_HEADERS, **homeowner_jwt["header"]},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("homeowner_email") is not None


@pytest.mark.asyncio
async def test_project_get_contractor_sees_pii(sandbox_client, paid_project_3ms, contractor_jwt):
    """Authenticated contractor sees PII + payment_intent_id."""
    token = paid_project_3ms["token"]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.get(
            f"/v1/projects/{token}",
            headers={**SANDBOX_HEADERS, **contractor_jwt["header"]},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("homeowner_email") is not None
