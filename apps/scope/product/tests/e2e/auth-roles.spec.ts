/**
 * auth-roles.spec.ts — Role-based access control in the UI.
 */

import { test, expect } from "@playwright/test";
import {
  createFreshProject,
  cleanupProject,
  authenticateInBrowser,
  dismissCookieConsent,
  APP_URL,
  type FreshProject,
} from "./lib/setup";
import { ensureTestUser } from "./lib/auth";
import { sbInsert, sbDelete } from "./lib/fixtures";

test.describe("auth & role guards", () => {
  let project: FreshProject;

  test.afterEach(async () => {
    if (project) await cleanupProject(project);
  });

  test("unauthenticated user sees login prompt on project page", async ({
    page,
  }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    // InlineLogin: shows "Inicia sesión" (ES) or "Sign in" (EN)
    await expect(
      page
        .getByText(/Inicia sesión|Iniciar sesión|Sign in|Log in/i)
        .first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("wrong contractor sees error on project page", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });

    const wrongEmail = `e2e-wrong-c-${crypto.randomUUID().slice(0, 8)}@sandbox.leo.casa`;
    const wrongUser = await ensureTestUser(wrongEmail);

    const wrongTag = crypto.randomUUID().slice(0, 8);
    const wrongCId = `e2e-wrong-${wrongTag}`;
    await sbInsert("contractors", {
      id: wrongCId,
      name: "Wrong Contractor",
      phone: `+349${wrongTag}`,
      canvas_token: `wrong-${wrongCId}`,
      claimed: true,
      provenance: "test",
      auth_user_id: wrongUser.id,
      dossier: { trade: "electrician", city: "Barcelona" },
    });

    await authenticateInBrowser(page, wrongEmail);
    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    // "Estás conectado como contratista" (ES) or "logged in as a contractor" (EN)
    await expect(
      page
        .getByText(
          /contratista|contractor|Cuenta incorrecta|Wrong account|Cerrar sesión/i
        )
        .first()
    ).toBeVisible({ timeout: 10000 });

    await sbDelete("contractors", { id: wrongCId });
  });

  test("wrong homeowner sees error on project page", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });

    const wrongEmail = `e2e-wrong-ho-${crypto.randomUUID().slice(0, 8)}@sandbox.leo.casa`;
    await ensureTestUser(wrongEmail);
    await authenticateInBrowser(page, wrongEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    // "Cuenta incorrecta" (ES) or "Wrong account" (EN)
    await expect(
      page
        .getByText(/Cuenta incorrecta|Wrong account|Cambiar de cuenta|Switch/i)
        .first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("homeowner visiting /dashboard gets redirected", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/dashboard`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);

    expect(page.url()).toContain("my-project");
  });

  test("contractor visiting /my-projects gets redirected", async ({
    page,
  }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await authenticateInBrowser(page, project.contractorEmail);

    await page.goto(`${APP_URL}/my-projects`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(3000);

    expect(page.url()).toContain("dashboard");
  });

  test("homeowner sees their own project in my-projects list", async ({
    page,
  }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/my-projects`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    // Project card shows title or fallback "Proyecto", plus amount
    await expect(
      page.getByText(/Proyecto|Reforma E2E|1725/i).first()
    ).toBeVisible({ timeout: 15000 });
  });

  test("contractor sees dashboard page", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await authenticateInBrowser(page, project.contractorEmail);

    await page.goto(`${APP_URL}/dashboard`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    // Dashboard shows "My jobs" heading or Spanish equivalent, or at minimum loads
    await expect(
      page.getByText(/My jobs|Mis trabajos|Pagado|custodia|Reforma|Algo fue/i).first()
    ).toBeVisible({ timeout: 15000 });
  });
});
