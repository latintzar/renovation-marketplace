/**
 * E2E test setup — creates a fresh project for each test.
 *
 * Every test gets its own contractor, homeowner, quote, and (optionally)
 * simulated payment. No shared state between tests. Cleanup on teardown.
 */

import type { Page, Browser, BrowserContext } from "@playwright/test";
import {
  ensureTestUser,
  authenticateInBrowser,
  linkUserToContractor,
} from "./auth";
import {
  SUPABASE_URL,
  SUPABASE_KEY,
  APP_URL,
  STRIPE_TEST_CONTRACTOR_ACCOUNT,
  sbGet,
  sbInsert,
  sbDelete,
} from "./fixtures";

const API_BASE =
  process.env.TEST_API_URL || "http://localhost:8000";
const TEST_PASSWORD = "test-pw-e2e-2026!";
const SUPABASE_ANON_KEY =
  "local-test-anon-key";

function sbHeaders() {
  return {
    apikey: SUPABASE_KEY,
    Authorization: `Bearer ${SUPABASE_KEY}`,
    "Content-Type": "application/json",
    Prefer: "return=representation",
  };
}

async function sbPatch(
  table: string,
  match: Record<string, string>,
  data: Record<string, unknown>
): Promise<void> {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(match)) params.set(k, `eq.${v}`);
  const resp = await fetch(`${SUPABASE_URL}/rest/v1/${table}?${params}`, {
    method: "PATCH",
    headers: sbHeaders(),
    body: JSON.stringify(data),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`sbPatch(${table}) failed ${resp.status}: ${text}`);
  }
}

export interface FreshProject {
  token: string;
  contractorId: string;
  contractorEmail: string;
  contractorAuthId: string;
  homeownerEmail: string;
  homeownerAuthId: string;
  milestoneCount: number;
  canvasUrl: string;
}

/**
 * Get a JWT for a test user via GoTrue password grant.
 * Retries with backoff on 429 (rate limit).
 */
export async function getJwt(email: string): Promise<string> {
  for (let attempt = 0; attempt < 5; attempt++) {
    const resp = await fetch(
      `${SUPABASE_URL}/auth/v1/token?grant_type=password`,
      {
        method: "POST",
        headers: { apikey: SUPABASE_ANON_KEY, "Content-Type": "application/json" },
        body: JSON.stringify({ email, password: TEST_PASSWORD }),
      }
    );
    if (resp.ok) return (await resp.json()).access_token;
    if (resp.status === 429) {
      const wait = 2000 * (attempt + 1);
      await new Promise((r) => setTimeout(r, wait));
      continue;
    }
    throw new Error(`JWT failed for ${email}: ${resp.status}`);
  }
  throw new Error(`JWT rate-limited after 5 retries for ${email}`);
}

/**
 * Create a completely fresh project — contractor, auth users, quote, optional payment.
 */
export async function createFreshProject(opts?: {
  milestoneCount?: number;
  paid?: boolean;
}): Promise<FreshProject> {
  const milestoneCount = opts?.milestoneCount ?? 3;
  const paid = opts?.paid ?? false;
  const tag = crypto.randomUUID().replace(/-/g, "").slice(0, 8);

  const contractorEmail = `e2e-c-${tag}@sandbox.leo.casa`;
  const homeownerEmail = `e2e-ho-${tag}@sandbox.leo.casa`;

  const contractorUser = await ensureTestUser(contractorEmail, TEST_PASSWORD);
  const homeownerUser = await ensureTestUser(homeownerEmail, TEST_PASSWORD);

  const contractorId = `e2e-${tag}`;
  await sbInsert("contractors", {
    id: contractorId,
    name: "Fontanería E2E",
    phone: `+346${tag}`,
    canvas_token: `e2e-canvas-${tag}`,
    claimed: true,
    provenance: "playwright_e2e",
    stripe_account_id: STRIPE_TEST_CONTRACTOR_ACCOUNT,
    stripe_onboarding_complete: true,
    auth_user_id: contractorUser.id,
    dossier: { trade: "fontanero", city: "Madrid" },
  });

  const names = [
    "Demolición",
    "Fontanería",
    "Alicatado",
    "Electricidad",
    "Pintura",
  ];
  const lineItems = [];
  for (let i = 0; i < milestoneCount; i++) {
    lineItems.push({
      description: names[i % names.length],
      amount: 500,
      duration_label: `${i + 1} días`,
    });
  }

  const finalizeResp = await fetch(`${API_BASE}/v1/quote/finalize`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Sandbox": "true" },
    body: JSON.stringify({
      contractor_id: contractorId,
      quote_data: {
        title: `Reforma E2E — ${milestoneCount} fases`,
        description:
          "Reforma integral de baño para test automatizado Playwright",
        line_items: lineItems,
        service_fee_percent: 5,
        iva_rate: 10,
        homeowner_name: "Propietario Test",
        contractor_name: "Fontanería E2E",
      },
      auth_user_id: contractorUser.id,
    }),
  });
  if (!finalizeResp.ok) {
    throw new Error(
      `Finalize failed: ${finalizeResp.status} ${await finalizeResp.text()}`
    );
  }
  const { token, canvas_url } = (await finalizeResp.json()) as {
    token: string;
    canvas_url: string;
  };

  await sbPatch("quotes", { token }, {
    homeowner_email: homeownerEmail,
    homeowner_auth_id: homeownerUser.id,
  });

  if (paid) {
    await sbPatch("quotes", { token }, {
      payment_status: "paid",
      payment_intent_id: `pi_test_e2e_${tag}`,
      status: "paid",
    });
  }

  return {
    token,
    contractorId,
    contractorEmail,
    contractorAuthId: contractorUser.id,
    homeownerEmail,
    homeownerAuthId: homeownerUser.id,
    milestoneCount,
    canvasUrl: canvas_url || `http://46.224.144.27/app/canvas/${token}`,
  };
}

export async function submitProofViaAPI(
  project: FreshProject,
  milestoneIndex: number
): Promise<void> {
  const jwt = await getJwt(project.contractorEmail);
  const resp = await fetch(
    `${API_BASE}/v1/projects/${project.token}/milestones/${milestoneIndex}/proof`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwt}`,
        "X-Sandbox": "true",
      },
      body: JSON.stringify({
        photos: [`https://example.com/proof_${milestoneIndex}.jpg`],
        note: `Phase ${milestoneIndex + 1} complete`,
      }),
    }
  );
  if (!resp.ok)
    throw new Error(
      `Proof failed [${milestoneIndex}]: ${resp.status} ${await resp.text()}`
    );
}

export async function releaseMilestoneViaAPI(
  project: FreshProject,
  milestoneIndex: number
): Promise<void> {
  const jwt = await getJwt(project.homeownerEmail);
  const resp = await fetch(
    `${API_BASE}/v1/projects/${project.token}/milestones/${milestoneIndex}/release`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${jwt}`,
        "X-Sandbox": "true",
      },
    }
  );
  if (!resp.ok)
    throw new Error(
      `Release failed [${milestoneIndex}]: ${resp.status} ${await resp.text()}`
    );
}

export async function createVariationViaAPI(
  project: FreshProject,
  title: string,
  amountCents: number
): Promise<string> {
  const jwt = await getJwt(project.contractorEmail);
  const resp = await fetch(
    `${API_BASE}/v1/projects/${project.token}/variations`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwt}`,
        "X-Sandbox": "true",
      },
      body: JSON.stringify({
        title,
        description: "E2E test variation",
        amount_cents: amountCents,
        reason: "Unforeseen work",
      }),
    }
  );
  if (!resp.ok)
    throw new Error(
      `Variation create failed: ${resp.status} ${await resp.text()}`
    );
  const variations = await sbGet("variation_orders", {
    scope_token: `eq.${project.token}`,
    select: "id",
    order: "created_at.desc",
    limit: "1",
  });
  return variations[0]?.id as string;
}

export async function openDisputeViaAPI(
  project: FreshProject,
  milestoneIndex: number
): Promise<void> {
  const resp = await fetch(`${API_BASE}/v1/dispute/open`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Sandbox": "true" },
    body: JSON.stringify({
      quote_token: project.token,
      milestone_index: milestoneIndex,
      homeowner_name: "Propietario Test",
      homeowner_phone: "34600000099",
      reason: "Quality not acceptable",
    }),
  });
  if (!resp.ok)
    throw new Error(
      `Dispute failed: ${resp.status} ${await resp.text()}`
    );
}

export async function sendMessageViaAPI(
  project: FreshProject,
  senderRole: "contractor" | "homeowner",
  body: string
): Promise<void> {
  const senderId =
    senderRole === "contractor"
      ? project.contractorId
      : project.homeownerAuthId;
  const resp = await fetch(`${API_BASE}/v1/messages/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Sandbox": "true" },
    body: JSON.stringify({
      quote_token: project.token,
      sender_role: senderRole,
      sender_id: senderId,
      body,
    }),
  });
  if (!resp.ok)
    throw new Error(
      `Message failed: ${resp.status} ${await resp.text()}`
    );
}

export async function cleanupProject(p: FreshProject): Promise<void> {
  const token = p.token;
  try {
    await Promise.all([
      sbDelete("milestone_updates", { scope_token: token }),
      sbDelete("variation_orders", { scope_token: token }),
      sbDelete("job_messages", { scope_token: token }),
      sbDelete("reviews", { scope_token: token }),
      sbDelete("notifications", { scope_token: token }),
      sbDelete("disputes", { quote_token: token }),
      sbDelete("consents", { scope_token: token }),
      sbDelete("cancellations", { scope_token: token }),
    ]);
    await sbDelete("quotes", { token });
    await sbDelete("contractors", { id: p.contractorId });
  } catch {
    // Best-effort cleanup — don't fail tests on cleanup errors
  }
}

/**
 * Dismiss cookie consent dialog if visible. Call after page load.
 */
export async function dismissCookieConsent(page: import("@playwright/test").Page): Promise<void> {
  const accept = page.getByRole("button", { name: /Accept|Aceptar/i });
  if (await accept.isVisible({ timeout: 2000 }).catch(() => false)) {
    await accept.click();
    await page.waitForTimeout(300);
  }
}

export { authenticateInBrowser, ensureTestUser, APP_URL, API_BASE as API_URL, sbGet, sbPatch };
