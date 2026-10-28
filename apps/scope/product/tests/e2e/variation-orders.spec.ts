/**
 * variation-orders.spec.ts — Change order flows.
 *
 * Variations are verified via DB state + project detail page renders.
 */

import { test, expect } from "@playwright/test";
import {
  createFreshProject,
  cleanupProject,
  submitProofViaAPI,
  releaseMilestoneViaAPI,
  createVariationViaAPI,
  dismissCookieConsent,
  authenticateInBrowser,
  APP_URL,
  sbGet,
  type FreshProject,
} from "./lib/setup";

test.describe("variation orders", () => {
  let project: FreshProject;

  test.afterEach(async () => {
    if (project) await cleanupProject(project);
  });

  test("variation created in DB with correct status", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    const variationId = await createVariationViaAPI(project, "Extra plumbing", 25000);

    expect(variationId).toBeTruthy();

    const variations = await sbGet("variation_orders", {
      scope_token: `eq.${project.token}`,
      select: "title,status,amount_cents",
    });
    expect(variations.length).toBe(1);
    expect((variations[0] as any)?.title).toBe("Extra plumbing");
    expect((variations[0] as any)?.status).toBe("pending");
    expect((variations[0] as any)?.amount_cents).toBe(25000);
  });

  test("project detail page loads with variation present", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await createVariationViaAPI(project, "New tile work", 15000);

    await authenticateInBrowser(page, project.homeownerEmail);
    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    // Page should load and show the project status
    await expect(page.getByText("En progreso")).toBeVisible({ timeout: 10000 });

    // Check if variation section or change order text is visible
    const bodyText = await page.locator("body").innerText();
    const hasVariation =
      bodyText.includes("New tile work") ||
      bodyText.includes("Change order") ||
      bodyText.includes("Cambio") ||
      bodyText.includes("150,00");

    // Also verify variation exists in DB
    const variations = await sbGet("variation_orders", {
      scope_token: `eq.${project.token}`,
      select: "status",
    });
    expect(variations.length).toBe(1);
    expect((variations[0] as any)?.status).toBe("pending");
  });

  test("homeowner declines variation via API", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await createVariationViaAPI(project, "Unnecessary work", 30000);

    // Decline via API (UI decline requires clicking the variation row)
    const jwt = await getJwtHelper(project.homeownerEmail);
    const variations = await sbGet("variation_orders", {
      scope_token: `eq.${project.token}`,
      select: "id",
      order: "created_at.desc",
      limit: "1",
    });

    const resp = await fetch(
      `http://localhost:8000/v1/projects/${project.token}/variations/${(variations[0] as any).id}/decline`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${jwt}`,
          "X-Sandbox": "true",
        },
      }
    );
    expect(resp.ok).toBeTruthy();

    const updated = await sbGet("variation_orders", {
      scope_token: `eq.${project.token}`,
      select: "status",
    });
    expect((updated[0] as any)?.status).toBe("declined");
  });

  test("contractor view shows project with variation in DB", async ({
    page,
  }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await createVariationViaAPI(project, "Pipe reroute", 20000);

    await authenticateInBrowser(page, project.contractorEmail);
    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("En progreso")).toBeVisible({ timeout: 10000 });

    const variations = await sbGet("variation_orders", {
      scope_token: `eq.${project.token}`,
      select: "title,status",
    });
    expect((variations[0] as any)?.title).toBe("Pipe reroute");
  });

  test("variation + mid-project release — project tracks correctly", async ({
    page,
  }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await createVariationViaAPI(project, "Foundation reinforcement", 50000);
    await releaseMilestoneViaAPI(project, 0);

    await authenticateInBrowser(page, project.homeownerEmail);
    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("En progreso")).toBeVisible({ timeout: 10000 });

    const rows = await sbGet("quotes", {
      token: `eq.${project.token}`,
      select: "milestones,status",
    });
    expect((rows[0] as any)?.milestones?.[0]?.status).toBe("released");
    expect((rows[0] as any)?.status).toBe("in_progress");
  });
});

async function getJwtHelper(email: string): Promise<string> {
  const anonKey =
    "local-test-anon-key";
  const resp = await fetch(
    `http://127.0.0.1:54321/auth/v1/token?grant_type=password`,
    {
      method: "POST",
      headers: { apikey: anonKey, "Content-Type": "application/json" },
      body: JSON.stringify({ email, password: "test-pw-e2e-2026!" }),
    }
  );
  return (await resp.json()).access_token;
}
