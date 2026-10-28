"""
test_lifecycle.py — Full project lifecycle: quote → consent → pay → milestones → complete → review
==================================================================================================

Tests the happy path end-to-end with 3 milestones. Every state transition
is verified against the database. This is the "does the product work?" test.
"""

from __future__ import annotations

import pytest
import httpx

from conftest import (
    BASE_URL, SANDBOX_HEADERS,
    _sb_get, _sb_patch, _sb_insert, _sb_delete,
    _ensure_auth_user, _get_jwt, _link_auth_user_to_contractor,
    _cleanup_project, create_sandbox_quote,
    STRIPE_TEST_ACCOUNT_ID,
)


@pytest.mark.asyncio
async def test_lifecycle_3ms_happy_path_completes(sandbox_client, contractor_with_stripe):
    """Full lifecycle: finalize → consent → checkout → proof×3 → release×3 → complete → review.

    Uses 3 milestones because multi-milestone state transitions are where bugs hide.
    """
    cid = contractor_with_stripe["id"]

    # ── Step 1: Finalize quote ──────────────────────────────────────
    resp = await sandbox_client.post("/v1/quote/finalize", json={
        "contractor_id": cid,
        "quote_data": {
            "title": "Lifecycle Test — 3 Milestones",
            "description": "Full E2E lifecycle test",
            "line_items": [
                {"description": "Phase 1: Demolition", "amount": 500},
                {"description": "Phase 2: Plumbing", "amount": 500},
                {"description": "Phase 3: Finishing", "amount": 500},
            ],
            "service_fee_percent": 5,
            "iva_rate": 10,
            "homeowner_name": "Test Homeowner",
        },
    })
    assert resp.status_code == 200, f"Finalize failed: {resp.text}"
    token = resp.json()["token"]
    assert token

    try:
        # Verify quote is finalized
        rows = await _sb_get("quotes", {"token": token})
        assert rows[0]["status"] == "finalized"
        assert rows[0]["payment_status"] == "unpaid"
        milestones = rows[0]["milestones"]
        assert len(milestones) == 3
        assert all(m["status"] == "pending" for m in milestones)

        # ── Step 2: Record consent ──────────────────────────────────
        ho_email = f"ho-lifecycle-{token[:8]}@sandbox.leo.casa"
        await _sb_patch("quotes", {"token": token}, {"homeowner_email": ho_email})

        consent_resp = await sandbox_client.post(
            f"/v1/documents/{token}/record-consent",
            json={
                "homeowner_email": ho_email,
                "ip_address": "127.0.0.1",
                "user_agent": "pytest-lifecycle",
            },
        )
        assert consent_resp.status_code == 200
        consent_data = consent_resp.json()
        assert consent_data["ok"]
        assert consent_data["consent_id"]
        assert consent_data["document_hash"]

        # ── Step 3: Create checkout ─────────────────────────────────
        checkout_resp = await sandbox_client.post("/v1/payment/create-checkout", json={
            "quote_token": token,
            "homeowner_email": ho_email,
            "consent_id": consent_data["consent_id"],
        })
        assert checkout_resp.status_code == 200
        assert checkout_resp.json()["checkout_url"]

        # Verify payment_status changed to pending
        rows = await _sb_get("quotes", {"token": token})
        assert rows[0]["payment_status"] == "pending"

        # Simulate payment webhook: mark as paid
        ho_user_id = await _ensure_auth_user(ho_email)
        fake_pi = f"pi_test_lifecycle_{token[:8]}"
        await _sb_patch("quotes", {"token": token}, {
            "payment_status": "paid",
            "payment_intent_id": fake_pi,
            "status": "paid",
            "homeowner_auth_id": ho_user_id,
        })

        # ── Step 4: Auth setup ──────────────────────────────────────
        contractor_email = f"c-lifecycle-{cid[:8]}@sandbox.leo.casa"
        c_user_id = await _ensure_auth_user(contractor_email)
        await _link_auth_user_to_contractor(c_user_id, cid)
        c_jwt = await _get_jwt(contractor_email)
        ho_jwt = await _get_jwt(ho_email)

        auth_c = {**SANDBOX_HEADERS, "Authorization": f"Bearer {c_jwt}"}
        auth_ho = {**SANDBOX_HEADERS, "Authorization": f"Bearer {ho_jwt}"}

        # ── Step 5: Proof + Release for each milestone ──────────────
        for idx in range(3):
            # Contractor submits proof
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
                proof_resp = await c.post(
                    f"/v1/projects/{token}/milestones/{idx}/proof",
                    json={"photos": [f"https://example.com/proof_{idx}.jpg"], "note": f"Phase {idx+1} done"},
                    headers=auth_c,
                )
            assert proof_resp.status_code == 200, f"Proof {idx} failed: {proof_resp.text}"

            # Verify milestone status
            rows = await _sb_get("quotes", {"token": token})
            assert rows[0]["milestones"][idx]["status"] == "proof_submitted"

            if idx == 0:
                assert rows[0]["status"] == "in_progress"

            # Homeowner releases milestone
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
                release_resp = await c.post(
                    f"/v1/projects/{token}/milestones/{idx}/release",
                    headers=auth_ho,
                )
            assert release_resp.status_code == 200, f"Release {idx} failed: {release_resp.text}"
            release_data = release_resp.json()
            assert release_data["ok"]
            assert release_data["transfer_id"]

            # Verify milestone released
            rows = await _sb_get("quotes", {"token": token})
            assert rows[0]["milestones"][idx]["status"] == "released"

        # ── Step 6: Verify project completed ────────────────────────
        rows = await _sb_get("quotes", {"token": token})
        assert rows[0]["status"] == "complete"
        assert rows[0]["completed_at"] is not None

        # Verify last release indicated all_released
        assert release_data["all_released"] is True

        # ── Step 7: Submit review ───────────────────────────────────
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
            review_resp = await c.post(
                f"/v1/projects/{token}/review",
                json={"rating": 5, "body": "Excellent work on the renovation!"},
                headers=auth_ho,
            )
        assert review_resp.status_code == 200, f"Review failed: {review_resp.text}"

        # Verify review in DB
        reviews = await _sb_get("reviews", {"scope_token": token})
        assert len(reviews) == 1
        assert reviews[0]["rating"] == 5

        # Verify contractor rating updated
        contractors = await _sb_get("contractors", {"id": cid})
        assert contractors[0].get("review_count", 0) >= 1

        # ── Step 8: Invoice available ───────────────────────────────
        invoice_resp = await sandbox_client.get(f"/v1/documents/{token}/invoice")
        assert invoice_resp.status_code == 200

    finally:
        await _cleanup_project(token)
        await _sb_delete("contractors", {"id": cid})


@pytest.mark.asyncio
async def test_lifecycle_status_progression(sandbox_client, contractor_with_stripe):
    """Verify the project status transitions: finalized → paid → in_progress → complete."""
    cid = contractor_with_stripe["id"]

    resp = await sandbox_client.post("/v1/quote/finalize", json={
        "contractor_id": cid,
        "quote_data": {
            "title": "Status Progression Test",
            "description": "Track status at each step",
            "line_items": [
                {"description": "Phase 1", "amount": 300},
                {"description": "Phase 2", "amount": 300},
                {"description": "Phase 3", "amount": 300},
            ],
            "service_fee_percent": 5,
            "iva_rate": 10,
        },
    })
    token = resp.json()["token"]

    try:
        # Status: finalized
        rows = await _sb_get("quotes", {"token": token})
        assert rows[0]["status"] == "finalized"

        # Simulate payment → status: paid
        ho_email = f"ho-status-{token[:8]}@sandbox.leo.casa"
        ho_user_id = await _ensure_auth_user(ho_email)
        await _sb_patch("quotes", {"token": token}, {
            "payment_status": "paid",
            "status": "paid",
            "homeowner_email": ho_email,
            "homeowner_auth_id": ho_user_id,
            "payment_intent_id": f"pi_test_{token[:8]}",
        })

        rows = await _sb_get("quotes", {"token": token})
        assert rows[0]["status"] == "paid"

        # Setup auth
        c_email = f"c-status-{cid[:8]}@sandbox.leo.casa"
        c_uid = await _ensure_auth_user(c_email)
        await _link_auth_user_to_contractor(c_uid, cid)
        c_jwt = await _get_jwt(c_email)
        ho_jwt = await _get_jwt(ho_email)

        auth_c = {**SANDBOX_HEADERS, "Authorization": f"Bearer {c_jwt}"}
        auth_ho = {**SANDBOX_HEADERS, "Authorization": f"Bearer {ho_jwt}"}

        # First proof → status: in_progress
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
            await c.post(f"/v1/projects/{token}/milestones/0/proof",
                         json={"photos": ["https://example.com/p.jpg"]}, headers=auth_c)
        rows = await _sb_get("quotes", {"token": token})
        assert rows[0]["status"] == "in_progress"

        # Release all 3 milestones → status: complete
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
            await c.post(f"/v1/projects/{token}/milestones/0/release", headers=auth_ho)

        for idx in [1, 2]:
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
                await c.post(f"/v1/projects/{token}/milestones/{idx}/proof",
                             json={"photos": ["https://example.com/p.jpg"]}, headers=auth_c)
                await c.post(f"/v1/projects/{token}/milestones/{idx}/release", headers=auth_ho)

        rows = await _sb_get("quotes", {"token": token})
        assert rows[0]["status"] == "complete"

    finally:
        await _cleanup_project(token)
