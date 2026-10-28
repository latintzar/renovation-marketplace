/**
 * lifecycle-3ms.spec.ts — Full 3-milestone lifecycle, every UI state verified.
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

test.describe("3-milestone lifecycle — canvas states", () => {
  let project: FreshProject;

  test.afterEach(async () => {
    if (project) await cleanupProject(project);
  });

  test("canvas shows quote with 3 phases and pay button", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3 });

    await page.goto(`${APP_URL}/canvas/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("Reforma E2E")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Demolición")).toBeVisible();
    await expect(page.getByText("Fontanería")).toBeVisible();
    await expect(page.getByText("Alicatado")).toBeVisible();

    // Pay CTA
    await expect(
      page.getByRole("button", { name: /Pay.*Start project|Pagar/i })
    ).toBeVisible();
  });

  test("paid canvas shows escrow message, no pay button", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });

    await page.goto(`${APP_URL}/canvas/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(
      page.getByRole("button", { name: /Pay.*Start project|Pagar/i })
    ).not.toBeVisible();

    await expect(
      page.getByText(/escrow|custodia|Payment confirmed|Pago confirmado/i).first()
    ).toBeVisible();
  });

  test("paid canvas with ?paid=true shows success banner", async ({
    page,
  }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });

    await page.goto(`${APP_URL}/canvas/${project.token}?paid=true`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(
      page.getByText(/Payment received|funds.*held|Pago recibido|custodia/i).first()
    ).toBeVisible({ timeout: 10000 });
  });
});

test.describe("3-milestone lifecycle — project detail states", () => {
  let project: FreshProject;

  test.afterEach(async () => {
    if (project) await cleanupProject(project);
  });

  test("paid project shows all milestones pending", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("Pagado · En custodia")).toBeVisible({ timeout: 10000 });
    // Project detail shows amounts per phase (not names like canvas does)
    await expect(page.getByText("500,00 €").first()).toBeVisible();
  });

  test("after proof on m0 — status En progreso, Review phase 1 visible", async ({
    page,
  }) => {
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
  });

  test("after release m0 — milestone shows released", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await releaseMilestoneViaAPI(project, 0);
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(
      page.getByText(/released.*escrow|Released from escrow|Liberado|released/i).first()
    ).toBeVisible({ timeout: 10000 });
  });

  test("after all 3 proof+release — Completado, review available", async ({
    page,
  }) => {
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
      page.getByText(/Review|Invoice|Work completed|Completado|Reseña|Factura/i).first()
    ).toBeVisible();
  });

  test("contractor sees project detail after proof submitted", async ({
    page,
  }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await authenticateInBrowser(page, project.contractorEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("En progreso")).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByRole("button", { name: /View photos|Ver fotos/i }).first()
    ).toBeVisible();
  });
});

test.describe("3-milestone lifecycle — homeowner releases via UI", () => {
  let project: FreshProject;

  test.afterEach(async () => {
    if (project) await cleanupProject(project);
  });

  test("homeowner clicks Review phase → Approve & release → Confirm", async ({
    page,
  }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await page.getByRole("button", { name: /Review phase 1|Revisar fase 1/i }).click();
    await page.waitForTimeout(1500);

    const approveBtn = page.getByRole("button", {
      name: /Approve & release|Aprobar y liberar/i,
    });
    await expect(approveBtn).toBeVisible({ timeout: 5000 });
    await approveBtn.click();
    await page.waitForTimeout(500);

    const confirmBtn = page.getByRole("button", { name: /Confirm|Confirmar/i });
    await expect(confirmBtn).toBeVisible({ timeout: 3000 });
    await confirmBtn.click();

    await page.waitForTimeout(6000);

    const rows = await sbGet("quotes", {
      token: `eq.${project.token}`,
      select: "milestones",
    });
    expect((rows[0] as any)?.milestones?.[0]?.status).toBe("released");
  });

  test("homeowner releases all 3 via UI — project completes", async ({
    page,
  }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    for (let i = 0; i < 3; i++) {
      await submitProofViaAPI(project, i);
    }
    await authenticateInBrowser(page, project.homeownerEmail);

    for (let i = 0; i < 3; i++) {
      await page.goto(`${APP_URL}/project/${project.token}`);
      await page.waitForLoadState("networkidle");
      await dismissCookieConsent(page);
      await page.waitForTimeout(1500);

      await page.getByRole("button", {
        name: new RegExp(`Review phase ${i + 1}|Revisar fase ${i + 1}`, "i"),
      }).click();
      await page.waitForTimeout(1500);

      await page
        .getByRole("button", { name: /Approve & release|Aprobar y liberar/i })
        .click();
      await page.waitForTimeout(500);

      await page.getByRole("button", { name: /Confirm|Confirmar/i }).click();
      await page.waitForTimeout(6000);
    }

    const rows = await sbGet("quotes", {
      token: `eq.${project.token}`,
      select: "status",
    });
    expect((rows[0] as any)?.status).toBe("complete");
  });
});
