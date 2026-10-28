/**
 * project-states.spec.ts — Project detail page in every possible state.
 */

import { test, expect } from "@playwright/test";
import {
  createFreshProject,
  cleanupProject,
  submitProofViaAPI,
  releaseMilestoneViaAPI,
  openDisputeViaAPI,
  dismissCookieConsent,
  authenticateInBrowser,
  APP_URL,
  sbGet,
  type FreshProject,
} from "./lib/setup";

test.describe("project detail — every state permutation", () => {
  let project: FreshProject;

  test.afterEach(async () => {
    if (project) await cleanupProject(project);
  });

  test("paid, 0/3 proof — Pagado badge, no review buttons", async ({
    page,
  }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("Pagado · En custodia")).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByRole("button", { name: /Review phase|Revisar fase/i })
    ).not.toBeVisible();
  });

  test("1/3 proof — En progreso, 1 review button", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("En progreso")).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByRole("button", { name: /Review phase 1|Revisar fase 1/i })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Review phase 2|Revisar fase 2/i })
    ).not.toBeVisible();
  });

  test("2/3 proof — 2 review buttons visible", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await submitProofViaAPI(project, 1);
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(
      page.getByRole("button", { name: /Review phase 1|Revisar fase 1/i })
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByRole("button", { name: /Review phase 2|Revisar fase 2/i })
    ).toBeVisible();
  });

  test("1/3 released — released indicator visible", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await releaseMilestoneViaAPI(project, 0);
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("En progreso")).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText(/released.*escrow|Released|Liberado/i).first()
    ).toBeVisible();
  });

  test("2/3 released, 1 proof — phase 3 reviewable", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await releaseMilestoneViaAPI(project, 0);
    await submitProofViaAPI(project, 1);
    await releaseMilestoneViaAPI(project, 1);
    await submitProofViaAPI(project, 2);
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("En progreso")).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByRole("button", { name: /Review phase 3|Revisar fase 3/i })
    ).toBeVisible();
  });

  test("3/3 released — Completado, no review buttons", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    for (let i = 0; i < 3; i++) {
      await submitProofViaAPI(project, i);
      await releaseMilestoneViaAPI(project, i);
    }
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("Completado").first()).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByRole("button", { name: /Review phase|Revisar fase/i })
    ).not.toBeVisible();
  });

  test("m0 disputed — DB shows disputed, project still in_progress", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await openDisputeViaAPI(project, 0);

    const rows = await sbGet("quotes", {
      token: `eq.${project.token}`,
      select: "milestones",
    });
    expect((rows[0] as any)?.milestones?.[0]?.status).toBe("disputed");

    await authenticateInBrowser(page, project.homeownerEmail);
    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(
      page.getByText(/En progreso|En disputa/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("contractor: paid — sees Pagado badge", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await authenticateInBrowser(page, project.contractorEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("Pagado · En custodia")).toBeVisible({ timeout: 10000 });
  });

  test("contractor: proof submitted — sees View photos not Review", async ({
    page,
  }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await authenticateInBrowser(page, project.contractorEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(
      page.getByRole("button", { name: /View photos|Ver fotos/i }).first()
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByRole("button", { name: /Review phase|Revisar fase/i })
    ).not.toBeVisible();
  });

  test("contractor: complete — sees Completado", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    for (let i = 0; i < 3; i++) {
      await submitProofViaAPI(project, i);
      await releaseMilestoneViaAPI(project, i);
    }
    await authenticateInBrowser(page, project.contractorEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("Completado").first()).toBeVisible({ timeout: 10000 });
  });
});
