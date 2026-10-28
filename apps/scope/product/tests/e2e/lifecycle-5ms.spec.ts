/**
 * lifecycle-5ms.spec.ts — Full 5-milestone lifecycle.
 */

import { test, expect } from "@playwright/test";
import {
  createFreshProject,
  cleanupProject,
  submitProofViaAPI,
  releaseMilestoneViaAPI,
  dismissCookieConsent,
  authenticateInBrowser,
  APP_URL,
  sbGet,
  type FreshProject,
} from "./lib/setup";

test.describe("5-milestone lifecycle", () => {
  let project: FreshProject;

  test.afterEach(async () => {
    if (project) await cleanupProject(project);
  });

  test("project detail shows all 5 milestones", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 5, paid: true });
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("Pagado · En custodia")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("500,00 €").first()).toBeVisible();
  });

  test("proof on m0 and m1 — mixed state, 2 review buttons", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 5, paid: true });
    await submitProofViaAPI(project, 0);
    await submitProofViaAPI(project, 1);
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
    ).toBeVisible();
  });

  test("3 of 5 released, proof on 4th — partial progress", async ({
    page,
  }) => {
    project = await createFreshProject({ milestoneCount: 5, paid: true });
    for (let i = 0; i < 3; i++) {
      await submitProofViaAPI(project, i);
      await releaseMilestoneViaAPI(project, i);
    }
    await submitProofViaAPI(project, 3);
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("En progreso")).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByRole("button", { name: /Review phase 4|Revisar fase 4/i })
    ).toBeVisible();
  });

  test("all 5 released — Completado", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 5, paid: true });
    for (let i = 0; i < 5; i++) {
      await submitProofViaAPI(project, i);
      await releaseMilestoneViaAPI(project, i);
    }
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("Completado").first()).toBeVisible({ timeout: 10000 });
  });

  test("contractor view — all 5 released shows Completado", async ({
    page,
  }) => {
    project = await createFreshProject({ milestoneCount: 5, paid: true });
    for (let i = 0; i < 5; i++) {
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
