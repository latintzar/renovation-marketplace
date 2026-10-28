"""
test_completion.py — Post-completion: reviews, invoice, agreement, consent
===========================================================================

Tests the end of the project lifecycle: reviews update contractor profiles,
invoices are only available after completion, agreements render correctly,
and consent recording creates proper audit trails.
"""

from __future__ import annotations

import pytest
import httpx

from conftest import (
    BASE_URL, SANDBOX_HEADERS,
    _sb_get, _sb_patch, _sb_delete,
    _ensure_auth_user, _get_jwt, _link_auth_user_to_contractor,
    _cleanup_project,
)


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_review_creates_and_updates_rating(sandbox_client, completed_project, contractor_with_stripe):
    """Review stores rating and updates contractor avg_rating."""
    token = completed_project["token"]
    cid = contractor_with_stripe["id"]

    ho_email = completed_project["homeowner_email"]
    ho_uid = await _ensure_auth_user(ho_email)
    await _sb_patch("quotes", {"token": token}, {"homeowner_auth_id": ho_uid})
    ho_jwt = await _get_jwt(ho_email)
    auth_ho = {**SANDBOX_HEADERS, "Authorization": f"Bearer {ho_jwt}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(
            f"/v1/projects/{token}/review",
            json={"rating": 4, "body": "Good work, minor issues with timing"},
            headers=auth_ho,
        )
    assert resp.status_code == 200

    reviews = await _sb_get("reviews", {"scope_token": token})
    assert len(reviews) == 1
    assert reviews[0]["rating"] == 4
    assert reviews[0]["body"] == "Good work, minor issues with timing"

    contractors = await _sb_get("contractors", {"id": cid})
    assert contractors[0].get("avg_rating") is not None
    assert contractors[0].get("review_count", 0) >= 1


@pytest.mark.asyncio
async def test_review_duplicate_rejected(sandbox_client, completed_project, contractor_with_stripe):
    """Submitting a second review for the same project returns 409."""
    token = completed_project["token"]

    ho_email = completed_project["homeowner_email"]
    ho_uid = await _ensure_auth_user(ho_email)
    await _sb_patch("quotes", {"token": token}, {"homeowner_auth_id": ho_uid})
    ho_jwt = await _get_jwt(ho_email)
    auth_ho = {**SANDBOX_HEADERS, "Authorization": f"Bearer {ho_jwt}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        first = await c.post(f"/v1/projects/{token}/review",
                             json={"rating": 5}, headers=auth_ho)
        assert first.status_code == 200

        second = await c.post(f"/v1/projects/{token}/review",
                              json={"rating": 3}, headers=auth_ho)
        assert second.status_code == 409


@pytest.mark.asyncio
async def test_review_on_incomplete_rejected(sandbox_client, paid_project_3ms):
    """Cannot review a project that isn't complete."""
    token = paid_project_3ms["token"]

    ho_email = paid_project_3ms["homeowner_email"]
    ho_uid = await _ensure_auth_user(ho_email)
    await _sb_patch("quotes", {"token": token}, {"homeowner_auth_id": ho_uid})
    ho_jwt = await _get_jwt(ho_email)
    auth_ho = {**SANDBOX_HEADERS, "Authorization": f"Bearer {ho_jwt}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        resp = await c.post(f"/v1/projects/{token}/review",
                            json={"rating": 5}, headers=auth_ho)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_review_rating_validation(sandbox_client, completed_project, contractor_with_stripe):
    """Rating must be 1-5."""
    token = completed_project["token"]

    ho_email = completed_project["homeowner_email"]
    ho_uid = await _ensure_auth_user(ho_email)
    await _sb_patch("quotes", {"token": token}, {"homeowner_auth_id": ho_uid})
    ho_jwt = await _get_jwt(ho_email)
    auth_ho = {**SANDBOX_HEADERS, "Authorization": f"Bearer {ho_jwt}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as c:
        low = await c.post(f"/v1/projects/{token}/review",
                           json={"rating": 0}, headers=auth_ho)
        assert low.status_code == 400

        high = await c.post(f"/v1/projects/{token}/review",
                            json={"rating": 6}, headers=auth_ho)
        assert high.status_code == 400


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invoice_only_after_complete(sandbox_client, paid_project_3ms):
    """Invoice endpoint returns 400 for non-complete projects."""
    token = paid_project_3ms["token"]
    resp = await sandbox_client.get(f"/v1/documents/{token}/invoice")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_invoice_renders_after_complete(sandbox_client, completed_project):
    """Invoice renders HTML after project completion."""
    token = completed_project["token"]
    resp = await sandbox_client.get(f"/v1/documents/{token}/invoice")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Agreement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agreement_html_renders(sandbox_client, paid_project_3ms):
    """Agreement renders as HTML with project data."""
    token = paid_project_3ms["token"]
    resp = await sandbox_client.get(f"/v1/documents/{token}/agreement")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consent_records_hash(sandbox_client, contractor_with_stripe):
    """Consent recording creates a row with document_hash and consent_id."""
    cid = contractor_with_stripe["id"]

    # Create a fresh quote for this test
    resp = await sandbox_client.post("/v1/quote/finalize", json={
        "contractor_id": cid,
        "quote_data": {
            "title": "Consent Test",
            "description": "Test consent recording",
            "line_items": [{"description": "Work", "amount": 500}],
            "service_fee_percent": 5,
            "iva_rate": 10,
        },
    })
    token = resp.json()["token"]
    ho_email = f"ho-consent-{token[:8]}@sandbox.leo.casa"
    await _sb_patch("quotes", {"token": token}, {"homeowner_email": ho_email})

    try:
        consent_resp = await sandbox_client.post(
            f"/v1/documents/{token}/record-consent",
            json={
                "homeowner_email": ho_email,
                "ip_address": "192.168.1.1",
                "user_agent": "pytest-consent-test",
                "session_id": "test-session-123",
            },
        )
        assert consent_resp.status_code == 200
        data = consent_resp.json()
        assert data["ok"]
        assert data["consent_id"]
        assert len(data["document_hash"]) == 64  # SHA-256 hex

        # Verify consent stored in DB
        consents = await _sb_get("consents", {"scope_token": token})
        assert len(consents) >= 1
        assert consents[0]["email"] == ho_email
        assert consents[0]["document_hash"] == data["document_hash"]

        # Verify quote updated with consent_id
        quotes = await _sb_get("quotes", {"token": token})
        assert quotes[0].get("consent_id") == data["consent_id"]

    finally:
        await _cleanup_project(token)
