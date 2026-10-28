"""
test_milestones.py — Milestone phase variations
================================================

Tests the core of the product: proof submission, release, rejection (dispute),
resubmission, last-milestone completion, idempotency, and boundary conditions.
All tests use 3-5 milestones because multi-milestone state is where bugs hide.
"""

from __future__ import annotations

import pytest
import httpx

from conftest import (
    BASE_URL, SANDBOX_HEADERS,
    _sb_get, _sb_patch, _sb_insert, _sb_delete,
    _ensure_auth_user, _get_jwt, _link_auth_user_to_contractor,
    _cleanup_project,
)


# ---------------------------------------------------------------------------
# Helper: set up auth for a paid project
# ---------------------------------------------------------------------------

async def _auth_for_project(project: dict, contractor: dict) -> tuple[dict, dict, str, str]:
    """Create auth users, link contractor, return (auth_c_headers, auth_ho_headers, c_jwt, ho_jwt)."""
    token = project["token"]
    cid = contractor["id"]

    c_email = f"c-ms-{token[:8]}@sandbox.leo.casa"
    c_uid = await _ensure_auth_user(c_email)
    await _link_auth_user_to_contractor(c_uid, cid)
    c_jwt = await _get_jwt(c_email)

    ho_email = project["homeowner_email"]
    ho_uid = await _ensure_auth_user(ho_email)
    await _sb_patch("quotes", {"token": token}, {"homeowner_auth_id": ho_uid})
    ho_jwt = await _get_jwt(ho_email)

    auth_c = {**SANDBOX_HEADERS, "Authorization": f"Bearer {c_jwt}"}
    auth_ho = {**SANDBOX_HEADERS, "Authorization": f"Bearer {ho_jwt}"}
    return auth_c, auth_ho, c_jwt, ho_jwt


@pytest.mark.asyncio
async def test_milestone_proof_advances_to_in_progress(sandbox_client, paid_project_3ms, contractor_with_stripe):
    """First proof submission transitions project from paid → in_progress."""
    auth_c, _, _, _ = await _auth_for_project(paid_project_3ms, contractor_with_stripe)
    token = paid_project_3ms["token"]

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        resp = await c.post(
            f"/v1/projects/{token}/milestones/0/proof",
            json={"photos": ["https://example.com/demo.jpg"], "note": "Phase 1 started"},
            headers=auth_c,
        )
    assert resp.status_code == 200

    rows = await _sb_get("quotes", {"token": token})
    assert rows[0]["milestones"][0]["status"] == "proof_submitted"
    assert rows[0]["status"] == "in_progress"


@pytest.mark.asyncio
async def test_milestone_release_creates_transfer(sandbox_client, paid_project_3ms, contractor_with_stripe):
    """Releasing a milestone creates a Stripe transfer and marks it released."""
    auth_c, auth_ho, _, _ = await _auth_for_project(paid_project_3ms, contractor_with_stripe)
    token = paid_project_3ms["token"]

    # Submit proof first
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        await c.post(f"/v1/projects/{token}/milestones/0/proof",
                     json={"photos": ["https://example.com/p.jpg"]}, headers=auth_c)
        release = await c.post(f"/v1/projects/{token}/milestones/0/release", headers=auth_ho)

    assert release.status_code == 200
    data = release.json()
    assert data["ok"]
    assert data["transfer_id"]
    assert data["transfer_id"].startswith("tr_") or data["transfer_id"] == "idempotent-duplicate"

    rows = await _sb_get("quotes", {"token": token})
    assert rows[0]["milestones"][0]["status"] == "released"


@pytest.mark.asyncio
async def test_milestone_dispute_resubmit_approve(sandbox_client, paid_project_3ms, contractor_with_stripe):
    """Homeowner disputes proof → contractor resubmits → homeowner approves."""
    auth_c, auth_ho, _, _ = await _auth_for_project(paid_project_3ms, contractor_with_stripe)
    token = paid_project_3ms["token"]

    # Contractor submits proof
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        await c.post(f"/v1/projects/{token}/milestones/0/proof",
                     json={"photos": ["https://example.com/bad.jpg"], "note": "First attempt"},
                     headers=auth_c)

    # Homeowner opens dispute (rejects)
    dispute_resp = await sandbox_client.post("/v1/dispute/open", json={
        "quote_token": token,
        "milestone_index": 0,
        "homeowner_name": "Test Homeowner",
        "homeowner_phone": "34600000099",
        "reason": "Work quality is below standard",
    })
    assert dispute_resp.status_code == 200
    assert dispute_resp.json()["ok"]

    # Verify milestone is disputed
    rows = await _sb_get("quotes", {"token": token})
    assert rows[0]["milestones"][0]["status"] == "disputed"

    # Contractor resubmits proof (overwrites disputed status back to proof_submitted)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        resubmit = await c.post(
            f"/v1/projects/{token}/milestones/0/proof",
            json={"photos": ["https://example.com/fixed.jpg"], "note": "Fixed the issues"},
            headers=auth_c,
        )
    assert resubmit.status_code == 200

    rows = await _sb_get("quotes", {"token": token})
    assert rows[0]["milestones"][0]["status"] == "proof_submitted"

    # Homeowner approves
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        release = await c.post(f"/v1/projects/{token}/milestones/0/release", headers=auth_ho)
    assert release.status_code == 200

    rows = await _sb_get("quotes", {"token": token})
    assert rows[0]["milestones"][0]["status"] == "released"


@pytest.mark.asyncio
async def test_milestone_last_release_completes_project(sandbox_client, paid_project_3ms, contractor_with_stripe):
    """Releasing the last milestone auto-completes the project."""
    auth_c, auth_ho, _, _ = await _auth_for_project(paid_project_3ms, contractor_with_stripe)
    token = paid_project_3ms["token"]

    for idx in range(3):
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
            await c.post(f"/v1/projects/{token}/milestones/{idx}/proof",
                         json={"photos": ["https://example.com/p.jpg"]}, headers=auth_c)
            release = await c.post(f"/v1/projects/{token}/milestones/{idx}/release", headers=auth_ho)
        assert release.status_code == 200

    # Last release should indicate all_released
    assert release.json()["all_released"] is True

    rows = await _sb_get("quotes", {"token": token})
    assert rows[0]["status"] == "complete"
    assert rows[0]["completed_at"] is not None


@pytest.mark.asyncio
async def test_milestone_double_release_idempotent(sandbox_client, paid_project_3ms, contractor_with_stripe):
    """Releasing an already-released milestone returns 409."""
    auth_c, auth_ho, _, _ = await _auth_for_project(paid_project_3ms, contractor_with_stripe)
    token = paid_project_3ms["token"]

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        await c.post(f"/v1/projects/{token}/milestones/0/proof",
                     json={"photos": ["https://example.com/p.jpg"]}, headers=auth_c)
        first = await c.post(f"/v1/projects/{token}/milestones/0/release", headers=auth_ho)
        assert first.status_code == 200

        second = await c.post(f"/v1/projects/{token}/milestones/0/release", headers=auth_ho)
        assert second.status_code == 409


@pytest.mark.asyncio
async def test_milestone_invalid_index(sandbox_client, paid_project_3ms, contractor_with_stripe):
    """Submitting proof for a non-existent milestone returns 400."""
    auth_c, _, _, _ = await _auth_for_project(paid_project_3ms, contractor_with_stripe)
    token = paid_project_3ms["token"]

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        resp = await c.post(f"/v1/projects/{token}/milestones/99/proof",
                            json={"photos": ["https://example.com/p.jpg"]}, headers=auth_c)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_milestone_proof_on_unpaid(sandbox_client, unpaid_project, contractor_with_stripe):
    """Cannot submit proof on an unpaid project."""
    token = unpaid_project["token"]
    cid = contractor_with_stripe["id"]

    c_email = f"c-unpaid-{token[:8]}@sandbox.leo.casa"
    c_uid = await _ensure_auth_user(c_email)
    await _link_auth_user_to_contractor(c_uid, cid)
    c_jwt = await _get_jwt(c_email)
    auth_c = {**SANDBOX_HEADERS, "Authorization": f"Bearer {c_jwt}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        resp = await c.post(f"/v1/projects/{token}/milestones/0/proof",
                            json={"photos": ["https://example.com/p.jpg"]}, headers=auth_c)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_milestone_5ms_full_cycle(sandbox_client, paid_project_5ms, contractor_with_stripe):
    """Full proof+release cycle across 5 milestones — stress test for state tracking."""
    auth_c, auth_ho, _, _ = await _auth_for_project(paid_project_5ms, contractor_with_stripe)
    token = paid_project_5ms["token"]

    for idx in range(5):
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
            proof = await c.post(
                f"/v1/projects/{token}/milestones/{idx}/proof",
                json={"photos": [f"https://example.com/proof_{idx}.jpg"], "note": f"Phase {idx+1}"},
                headers=auth_c,
            )
            assert proof.status_code == 200, f"Proof {idx} failed: {proof.text}"

            release = await c.post(f"/v1/projects/{token}/milestones/{idx}/release", headers=auth_ho)
            assert release.status_code == 200, f"Release {idx} failed: {release.text}"

    rows = await _sb_get("quotes", {"token": token})
    assert rows[0]["status"] == "complete"
    assert all(m["status"] == "released" for m in rows[0]["milestones"])
