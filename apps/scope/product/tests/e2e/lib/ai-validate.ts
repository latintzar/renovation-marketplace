/**
 * tests/e2e/lib/ai-validate.ts
 * ============================
 *
 * AI-powered semantic validation for Playwright tests.
 * Uses Claude Sonnet 4.6 via OpenRouter (same pattern as the Leo sales backend).
 *
 * Two functions:
 *
 *   aiValidate(text, assertion) — checks rendered text against a plain-English assertion.
 *   aiValidateUX(page, assertion) — extracts text + aria snapshot and does a holistic UX check.
 *
 * Usage:
 *   import { aiValidate, aiValidateUX } from "./lib/ai-validate";
 *
 *   const text = await page.locator("main").innerText();
 *   const result = await aiValidate(text, "Shows a total price in EUR");
 *   expect(result.pass).toBe(true);
 *
 *   const ux = await aiValidateUX(page, "Is there a clear call-to-action button?");
 *   expect(ux.pass).toBe(true);
 */

import { Page } from "@playwright/test";

const OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions";
const OPENROUTER_MODEL = "anthropic/claude-sonnet-4-6";

function getApiKey(): string {
  const key =
    process.env.OPENROUTER_API_KEY ||
    process.env.ANTHROPIC_API_KEY ||
    process.env.AI_VALIDATE_API_KEY;
  if (!key) {
    throw new Error(
      "OPENROUTER_API_KEY not set — AI validation requires an OpenRouter API key."
    );
  }
  return key;
}

async function openRouterChat(system: string, user: string): Promise<string> {
  const resp = await fetch(OPENROUTER_CHAT_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getApiKey()}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://leo.casa",
      "X-Title": "Leo E2E Tests",
    },
    body: JSON.stringify({
      model: OPENROUTER_MODEL,
      messages: [
        { role: "system", content: system },
        { role: "user", content: user },
      ],
      max_tokens: 200,
      temperature: 0.1,
    }),
  });

  if (!resp.ok) {
    throw new Error(`OpenRouter error ${resp.status}: ${await resp.text()}`);
  }

  const data = (await resp.json()) as any;
  const content = data?.choices?.[0]?.message?.content;
  if (!content) throw new Error(`OpenRouter returned no content: ${JSON.stringify(data)}`);
  return String(content).trim();
}

export interface AIValidateResult {
  pass: boolean;
  reason: string;
  model: string;
}

const QA_SYSTEM = `You are a QA validator. Given page content and an assertion, reply ONLY with valid JSON:
{"pass": true, "reason": "one sentence"} or {"pass": false, "reason": "one sentence explaining what is missing or wrong"}
No other text.`;

/**
 * Validate page content against a natural-language assertion using Claude Sonnet via OpenRouter.
 */
export async function aiValidate(
  content: string,
  assertion: string
): Promise<AIValidateResult> {
  const truncated =
    content.length > 4000 ? content.slice(0, 4000) + "\n...[truncated]" : content;

  const user = `Page content:\n---\n${truncated}\n---\n\nAssertion: ${assertion}`;

  const raw = await openRouterChat(QA_SYSTEM, user);

  try {
    const parsed = JSON.parse(raw);
    return {
      pass: Boolean(parsed.pass),
      reason: String(parsed.reason || ""),
      model: OPENROUTER_MODEL,
    };
  } catch {
    const passMatch =
      raw.toLowerCase().includes('"pass": true') || raw.toLowerCase().startsWith("true");
    return {
      pass: passMatch,
      reason: raw.slice(0, 200),
      model: OPENROUTER_MODEL,
    };
  }
}

/**
 * Validate a full page's UX quality using visible text + aria snapshot.
 */
export async function aiValidateUX(
  page: Page,
  assertion: string
): Promise<AIValidateResult> {
  const text = await page
    .locator("main, [role='main'], body")
    .first()
    .innerText()
    .catch(() => "");

  let structure = "(accessibility tree unavailable)";
  try {
    const snap = await page.locator("body").ariaSnapshot().catch(() => null);
    if (snap) structure = snap.slice(0, 2000);
  } catch {
    // ariaSnapshot unavailable — text-only is still useful
  }

  const combined = `VISIBLE TEXT:\n${text}\n\nSEMANTIC STRUCTURE:\n${structure}`;
  return aiValidate(combined, assertion);
}

/**
 * Skip AI validation gracefully if no API key is set.
 */
export function skipIfNoApiKey(): boolean {
  return (
    !process.env.OPENROUTER_API_KEY &&
    !process.env.ANTHROPIC_API_KEY &&
    !process.env.AI_VALIDATE_API_KEY
  );
}
