"""
test_messages.py — In-job chat messaging tests
================================================

Tests the messaging flow between contractor and homeowner
during an active (paid) project.
"""

from __future__ import annotations

import pytest
import httpx

from conftest import (
    BASE_URL, SANDBOX_HEADERS,
    _sb_get, _sb_delete,
)


@pytest.mark.asyncio
async def test_message_contractor_sends(sandbox_client, paid_project_3ms):
    """Contractor sends a message — stored in job_messages."""
    token = paid_project_3ms["token"]

    resp = await sandbox_client.post("/v1/messages/send", json={
        "quote_token": token,
        "sender_role": "contractor",
        "sender_id": paid_project_3ms["contractor_id"],
        "body": "Starting work on Phase 1 tomorrow",
    })
    assert resp.status_code == 200
    assert resp.json()["ok"]

    # Verify in DB
    messages = await _sb_get("job_messages", {"scope_token": token})
    assert len(messages) >= 1
    assert any(m["body"] == "Starting work on Phase 1 tomorrow" for m in messages)

    await _sb_delete("job_messages", {"scope_token": token})


@pytest.mark.asyncio
async def test_message_homeowner_sends(sandbox_client, paid_project_3ms):
    """Homeowner sends a message."""
    token = paid_project_3ms["token"]

    resp = await sandbox_client.post("/v1/messages/send", json={
        "quote_token": token,
        "sender_role": "homeowner",
        "sender_id": paid_project_3ms.get("homeowner_auth_id", "ho-test"),
        "body": "When will the materials arrive?",
    })
    assert resp.status_code == 200

    await _sb_delete("job_messages", {"scope_token": token})


@pytest.mark.asyncio
async def test_message_history_ordered(sandbox_client, paid_project_3ms):
    """Messages come back in chronological order."""
    token = paid_project_3ms["token"]

    for i, msg in enumerate(["First message", "Second message", "Third message"]):
        await sandbox_client.post("/v1/messages/send", json={
            "quote_token": token,
            "sender_role": "contractor" if i % 2 == 0 else "homeowner",
            "sender_id": f"test-{i}",
            "body": msg,
        })

    resp = await sandbox_client.get(f"/v1/messages/{token}")
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) >= 3

    bodies = [m["body"] for m in messages]
    first_idx = bodies.index("First message")
    second_idx = bodies.index("Second message")
    third_idx = bodies.index("Third message")
    assert first_idx < second_idx < third_idx

    await _sb_delete("job_messages", {"scope_token": token})


@pytest.mark.asyncio
async def test_message_on_unpaid_blocked(sandbox_client, unpaid_project):
    """Cannot send messages on unpaid projects."""
    token = unpaid_project["token"]

    resp = await sandbox_client.post("/v1/messages/send", json={
        "quote_token": token,
        "sender_role": "contractor",
        "sender_id": "test-id",
        "body": "This should fail",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_message_empty_body_rejected(sandbox_client, paid_project_3ms):
    """Empty message body is rejected."""
    token = paid_project_3ms["token"]

    resp = await sandbox_client.post("/v1/messages/send", json={
        "quote_token": token,
        "sender_role": "contractor",
        "sender_id": "test-id",
        "body": "   ",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_message_invalid_role_rejected(sandbox_client, paid_project_3ms):
    """Invalid sender_role is rejected."""
    token = paid_project_3ms["token"]

    resp = await sandbox_client.post("/v1/messages/send", json={
        "quote_token": token,
        "sender_role": "admin",
        "sender_id": "test-id",
        "body": "Should fail",
    })
    assert resp.status_code == 400
