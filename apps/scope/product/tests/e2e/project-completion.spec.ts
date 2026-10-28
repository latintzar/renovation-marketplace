/**
 * project-completion.spec.ts — Post-completion: review, invoice, agreement.
 */

import { test, expect } from "@playwright/test";
import {
  createFreshProject,
  cleanupProject,
  submitProofViaAPI,
  releaseMilestoneViaAPI,
  getJwt,
  dismissCookieConsent,
  authenticateInBrowser,
  APP_URL,
  API_URL,
  sbGet,
  type FreshProject,
} from "./lib/setup";

async function completeProject(project: FreshProject): Promise<void> {
  for (let i = 0; i < project.milestoneCount; i++) {
    await submitProofViaAPI(project, i);
    await releaseMilestoneViaAPI(project, i);
  }
}

test.describe("project completion — review", () => {
  let project: FreshProject;

  test.afterEach(async () => {
    if (project) await cleanupProject(project);
  });

  test("completed project shows review UI", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await completeProject(project);
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("Completado").first()).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText(/Valorar|Factura|Work completed|Trabajo completado/i).first()
    ).toBeVisible();
  });

  test("Valorar button opens review sheet", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await completeProject(project);
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    const reviewBtn = page.getByRole("button", { name: /Valorar|Review/i }).first();
    await expect(reviewBtn).toBeVisible({ timeout: 10000 });
    await reviewBtn.click();
    await page.waitForTimeout(1500);

    // Review sheet should show heading and submit button
    await expect(
      page.getByText(/How was the work|Cómo fue/i).first()
    ).toBeVisible({ timeout: 5000 });
    await expect(
      page.getByRole("button", { name: /Submit review|Enviar/i })
    ).toBeVisible();
  });

  test("review submitted via API reflects in DB", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await completeProject(project);

    const jwt = await getJwt(project.homeownerEmail);
    const resp = await fetch(`${API_URL}/v1/projects/${project.token}/review`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwt}`,
        "X-Sandbox": "true",
      },
      body: JSON.stringify({ rating: 5, body: "Excellent renovation!" }),
    });
    expect(resp.ok).toBeTruthy();

    const reviews = await sbGet("reviews", {
      scope_token: `eq.${project.token}`,
      select: "rating,body",
    });
    expect(reviews.length).toBe(1);
    expect((reviews[0] as any)?.rating).toBe(5);
    expect((reviews[0] as any)?.body).toBe("Excellent renovation!");
  });

  test("1-star review with body via API", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await completeProject(project);

    const jwt = await getJwt(project.homeownerEmail);
    await fetch(`${API_URL}/v1/projects/${project.token}/review`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwt}`,
        "X-Sandbox": "true",
      },
      body: JSON.stringify({ rating: 1, body: "Work was below expectations." }),
    });

    const reviews = await sbGet("reviews", {
      scope_token: `eq.${project.token}`,
      select: "rating,body",
    });
    expect(reviews.length).toBe(1);
    expect((reviews[0] as any)?.rating).toBe(1);
  });
});

test.describe("project completion — documents", () => {
  let project: FreshProject;

  test.afterEach(async () => {
    if (project) await cleanupProject(project);
  });

  test("invoice link visible after completion", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await completeProject(project);
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(
      page.getByText(/Invoice|Factura/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("agreement link available on project page", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(
      page.getByText(/Ver acuerdo|View agreement|contrato|agreement/i).first()
    ).toBeVisible({ timeout: 10000 });
  });
});

test.describe("project completion — contractor profile impact", () => {
  let project: FreshProject;

  test.afterEach(async () => {
    if (project) await cleanupProject(project);
  });

  test("contractor rating updates after review via API", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await completeProject(project);

    const jwt = await getJwt(project.homeownerEmail);

    await fetch(`${API_URL}/v1/projects/${project.token}/review`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwt}`,
        "X-Sandbox": "true",
      },
      body: JSON.stringify({ rating: 5, body: "Perfect!" }),
    });

    const contractors = await sbGet("contractors", {
      id: `eq.${project.contractorId}`,
      select: "avg_rating,review_count",
    });
    expect((contractors[0] as any)?.review_count).toBeGreaterThanOrEqual(1);
  });
});
