"""
backend/tests/conftest.py
==========================

Shared pytest fixtures for Leo backend integration tests.

All tests run against the live backend (http://localhost:8000) with sandbox
mode active (X-Sandbox: true). No mocks — this tests real Supabase, real
Stripe test keys, real route handlers.

Cleanup: each fixture cleans up the sandbox rows it creates so tests are
idempotent and don't pollute the DB.

Usage in tests:
    async def test_something(sandbox_client, test_contractor_token):
        resp = await sandbox_client.get("/v1/quotes")
        assert resp.status_code == 200
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid

import httpx
import pytest
import pytest_asyncio

# Make backend modules importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings

logger = logging.getLogger(__name__)

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
SANDBOX_HEADERS = {
    "X-Sandbox": "true",
    "Content-Type": "application/json",
}

# Supabase auth constants
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
SUPABASE_ANON_KEY = getattr(settings, "SUPABASE_ANON_KEY", "") or os.getenv("SUPABASE_ANON_KEY", "")
TEST_PASSWORD = "test-pw-e2e-2026!"


# ---------------------------------------------------------------------------
# Supabase Auth helpers — create users + get JWTs for real auth in tests
# ---------------------------------------------------------------------------

async def _ensure_auth_user(email: str, password: str = TEST_PASSWORD) -> str:
    """Create or find a Supabase auth user. Returns user ID."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=15) as c:
        resp = await c.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers=headers,
            json={"email": email, "password": password, "email_confirm": True},
        )
        if resp.status_code in (200, 201):
            return resp.json()["id"]

        # User exists — find by listing
        page = 1
        while page <= 10:
            list_resp = await c.get(
                f"{SUPABASE_URL}/auth/v1/admin/users?page={page}&per_page=50",
                headers=headers,
            )
            if list_resp.status_code != 200:
                break
            data = list_resp.json()
            users = data.get("users", data) if isinstance(data, dict) else data
            if not users:
                break
            for u in users:
                if u.get("email") == email:
                    # Reset password so we can sign in
                    await c.put(
                        f"{SUPABASE_URL}/auth/v1/admin/users/{u['id']}",
                        headers=headers,
                        json={"password": password},
                    )
                    return u["id"]
            page += 1

    raise RuntimeError(f"Failed to create or find auth user: {email}")


async def _get_jwt(email: str, password: str = TEST_PASSWORD) -> str:
    """Sign in via Supabase GoTrue and return an access_token (JWT)."""
    anon = SUPABASE_ANON_KEY
    if not anon:
        anon = SUPABASE_KEY
    async with httpx.AsyncClient(timeout=15) as c:
        resp = await c.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": anon, "Content-Type": "application/json"},
            json={"email": email, "password": password},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"GoTrue sign-in failed for {email}: {resp.status_code} {resp.text[:200]}")
        return resp.json()["access_token"]


async def _link_auth_user_to_contractor(auth_user_id: str, contractor_id: str) -> None:
    """Set auth_user_id + claimed on a contractor row so JWT resolves as contractor role."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10) as c:
        await c.patch(
            f"{SUPABASE_URL}/rest/v1/contractors",
            params={"id": f"eq.{contractor_id}"},
            headers=headers,
            json={"auth_user_id": auth_user_id, "claimed": True},
        )


# ---------------------------------------------------------------------------
# JWT fixtures — real Supabase auth for tests that hit JWT-protected endpoints
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def contractor_jwt(contractor_with_stripe) -> dict:
    """Create a Supabase auth user linked to the test contractor. Returns dict with jwt + user info.

    The contractor_with_stripe fixture creates the contractor row;
    this fixture creates the auth user, links them, and returns a JWT.
    """
    email = f"test-contractor-{contractor_with_stripe['id'][:8]}@sandbox.leo.casa"
    user_id = await _ensure_auth_user(email)
    await _link_auth_user_to_contractor(user_id, contractor_with_stripe["id"])
    jwt = await _get_jwt(email)
    return {
        "token": jwt,
        "user_id": user_id,
        "email": email,
        "contractor_id": contractor_with_stripe["id"],
        "header": {"Authorization": f"Bearer {jwt}"},
    }


@pytest_asyncio.fixture
async def homeowner_jwt(paid_project_3ms) -> dict:
    """Create a Supabase auth user for the homeowner of paid_project_3ms.

    Sets homeowner_auth_id on the quote so JWT identity checks pass.
    """
    email = paid_project_3ms["homeowner_email"]
    user_id = await _ensure_auth_user(email)

    # Patch the quote so homeowner_auth_id matches the real auth user
    await _sb_patch("quotes", {"token": paid_project_3ms["token"]}, {"homeowner_auth_id": user_id})

    jwt = await _get_jwt(email)
    return {
        "token": jwt,
        "user_id": user_id,
        "email": email,
        "header": {"Authorization": f"Bearer {jwt}"},
    }


@pytest_asyncio.fixture
async def wrong_contractor_jwt() -> dict:
    """JWT for a contractor NOT assigned to any test project."""
    email = f"wrong-contractor-{uuid.uuid4().hex[:8]}@sandbox.leo.casa"
    user_id = await _ensure_auth_user(email)

    # Create a separate contractor row linked to this user
    wrong_id = str(uuid.uuid4())
    await _sb_insert("contractors", {
        "id": wrong_id,
        "name": "Wrong Contractor",
        "phone": f"346{uuid.uuid4().hex[:8]}",
        "canvas_token": f"wrong-{uuid.uuid4().hex[:8]}",
        "claimed": True,
        "provenance": "test",
        "auth_user_id": user_id,
        "dossier": {"trade": "electrician", "city": "Barcelona"},
    })

    jwt = await _get_jwt(email)
    yield {
        "token": jwt,
        "user_id": user_id,
        "email": email,
        "contractor_id": wrong_id,
        "header": {"Authorization": f"Bearer {jwt}"},
    }

    await _sb_delete("contractors", {"id": wrong_id})


@pytest_asyncio.fixture
async def wrong_homeowner_jwt() -> dict:
    """JWT for a homeowner NOT associated with any test project."""
    email = f"wrong-homeowner-{uuid.uuid4().hex[:8]}@sandbox.leo.casa"
    user_id = await _ensure_auth_user(email)
    jwt = await _get_jwt(email)
    return {
        "token": jwt,
        "user_id": user_id,
        "email": email,
        "header": {"Authorization": f"Bearer {jwt}"},
    }


# ---------------------------------------------------------------------------
# Sandbox HTTP client — function scoped for event loop compatibility
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def sandbox_client():
    """httpx.AsyncClient with X-Sandbox: true, pointed at localhost.

    Function-scoped so each test gets a fresh client (avoids event loop issues
    with pytest-asyncio's auto mode).
    """
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers=SANDBOX_HEADERS,
        timeout=30,
    ) as client:
        # Quick health check on first use — skip suite if backend is down
        try:
            resp = await client.get("/health")
            if resp.status_code != 200:
                pytest.skip(f"Backend not healthy ({resp.status_code}): {resp.text}")
        except Exception as e:
            pytest.skip(f"Backend not available at {BASE_URL}: {e}")
        yield client


# ---------------------------------------------------------------------------
# Supabase cleanup helper
# ---------------------------------------------------------------------------

async def _sb_delete(table: str, filters: dict) -> None:
    """Delete rows from Supabase matching filters. Used for test cleanup."""
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    params = {k: f"eq.{v}" for k, v in filters.items()}
    async with httpx.AsyncClient(timeout=10) as c:
        resp = await c.delete(f"{url}/rest/v1/{table}", headers=headers, params=params)
        if resp.status_code not in (200, 204):
            logger.warning("Cleanup %s %s: %s %s", table, filters, resp.status_code, resp.text[:100])


async def _sb_get(table: str, filters: dict, select: str = "*") -> list:
    """Fetch rows from Supabase matching filters."""
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    params = {k: f"eq.{v}" for k, v in filters.items()}
    params["select"] = select
    async with httpx.AsyncClient(timeout=10) as c:
        resp = await c.get(f"{url}/rest/v1/{table}", headers=headers, params=params)
        if resp.status_code == 200:
            return resp.json()
    return []


# ---------------------------------------------------------------------------
# Test contractor: create a sandbox contractor row directly in Supabase.
# We bypass the claim flow (which needs Google OAuth) and insert a row with
# a known canvas_token that tests can use.
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_contractor_id() -> str:
    """Create a sandbox contractor and return its ID. Cleanup after each test."""
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    contractor_id = str(uuid.uuid4())
    canvas_token = f"test-{uuid.uuid4().hex[:16]}"

    # Use a unique phone per test run to avoid unique constraint conflicts
    unique_phone = f"346{uuid.uuid4().hex[:8]}"
    payload = {
        "id": contractor_id,
        "name": "Test Contractor (sandbox)",
        "phone": unique_phone,
        "canvas_token": canvas_token,
        "claimed": False,
        "provenance": "test",
        "dossier": {"trade": "plumber", "city": "Madrid"},
    }

    async with httpx.AsyncClient(timeout=10) as c:
        resp = await c.post(
            f"{url}/rest/v1/contractors",
            headers=headers,
            json=payload,
        )
        assert resp.status_code in (200, 201), f"Failed to create test contractor: {resp.text}"

    logger.info("Test contractor created: %s (canvas_token=%s)", contractor_id[:8], canvas_token)

    yield contractor_id

    # Cleanup: delete the contractor and any quotes created by tests
    await _sb_delete("quotes", {"contractor_id": contractor_id})
    await _sb_delete("contractors", {"id": contractor_id})
    logger.info("Test contractor cleaned up: %s", contractor_id[:8])


@pytest_asyncio.fixture
async def test_contractor_canvas_token(test_contractor_id: str) -> str:
    """Return the canvas_token of the test contractor."""
    rows = await _sb_get("contractors", {"id": test_contractor_id}, "canvas_token")
    assert rows, "Test contractor not found"
    return rows[0]["canvas_token"]


# ---------------------------------------------------------------------------
# Helpers for tests to create sandbox quotes
# ---------------------------------------------------------------------------

async def _sb_patch(table: str, filters: dict, data: dict) -> None:
    """Patch rows in Supabase matching filters."""
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    params = {k: f"eq.{v}" for k, v in filters.items()}
    async with httpx.AsyncClient(timeout=10) as c:
        resp = await c.patch(f"{url}/rest/v1/{table}", headers=headers, params=params, json=data)
        if resp.status_code not in (200, 204):
            logger.warning("Patch %s %s: %s %s", table, filters, resp.status_code, resp.text[:100])


async def _sb_insert(table: str, payload: dict) -> dict:
    """Insert a row into Supabase and return the created row."""
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    async with httpx.AsyncClient(timeout=10) as c:
        resp = await c.post(f"{url}/rest/v1/{table}", headers=headers, json=payload)
        assert resp.status_code in (200, 201), f"Insert into {table} failed: {resp.text}"
        return resp.json()[0] if isinstance(resp.json(), list) else resp.json()


async def create_sandbox_quote(
    sandbox_client: httpx.AsyncClient,
    contractor_id: str,
    quote_data: dict | None = None,
) -> dict:
    """Directly insert a sandbox quote via Supabase and return its token.

    Used by tests that need a pre-existing quote to test payment/milestone flows.
    """
    token = uuid.uuid4().hex
    payload = {
        "token": token,
        "contractor_id": contractor_id,
        "is_sandbox": True,
        "status": "finalized",
        "payment_status": "unpaid",
        "amount_total_cents": 150000,
        "homeowner_email": "test-homeowner@sandbox.leo.casa",
        "homeowner_phone": "34600000002",
        "quote_data": quote_data or {
            "title": "Test Kitchen Renovation",
            "description": "Sandbox test quote",
            "line_items": [
                {"description": "Labour", "amount_cents": 100000},
                {"description": "Materials", "amount_cents": 50000},
            ],
            "total_cents": 150000,
        },
        "milestones": [
            {"id": "m1", "title": "Start", "amount_cents": 75000, "status": "pending"},
            {"id": "m2", "title": "Completion", "amount_cents": 75000, "status": "pending"},
        ],
    }
    return await _sb_insert("quotes", payload)


# ---------------------------------------------------------------------------
# Stripe-enabled contractor: contractor + pre-onboarded Stripe Express account
# ---------------------------------------------------------------------------

# Pre-onboarded Stripe Express test account with transfers: active.
# Created once, TOS accepted via Stripe hosted flow, reused across all tests.
# DO NOT delete this account — it's permanent test infrastructure.
STRIPE_TEST_ACCOUNT_ID = "acct_1TMCwBFRMxx8LzH0"


@pytest_asyncio.fixture
async def contractor_with_stripe(sandbox_client) -> dict:
    """Create a sandbox contractor linked to a pre-onboarded Stripe Express account.

    Uses a shared Stripe account with transfers capability active (TOS accepted,
    bank account added). Each test gets a unique contractor row in Supabase that
    references this shared account.

    Returns dict with: id, stripe_account_id, canvas_token, phone
    Cleans up Supabase rows on teardown (NOT the Stripe account — it's shared).
    """
    contractor_id = str(uuid.uuid4())
    canvas_token = f"test-{uuid.uuid4().hex[:16]}"
    unique_phone = f"346{uuid.uuid4().hex[:8]}"

    await _sb_insert("contractors", {
        "id": contractor_id,
        "name": "Test Stripe Contractor",
        "phone": unique_phone,
        "canvas_token": canvas_token,
        "claimed": False,
        "provenance": "test",
        "stripe_account_id": STRIPE_TEST_ACCOUNT_ID,
        "stripe_onboarding_complete": True,
        "dossier": {"trade": "plumber", "city": "Madrid"},
    })

    logger.info("Test contractor with pre-onboarded Stripe: %s -> %s",
                contractor_id[:8], STRIPE_TEST_ACCOUNT_ID[:16])

    yield {
        "id": contractor_id,
        "stripe_account_id": STRIPE_TEST_ACCOUNT_ID,
        "canvas_token": canvas_token,
        "phone": unique_phone,
    }

    await _sb_delete("quotes", {"contractor_id": contractor_id})
    await _sb_delete("contractors", {"id": contractor_id})


# ---------------------------------------------------------------------------
# Paid project fixtures: quote + simulated payment at different milestone counts
# ---------------------------------------------------------------------------

async def _create_paid_project(
    sandbox_client: httpx.AsyncClient,
    contractor: dict,
    num_milestones: int = 2,
    total_cents: int = 100000,
) -> dict:
    """Create a quote, attempt checkout, simulate payment. Returns full project context.

    The quote is marked paid via direct Supabase patch (simulating webhook),
    because we can't complete Stripe Checkout in pytest.
    """
    token = uuid.uuid4().hex
    per_milestone = total_cents // num_milestones
    milestones = [
        {
            "id": f"m{i+1}",
            "title": f"Phase {i+1}",
            "amount_cents": per_milestone,
            "status": "pending",
        }
        for i in range(num_milestones)
    ]

    homeowner_email = f"ho-{token[:8]}@sandbox.leo.casa"
    homeowner_auth_id = f"ho-auth-{token[:8]}"

    await _sb_insert("quotes", {
        "token": token,
        "contractor_id": contractor["id"],
        "is_sandbox": True,
        "status": "finalized",
        "payment_status": "unpaid",
        "amount_total_cents": total_cents,
        "homeowner_email": homeowner_email,
        "homeowner_phone": "34600000099",
        "homeowner_auth_id": homeowner_auth_id,
        "quote_data": {
            "title": f"Test Project ({num_milestones} milestones)",
            "description": "Automated test project",
            "line_items": [{"description": "Work", "amount_cents": total_cents}],
            "total_cents": total_cents,
        },
        "milestones": milestones,
    })

    # Try to create a real Checkout session (validates payment route works)
    checkout_resp = await sandbox_client.post("/v1/payment/create-checkout", json={
        "quote_token": token,
        "homeowner_email": homeowner_email,
    })
    checkout_ok = checkout_resp.status_code == 200

    # Simulate webhook: mark quote as paid with a fake payment_intent_id
    fake_pi = f"pi_test_{uuid.uuid4().hex[:16]}"
    await _sb_patch("quotes", {"token": token}, {
        "payment_status": "paid",
        "payment_intent_id": fake_pi,
        "status": "paid",
    })

    return {
        "token": token,
        "contractor_id": contractor["id"],
        "contractor_phone": contractor.get("phone", ""),
        "stripe_account_id": contractor.get("stripe_account_id"),
        "milestones": milestones,
        "homeowner_email": homeowner_email,
        "homeowner_auth_id": homeowner_auth_id,
        "payment_intent_id": fake_pi,
        "checkout_created": checkout_ok,
        "num_milestones": num_milestones,
    }


async def _cleanup_project(token: str) -> None:
    """Remove all Supabase rows for a project.

    IMPORTANT: Side-effect tables (milestone_updates, notifications, reviews,
    variation_orders, cancellations, consents) use scope_token (legacy column name),
    NOT quote_token. job_messages and disputes also use scope_token/quote_token.
    The primary quotes table uses `token`.
    """
    for table, col in [
        ("milestone_updates", "scope_token"),
        ("job_messages", "scope_token"),
        ("notifications", "scope_token"),
        ("reviews", "scope_token"),
        ("variation_orders", "scope_token"),
        ("disputes", "quote_token"),
        ("cancellations", "scope_token"),
        ("consents", "scope_token"),
        ("quotes", "token"),
    ]:
        await _sb_delete(table, {col: token})


@pytest_asyncio.fixture
async def paid_project_2ms(sandbox_client, contractor_with_stripe) -> dict:
    """Paid project with 2 milestones (€500 each). Cleans up after test."""
    project = await _create_paid_project(sandbox_client, contractor_with_stripe, num_milestones=2, total_cents=100000)
    yield project
    await _cleanup_project(project["token"])


@pytest_asyncio.fixture
async def paid_project_3ms(sandbox_client, contractor_with_stripe) -> dict:
    """Paid project with 3 milestones. Cleans up after test."""
    project = await _create_paid_project(sandbox_client, contractor_with_stripe, num_milestones=3, total_cents=150000)
    yield project
    await _cleanup_project(project["token"])


@pytest_asyncio.fixture
async def paid_project_5ms(sandbox_client, contractor_with_stripe) -> dict:
    """Paid project with 5 milestones. Cleans up after test."""
    project = await _create_paid_project(sandbox_client, contractor_with_stripe, num_milestones=5, total_cents=250000)
    yield project
    await _cleanup_project(project["token"])


@pytest_asyncio.fixture
async def unpaid_project(sandbox_client, contractor_with_stripe) -> dict:
    """Finalized quote that has NOT been paid. For guard tests."""
    import uuid as _uuid
    token = _uuid.uuid4().hex
    await _sb_insert("quotes", {
        "token": token,
        "contractor_id": contractor_with_stripe["id"],
        "is_sandbox": True,
        "status": "finalized",
        "payment_status": "unpaid",
        "amount_total_cents": 100000,
        "homeowner_email": f"ho-{token[:8]}@sandbox.leo.casa",
        "homeowner_phone": "34600000099",
        "homeowner_auth_id": f"ho-auth-{token[:8]}",
        "quote_data": {
            "title": "Unpaid Test Project",
            "description": "Guard test — not paid",
            "line_items": [{"description": "Work", "amount_cents": 100000}],
            "total_cents": 100000,
        },
        "milestones": [
            {"id": "m1", "title": "Materials", "amount_cents": 50000, "status": "pending"},
            {"id": "m2", "title": "Work", "amount_cents": 50000, "status": "pending"},
        ],
    })
    yield {
        "token": token,
        "contractor_id": contractor_with_stripe["id"],
        "stripe_account_id": contractor_with_stripe.get("stripe_account_id"),
        "homeowner_auth_id": f"ho-auth-{token[:8]}",
        "milestones": [
            {"id": "m1", "title": "Materials", "amount_cents": 50000, "status": "pending"},
            {"id": "m2", "title": "Work", "amount_cents": 50000, "status": "pending"},
        ],
    }
    await _cleanup_project(token)


@pytest_asyncio.fixture
async def completed_project(sandbox_client, contractor_with_stripe) -> dict:
    """Fully completed project — both milestones released. For review and post-completion tests.

    Uses direct Supabase patching to simulate completion (bypasses the multi-step
    proof→release flow). The paid_project fixtures test the real transfer path.
    """
    project = await _create_paid_project(sandbox_client, contractor_with_stripe, num_milestones=2, total_cents=100000)
    token = project["token"]

    # Simulate both milestones released + quote complete
    milestones = [
        {"id": "m1", "title": "Materials", "amount_cents": 50000, "status": "released"},
        {"id": "m2", "title": "Work", "amount_cents": 50000, "status": "released"},
    ]
    import datetime
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    await _sb_patch("quotes", {"token": token}, {
        "milestones": milestones,
        "status": "complete",
        "completed_at": now_iso,
    })

    # Insert milestone_updates rows (needed for invoice document)
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    sb_hdrs = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    async with httpx.AsyncClient(timeout=10) as c:
        for i, m in enumerate(milestones):
            await c.post(f"{settings.SUPABASE_URL}/rest/v1/milestone_updates", headers=sb_hdrs, json={
                "scope_token": token,
                "milestone_index": i,
                "status": "released",
                "released_at": now_iso,
                "stripe_transfer_id": f"tr_test_{i}_{token[:8]}",
                "photos": [],
                "note": "Test proof",
            })

    yield {**project, "milestones": milestones, "status": "complete"}
    await _cleanup_project(token)
