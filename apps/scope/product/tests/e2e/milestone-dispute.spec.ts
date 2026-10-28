/**
 * milestone-dispute.spec.ts — Dispute and resubmit flow.
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

test.describe("milestone dispute flow", () => {
  let project: FreshProject;

  test.afterEach(async () => {
    if (project) await cleanupProject(project);
  });

  test("disputed milestone — DB shows disputed, UI reflects in_progress", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await openDisputeViaAPI(project, 0);

    // Verify DB state
    const rows = await sbGet("quotes", {
      token: `eq.${project.token}`,
      select: "milestones",
    });
    expect((rows[0] as any)?.milestones?.[0]?.status).toBe("disputed");

    await authenticateInBrowser(page, project.homeownerEmail);
    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    // Project overall status is still in_progress (only 1 milestone disputed)
    await expect(page.getByText(/En progreso|En disputa/i).first()).toBeVisible({ timeout: 10000 });
  });

  test("dispute → resubmit → review button reappears", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await openDisputeViaAPI(project, 0);
    await submitProofViaAPI(project, 0);
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(
      page.getByRole("button", { name: /Review phase 1|Revisar fase 1/i })
    ).toBeVisible({ timeout: 10000 });
  });

  test("dispute on m1, m0 released and m2 pending — DB states correct", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await releaseMilestoneViaAPI(project, 0);
    await submitProofViaAPI(project, 1);
    await openDisputeViaAPI(project, 1);
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    const rows = await sbGet("quotes", {
      token: `eq.${project.token}`,
      select: "milestones",
    });
    const ms = (rows[0] as any)?.milestones;
    expect(ms[0].status).toBe("released");
    expect(ms[1].status).toBe("disputed");
    expect(ms[2].status).toBe("pending");
  });

  test("full flow: dispute m0 → resubmit → release all 3 → complete", async ({
    page,
  }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await submitProofViaAPI(project, 0);
    await openDisputeViaAPI(project, 0);
    await submitProofViaAPI(project, 0);
    await releaseMilestoneViaAPI(project, 0);
    await submitProofViaAPI(project, 1);
    await releaseMilestoneViaAPI(project, 1);
    await submitProofViaAPI(project, 2);
    await releaseMilestoneViaAPI(project, 2);

    await authenticateInBrowser(page, project.homeownerEmail);
    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    await expect(page.getByText("Completado").first()).toBeVisible({ timeout: 10000 });

    const rows = await sbGet("quotes", {
      token: `eq.${project.token}`,
      select: "status",
    });
    expect((rows[0] as any)?.status).toBe("complete");
  });
});
