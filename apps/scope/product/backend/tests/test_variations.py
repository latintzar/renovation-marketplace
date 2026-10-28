"""
test_variations.py — Change order (variation) tests
====================================================

Tests the variation order flow: contractor proposes → homeowner approves/declines.
Covers happy path, double-action guard, wrong-project guard, and not-found.
"""

from __future__ import annotations

import uuid
import pytest
import httpx

from conftest import (
    BASE_URL, SANDBOX_HEADERS,
    _sb_get, _sb_patch, _sb_insert, _sb_delete,
    _ensure_auth_user, _get_jwt, _link_auth_user_to_contractor,
)


async def _auth_for_project(project: dict, contractor: dict) -> tuple[dict, dict]:
    """Create auth users and return (contractor_headers, homeowner_headers)."""
    token = project["token"]
    cid = contractor["id"]

    c_email = f"c-var-{token[:8]}@sandbox.leo.casa"
    c_uid = await _ensure_auth_user(c_email)
    await _link_auth_user_to_contractor(c_uid, cid)
    c_jwt = await _get_jwt(c_email)

    ho_email = project["homeowner_email"]
    ho_uid = await _ensure_auth_user(ho_email)
    await _sb_patch("quotes", {"token": token}, {"homeowner_auth_id": ho_uid})
    ho_jwt = await _get_jwt(ho_email)

    auth_c = {**SANDBOX_HEADERS, "Authorization": f"Bearer {c_jwt}"}
    auth_ho = {**SANDBOX_HEADERS, "Authorization": f"Bearer {ho_jwt}"}
    return auth_c, auth_ho


@pytest.mark.asyncio
async def test_variation_create_and_approve(sandbox_client, paid_project_3ms, contractor_with_stripe):
    """Contractor proposes a variation → homeowner approves → Stripe Checkout created."""
    auth_c, auth_ho = await _auth_for_project(paid_project_3ms, contractor_with_stripe)
    token = paid_project_3ms["token"]

    # Contractor creates variation
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        create_resp = await c.post(
            f"/v1/projects/{token}/variations",
            json={
                "title": "Extra plumbing work",
                "description": "Need to reroute a pipe",
                "amount_cents": 25000,
                "reason": "Unexpected pipe layout",
            },
            headers=auth_c,
        )
    assert create_resp.status_code == 200, f"Create variation failed: {create_resp.text}"

    # Verify variation in DB
    variations = await _sb_get("variation_orders", {"scope_token": token})
    assert len(variations) >= 1
    var = variations[0]
    assert var["status"] == "pending"
    assert var["amount_cents"] == 25000
    variation_id = var["id"]

    # Homeowner approves
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        approve_resp = await c.post(
            f"/v1/projects/{token}/variations/{variation_id}/approve",
            headers=auth_ho,
        )
    assert approve_resp.status_code == 200
    data = approve_resp.json()
    assert data["ok"]
    assert data["checkout_url"]

    # Verify status updated
    variations = await _sb_get("variation_orders", {"id": variation_id})
    assert variations[0]["status"] == "approved"
    assert variations[0]["checkout_session_id"]

    # Cleanup
    await _sb_delete("variation_orders", {"scope_token": token})


@pytest.mark.asyncio
async def test_variation_create_and_decline(sandbox_client, paid_project_3ms, contractor_with_stripe):
    """Contractor proposes → homeowner declines → variation marked declined."""
    auth_c, auth_ho = await _auth_for_project(paid_project_3ms, contractor_with_stripe)
    token = paid_project_3ms["token"]

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        await c.post(f"/v1/projects/{token}/variations",
                     json={"title": "New tiles", "amount_cents": 15000}, headers=auth_c)

    variations = await _sb_get("variation_orders", {"scope_token": token})
    variation_id = variations[0]["id"]

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        decline_resp = await c.post(
            f"/v1/projects/{token}/variations/{variation_id}/decline",
            headers=auth_ho,
        )
    assert decline_resp.status_code == 200

    variations = await _sb_get("variation_orders", {"id": variation_id})
    assert variations[0]["status"] == "declined"

    await _sb_delete("variation_orders", {"scope_token": token})


@pytest.mark.asyncio
async def test_variation_already_actioned(sandbox_client, paid_project_3ms, contractor_with_stripe):
    """Approving an already-approved variation returns 409."""
    auth_c, auth_ho = await _auth_for_project(paid_project_3ms, contractor_with_stripe)
    token = paid_project_3ms["token"]

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        await c.post(f"/v1/projects/{token}/variations",
                     json={"title": "Extra work", "amount_cents": 10000}, headers=auth_c)

    variations = await _sb_get("variation_orders", {"scope_token": token})
    variation_id = variations[0]["id"]

    # Approve once
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        await c.post(f"/v1/projects/{token}/variations/{variation_id}/approve", headers=auth_ho)

    # Try again → 409
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        second = await c.post(
            f"/v1/projects/{token}/variations/{variation_id}/approve",
            headers=auth_ho,
        )
    assert second.status_code == 409

    await _sb_delete("variation_orders", {"scope_token": token})


@pytest.mark.asyncio
async def test_variation_wrong_project_token(sandbox_client, paid_project_3ms, contractor_with_stripe):
    """Approving a variation with mismatched project token returns 400."""
    auth_c, auth_ho = await _auth_for_project(paid_project_3ms, contractor_with_stripe)
    token = paid_project_3ms["token"]

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        await c.post(f"/v1/projects/{token}/variations",
                     json={"title": "Misroute test", "amount_cents": 5000}, headers=auth_c)

    variations = await _sb_get("variation_orders", {"scope_token": token})
    variation_id = variations[0]["id"]

    # Use wrong token in URL
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        resp = await c.post(
            f"/v1/projects/wrong-token-12345/variations/{variation_id}/approve",
            headers=auth_ho,
        )
    # Should be 400 or 404 (wrong project)
    assert resp.status_code in (400, 404)

    await _sb_delete("variation_orders", {"scope_token": token})


@pytest.mark.asyncio
async def test_variation_not_found(sandbox_client, paid_project_3ms, contractor_with_stripe):
    """Approving a non-existent variation returns 404."""
    _, auth_ho = await _auth_for_project(paid_project_3ms, contractor_with_stripe)
    token = paid_project_3ms["token"]

    fake_id = str(uuid.uuid4())
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        resp = await c.post(
            f"/v1/projects/{token}/variations/{fake_id}/approve",
            headers=auth_ho,
        )
    assert resp.status_code == 404
