/**
 * E2E Test Fixtures — Real app flows for lifecycle tests.
 *
 * Philosophy: tests drive the REAL app in sandbox mode. The only things set up
 * outside the UI are auth users and a contractor row (because OnboardPro is an
 * AI chat we can't automate deterministically). Everything else — quote creation,
 * payment, proof submission, releases — goes through the actual app or its real
 * API endpoints (the same ones the UI calls).
 *
 * Usage:
 *   const project = await bootstrapProject(contractorPage, homeownerPage);
 *   // now drive the UI in both browser contexts
 */

import type { Page } from "@playwright/test";
import { ensureTestUser, authenticateInBrowser, linkUserToContractor } from "./auth";

export const SUPABASE_URL =
  process.env.SUPABASE_URL || "http://127.0.0.1:54321";
export const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || "";
export const APP_URL = process.env.TEST_APP_URL || "http://46.224.144.27/app";
export const API_URL = process.env.TEST_API_URL || "http://46.224.144.27/api";
export const STRIPE_TEST_CONTRACTOR_ACCOUNT = "acct_1TMCwBFRMxx8LzH0";

export const E2E_CONTRACTOR_EMAIL = "e2e-contractor@sandbox.leo.casa";
export const E2E_HOMEOWNER_EMAIL = "e2e-homeowner@sandbox.leo.casa";
export const E2E_WRONG_CONTRACTOR_EMAIL = "e2e-wrong-contractor@sandbox.leo.casa";
export const E2E_WRONG_HOMEOWNER_EMAIL = "e2e-wrong-homeowner@sandbox.leo.casa";

export { ensureTestUser };

// ─── Supabase helpers (for verification + cleanup only) ────────────────────

function sbHeaders() {
  return {
    apikey: SUPABASE_KEY,
    Authorization: `Bearer ${SUPABASE_KEY}`,
    "Content-Type": "application/json",
    Prefer: "return=representation",
  };
}

export async function sbGet(
  table: string,
  params: Record<string, string>
): Promise<Record<string, unknown>[]> {
  const qs = new URLSearchParams(params);
  const resp = await fetch(`${SUPABASE_URL}/rest/v1/${table}?${qs}`, {
    headers: sbHeaders(),
  });
  if (!resp.ok) return [];
  return (await resp.json()) as Record<string, unknown>[];
}

export async function sbInsert(
  table: string,
  row: Record<string, unknown>
): Promise<Record<string, unknown>> {
  const resp = await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
    method: "POST",
    headers: sbHeaders(),
    body: JSON.stringify(row),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`sbInsert(${table}) failed ${resp.status}: ${text}`);
  }
  const data = await resp.json();
  return Array.isArray(data) ? data[0] : data;
}

export async function sbDelete(
  table: string,
  match: Record<string, string>
): Promise<void> {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(match)) params.set(k, `eq.${v}`);
  await fetch(`${SUPABASE_URL}/rest/v1/${table}?${params}`, {
    method: "DELETE",
    headers: sbHeaders(),
  });
}

// ─── Bootstrap: the minimum DB setup before UI flows ───────────────────────

export interface TestProject {
  token: string;
  contractorId: string;
  contractorAuthId: string;
  homeownerAuthId: string;
  homeownerEmail: string;
}

/**
 * Create the minimum infrastructure that can't be done through the UI:
 * 1. Auth users (contractor + homeowner) via Supabase admin
 * 2. Contractor row (because OnboardPro is an AI chat)
 *
 * Does NOT create a quote — that goes through the real finalize API.
 */
export async function bootstrapContractor(opts?: {
  tag?: string;
  contractorEmail?: string;
}): Promise<{
  contractorId: string;
  contractorAuthId: string;
  contractorEmail: string;
}> {
  if (!SUPABASE_KEY) throw new Error("SUPABASE_SERVICE_ROLE_KEY not set");

  const tag = opts?.tag ?? crypto.randomUUID().replace(/-/g, "").slice(0, 8);
  const email = opts?.contractorEmail ?? E2E_CONTRACTOR_EMAIL;

  const user = await ensureTestUser(email);
  const contractorId = `e2e-${tag}`;

  const existing = await sbGet("contractors", {
    id: `eq.${contractorId}`,
    select: "id",
    limit: "1",
  });
  if (!existing.length) {
    await sbInsert("contractors", {
      id: contractorId,
      name: "Fontanería Martínez E2E",
      phone: "+34612345678",
      canvas_token: `e2e-canvas-${tag}`,
      claimed: true,
      provenance: "playwright_e2e",
      stripe_account_id: STRIPE_TEST_CONTRACTOR_ACCOUNT,
      stripe_onboarding_complete: true,
      auth_user_id: user.id,
      dossier: {
        trade: "fontanero",
        city: "Madrid",
        bio: "Fontanero profesional con 15 años de experiencia en reforma integral",
        languages: ["es"],
      },
    });
  } else {
    await linkUserToContractor(user.id, contractorId);
  }

  return { contractorId, contractorAuthId: user.id, contractorEmail: email };
}

/**
 * Create a quote through the REAL backend finalize API — the same endpoint
 * the app calls when a contractor clicks "Finalizar" in FirstQuote.
 *
 * This produces a quote row with all the fields the production app creates:
 * computed financials, proper milestone tracking array, quote_data with title,
 * line_items, terms, service_fee_percent, iva_rate, etc.
 */
export async function createQuoteViaAPI(opts: {
  contractorId: string;
  contractorAuthId: string;
  homeownerEmail: string;
  milestoneCount?: number;
  sandbox?: boolean;
}): Promise<{ token: string; canvasUrl: string }> {
  const {
    contractorId,
    contractorAuthId,
    homeownerEmail,
    milestoneCount = 2,
    sandbox = true,
  } = opts;

  // Build quote_data matching exactly what FirstQuote.tsx sends
  const lineItems = [];
  const phaseNames = [
    "Demolición y preparación",
    "Instalación de fontanería",
    "Alicatado y acabados",
    "Instalación eléctrica",
    "Pintura y limpieza final",
  ];
  const durations = ["1 día", "2 días", "3 días", "2 días", "1 día"];
  const amountPerPhase = 500;

  for (let i = 0; i < milestoneCount; i++) {
    lineItems.push({
      description: phaseNames[i % phaseNames.length],
      amount: amountPerPhase,
      duration_label: durations[i % durations.length],
    });
  }

  const quoteData = {
    title: "Reforma de Baño — Proyecto E2E",
    description: "Reforma integral de baño: demolición, fontanería, alicatado porcelánico 60×60, instalación de sanitarios Roca y pintura.",
    contractor_name: "Fontanería Martínez E2E",
    client_name: "Propietario Test",
    location: "Calle Gran Vía 42, Madrid",
    line_items: lineItems,
    service_fee_percent: 5,
    materials_upfront: 200,
    iva_rate: 10,
    terms: [
      "Plazo de ejecución: 10 días laborables",
      "Presupuesto válido por 30 días",
      "Garantía de 2 años en mano de obra",
    ],
    status: "finalized",
    homeowner_name: "Test Homeowner",
  };

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(sandbox ? { "X-Sandbox": "true" } : {}),
  };

  const resp = await fetch(`${API_URL}/v1/quote/finalize`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      contractor_id: contractorId,
      quote_data: quoteData,
      auth_user_id: contractorAuthId,
    }),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Quote finalize failed ${resp.status}: ${text}`);
  }

  const result = (await resp.json()) as {
    ok: boolean;
    token: string;
    canvas_url: string;
  };

  if (!result.ok || !result.token) {
    throw new Error(`Quote finalize returned not-ok: ${JSON.stringify(result)}`);
  }

  // Set homeowner_email on the quote (finalize doesn't set it — it gets set
  // when the homeowner provides their email or when the contractor enters it)
  const params = new URLSearchParams({ token: `eq.${result.token}` });
  await fetch(`${SUPABASE_URL}/rest/v1/quotes?${params}`, {
    method: "PATCH",
    headers: sbHeaders(),
    body: JSON.stringify({ homeowner_email: homeownerEmail }),
  });

  return { token: result.token, canvasUrl: result.canvas_url };
}

// ─── Browser helpers ───────────────────────────────────────────────────────

export async function setSandboxMode(page: Page): Promise<void> {
  await page.goto(`${APP_URL}/`);
  await page.waitForLoadState("domcontentloaded");
  await page.evaluate(() => {
    localStorage.setItem("leo_sandbox_mode", "true");
    localStorage.setItem(
      "leo_sandbox_state",
      JSON.stringify({
        state: { enabled: true, personas: [], activePersonaId: null },
        version: 0,
      })
    );
  });
}

export async function loginAsContractor(
  page: Page,
  email = E2E_CONTRACTOR_EMAIL
): Promise<void> {
  await authenticateInBrowser(page, email);
}

export async function loginAsHomeowner(
  page: Page,
  email = E2E_HOMEOWNER_EMAIL
): Promise<void> {
  await authenticateInBrowser(page, email);
}

export async function gotoProject(page: Page, token: string): Promise<void> {
  await page.goto(`${APP_URL}/project/${token}`);
  await page.waitForLoadState("networkidle");
}

export async function gotoDashboard(page: Page): Promise<void> {
  await page.goto(`${APP_URL}/dashboard`);
  await page.waitForLoadState("networkidle");
}

export async function gotoCanvas(page: Page, token: string): Promise<void> {
  await page.goto(`${APP_URL}/canvas/${token}`);
  await page.waitForLoadState("networkidle");
}

export async function gotoChat(page: Page, token: string): Promise<void> {
  await page.goto(`${APP_URL}/job-chat/${token}`);
  await page.waitForLoadState("networkidle");
}

/**
 * Complete Stripe Checkout on checkout.stripe.com using the test card.
 * The page must already be on checkout.stripe.com (redirected from the app).
 * After completion, waits for redirect back to the app.
 */
export async function completeStripeCheckout(page: Page): Promise<void> {
  // Wait for Stripe Checkout page
  await page.waitForURL(/checkout\.stripe\.com/, { timeout: 30_000 });
  await page.waitForLoadState("networkidle");
  // Give Stripe UI time to fully hydrate
  await page.waitForTimeout(2000);

  // Fill email if present (Stripe sometimes asks)
  const emailField = page.locator('#email, input[name="email"]').first();
  if (await emailField.isVisible({ timeout: 3000 }).catch(() => false)) {
    await emailField.fill(E2E_HOMEOWNER_EMAIL);
    await page.keyboard.press("Tab");
    await page.waitForTimeout(500);
  }

  // Fill card number — Stripe Checkout uses direct inputs (not iframes) for
  // its hosted page. The test card fields have known selectors.
  const cardNumber = page.locator('#cardNumber, input[name="cardNumber"]').first();
  if (await cardNumber.isVisible({ timeout: 3000 }).catch(() => false)) {
    await cardNumber.fill("4242424242424242");
  } else {
    // Fallback: try the combined card element
    const combined = page.locator('[placeholder*="1234"], [autocomplete="cc-number"]').first();
    await combined.fill("4242424242424242");
  }
  await page.waitForTimeout(300);

  // Fill expiry
  const expiry = page.locator('#cardExpiry, input[name="cardExpiry"]').first();
  if (await expiry.isVisible({ timeout: 2000 }).catch(() => false)) {
    await expiry.fill("12/34");
  } else {
    await page.locator('[placeholder*="MM"]').first().fill("12/34");
  }
  await page.waitForTimeout(300);

  // Fill CVC
  const cvc = page.locator('#cardCvc, input[name="cardCvc"]').first();
  if (await cvc.isVisible({ timeout: 2000 }).catch(() => false)) {
    await cvc.fill("123");
  } else {
    await page.locator('[placeholder*="CVC"]').first().fill("123");
  }
  await page.waitForTimeout(300);

  // Fill cardholder name if present
  const billingName = page.locator('#billingName, input[name="billingName"]').first();
  if (await billingName.isVisible({ timeout: 2000 }).catch(() => false)) {
    await billingName.fill("Test Propietario");
  }
  await page.waitForTimeout(300);

  // Submit payment
  const submitBtn = page
    .locator('.SubmitButton, button[type="submit"]')
    .first();
  await submitBtn.click();

  // Wait for redirect back to the app
  await page.waitForURL(
    (url) => !url.toString().includes("checkout.stripe.com"),
    { timeout: 60_000 }
  );
  await page.waitForLoadState("networkidle");
}

// ─── Cleanup ────────────────────────────────────────────────────────────────

export async function cleanupTestProject(p: TestProject): Promise<void> {
  await Promise.all([
    sbDelete("milestone_updates", { scope_token: p.token }),
    sbDelete("variation_orders", { scope_token: p.token }),
    sbDelete("job_messages", { scope_token: p.token }),
    sbDelete("reviews", { quote_token: p.token }),
    sbDelete("notifications", { quote_token: p.token }),
  ]);
  await sbDelete("quotes", { token: p.token });
  await sbDelete("contractors", { id: p.contractorId });
}
