/**
 * Playwright auth helper — creates real Supabase sessions for E2E tests.
 *
 * Uses the service role key to:
 * 1. Create (or reuse) a test user via Supabase Auth Admin API
 * 2. Generate a magic link that auto-signs-in when visited
 * 3. Navigate the browser to that link, giving it a real session
 *
 * This means authenticated tests use REAL auth — no mocks, no localStorage hacks.
 */

import type { Page } from "@playwright/test";

const SUPABASE_URL =
  process.env.SUPABASE_URL || "http://127.0.0.1:54321";
const SUPABASE_REF = SUPABASE_URL.replace("https://", "").split(".")[0];
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || "";
const SUPABASE_ANON_KEY =
  "local-test-anon-key";
const APP_URL = process.env.TEST_APP_URL || "http://46.224.144.27/app";

interface TestUser {
  id: string;
  email: string;
}

/**
 * Create a test user via Supabase Admin API (idempotent — reuses if exists).
 */
export async function ensureTestUser(
  email: string,
  password = "test-pw-e2e-2026!"
): Promise<TestUser> {
  if (!SUPABASE_SERVICE_KEY)
    throw new Error("SUPABASE_SERVICE_ROLE_KEY not set — cannot create test user");

  // Try to find existing user by email
  const listResp = await fetch(
    `${SUPABASE_URL}/auth/v1/admin/users?page=1&per_page=1`,
    {
      headers: {
        apikey: SUPABASE_SERVICE_KEY,
        Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
      },
    }
  );

  // Search by creating — if user exists, Supabase returns 422
  const createResp = await fetch(`${SUPABASE_URL}/auth/v1/admin/users`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_SERVICE_KEY,
      Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email,
      password,
      email_confirm: true,
    }),
  });

  if (createResp.ok) {
    const data = await createResp.json();
    return { id: data.id, email };
  }

  // User likely exists — fetch by email
  const existing = await getUserByEmail(email);
  if (existing) {
    // Update password to ensure we can sign in
    await fetch(`${SUPABASE_URL}/auth/v1/admin/users/${existing.id}`, {
      method: "PUT",
      headers: {
        apikey: SUPABASE_SERVICE_KEY,
        Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ password }),
    });
    return existing;
  }

  throw new Error(`Failed to create or find test user: ${email}`);
}

async function getUserByEmail(email: string): Promise<TestUser | null> {
  let page = 1;
  while (page <= 10) {
    const resp = await fetch(
      `${SUPABASE_URL}/auth/v1/admin/users?page=${page}&per_page=50`,
      {
        headers: {
          apikey: SUPABASE_SERVICE_KEY,
          Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
        },
      }
    );
    if (!resp.ok) return null;
    const data = await resp.json();
    const users = data.users || data;
    if (!Array.isArray(users) || users.length === 0) return null;
    const match = users.find((u: any) => u.email === email);
    if (match) return { id: match.id, email: match.email };
    page++;
  }
  return null;
}

/**
 * Sign in via Supabase GoTrue REST API (from Node), then inject the
 * session into the browser's localStorage so the Supabase JS client
 * picks it up on page load. Real auth, no mocks.
 */
export async function authenticateInBrowser(
  page: Page,
  email: string,
  password = "test-pw-e2e-2026!"
): Promise<void> {
  // 1. Sign in via GoTrue REST API from Node
  const resp = await fetch(
    `${SUPABASE_URL}/auth/v1/token?grant_type=password`,
    {
      method: "POST",
      headers: {
        apikey: SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    }
  );

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`GoTrue sign-in failed for ${email}: ${resp.status} ${err}`);
  }

  const session = await resp.json();

  // 2. Navigate to app origin so we can write to its localStorage
  await page.goto(`${APP_URL}/`);
  await page.waitForLoadState("domcontentloaded");

  // 3. Inject session into localStorage (Supabase JS reads from sb-{ref}-auth-token)
  const storageKey = `sb-${SUPABASE_REF}-auth-token`;
  const storageValue = JSON.stringify({
    access_token: session.access_token,
    refresh_token: session.refresh_token,
    expires_in: session.expires_in,
    expires_at: Math.floor(Date.now() / 1000) + session.expires_in,
    token_type: "bearer",
    user: session.user,
  });

  await page.evaluate(
    ({ key, value }) => {
      localStorage.setItem(key, value);
      localStorage.setItem("leo_language", "en");
      localStorage.setItem("leo_sandbox_mode", "true");
    },
    { key: storageKey, value: storageValue }
  );

  // 4. Reload so AuthContext hydrates from the stored session
  await page.reload();
  await page.waitForLoadState("networkidle");
}

/**
 * Full auth setup: ensure user exists, then authenticate in the browser.
 * Returns the user ID for use in test assertions.
 */
export async function setupAuthenticatedSession(
  page: Page,
  email = "e2e-test@sandbox.leo.casa"
): Promise<TestUser> {
  const user = await ensureTestUser(email);
  await authenticateInBrowser(page, email);
  return user;
}

/**
 * Link a test user to a contractor row so they authenticate as "contractor" role.
 * The AuthContext resolves role by checking if the user's auth ID matches a contractor row.
 */
export async function linkUserToContractor(
  userId: string,
  contractorId: string
): Promise<void> {
  await fetch(
    `${SUPABASE_URL}/rest/v1/contractors?id=eq.${contractorId}`,
    {
      method: "PATCH",
      headers: {
        apikey: SUPABASE_SERVICE_KEY,
        Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
        "Content-Type": "application/json",
        Prefer: "return=minimal",
      },
      body: JSON.stringify({ auth_user_id: userId }),
    }
  );
}
