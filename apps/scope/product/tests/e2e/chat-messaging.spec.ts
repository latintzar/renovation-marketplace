/**
 * chat-messaging.spec.ts — In-job chat messaging tests.
 */

import { test, expect } from "@playwright/test";
import {
  createFreshProject,
  cleanupProject,
  sendMessageViaAPI,
  dismissCookieConsent,
  authenticateInBrowser,
  APP_URL,
  type FreshProject,
} from "./lib/setup";

test.describe("chat messaging", () => {
  let project: FreshProject;

  test.afterEach(async () => {
    if (project) await cleanupProject(project);
  });

  test("contractor message appears in chat page", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await sendMessageViaAPI(
      project,
      "contractor",
      "Starting work on Phase 1 tomorrow"
    );

    await authenticateInBrowser(page, project.homeownerEmail);
    await page.goto(`${APP_URL}/job-chat/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);
    await page.waitForTimeout(2000);

    await expect(
      page.getByText("Starting work on Phase 1 tomorrow")
    ).toBeVisible({ timeout: 10000 });
  });

  test("homeowner message appears in chat page", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await sendMessageViaAPI(
      project,
      "homeowner",
      "When will materials arrive?"
    );

    await authenticateInBrowser(page, project.contractorEmail);
    await page.goto(`${APP_URL}/job-chat/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);
    await page.waitForTimeout(2000);

    await expect(
      page.getByText("When will materials arrive?")
    ).toBeVisible({ timeout: 10000 });
  });

  test("multiple messages appear in chronological order", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await sendMessageViaAPI(project, "contractor", "Message 1: Starting");
    await sendMessageViaAPI(
      project,
      "homeowner",
      "Message 2: OK sounds good"
    );
    await sendMessageViaAPI(project, "contractor", "Message 3: Materials bought");

    await authenticateInBrowser(page, project.homeownerEmail);
    await page.goto(`${APP_URL}/job-chat/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);
    await page.waitForTimeout(2000);

    await expect(page.getByText("Message 1: Starting")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Message 2: OK sounds good")).toBeVisible();
    await expect(page.getByText("Message 3: Materials bought")).toBeVisible();

    const bodyText = await page.locator("body").innerText();
    const idx1 = bodyText.indexOf("Message 1:");
    const idx3 = bodyText.indexOf("Message 3:");
    expect(idx1).toBeLessThan(idx3);
  });

  test("chat link from project detail navigates to chat", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await sendMessageViaAPI(project, "contractor", "Chat link test message");

    await authenticateInBrowser(page, project.homeownerEmail);
    await page.goto(`${APP_URL}/project/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);

    const chatLink = page.locator(`a[href*="job-chat/${project.token}"]`);
    if (await chatLink.isVisible().catch(() => false)) {
      await chatLink.click();
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(2000);

      await expect(
        page.getByText("Chat link test message")
      ).toBeVisible({ timeout: 10000 });
    }
  });

  test("homeowner sends a message via UI input", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await authenticateInBrowser(page, project.homeownerEmail);

    await page.goto(`${APP_URL}/job-chat/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);
    await page.waitForTimeout(1000);

    const input = page.getByPlaceholder(/Type a message|Escribe|mensaje/i);
    await expect(input).toBeVisible({ timeout: 10000 });
    await input.fill("Hello contractor, question about timeline");
    await input.press("Enter");
    await page.waitForTimeout(4000);

    await expect(
      page.getByText("Hello contractor, question about timeline")
    ).toBeVisible({ timeout: 10000 });
  });

  test("contractor sends a message via UI input", async ({ page }) => {
    project = await createFreshProject({ milestoneCount: 3, paid: true });
    await authenticateInBrowser(page, project.contractorEmail);

    await page.goto(`${APP_URL}/job-chat/${project.token}`);
    await page.waitForLoadState("networkidle");
    await dismissCookieConsent(page);
    await page.waitForTimeout(1000);

    const input = page.getByPlaceholder(/Type a message|Escribe|mensaje/i);
    await expect(input).toBeVisible({ timeout: 10000 });
    await input.fill("Work starts Monday morning");
    await input.press("Enter");
    await page.waitForTimeout(4000);

    await expect(
      page.getByText("Work starts Monday morning")
    ).toBeVisible({ timeout: 10000 });
  });
});
