import { expect, test, type Page } from "@playwright/test";

import {
  assertScreenshotLayoutStable,
  seedVisualProfileSession,
  stabilizeVisualPage,
  visualScreenshotClip,
  waitForAktuellHighlights,
  waitForEntdeckenRanking,
} from "./support/pageReady";

function screenshotOptions(page: Page) {
  return {
    animations: "disabled" as const,
    mask: [page.locator(".highlight-tile-photo, .artist-image-source, .recommendation-card-thumbnail")],
  };
}

async function captureReferenceScreenshot(
  page: Page,
  snapshotName: string,
): Promise<void> {
  await stabilizeVisualPage(page);
  await assertScreenshotLayoutStable(page);
  await page.waitForTimeout(250);
  await stabilizeVisualPage(page);
  await expect(page).toHaveScreenshot(
    snapshotName,
    {
      ...screenshotOptions(page),
      clip: visualScreenshotClip(page),
      timeout: 30_000,
    },
  );
}

test.describe("live API reference screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await seedVisualProfileSession(page);
  });

  test("aktuell desktop reference", async ({ page }) => {
    await page.goto("/neuheiten");
    await waitForAktuellHighlights(page);
    await captureReferenceScreenshot(page, "aktuell-live-desktop.png");
  });

  test("entdecken desktop reference", async ({ page }) => {
    await page.goto("/entdecken");
    await waitForEntdeckenRanking(page);
    await captureReferenceScreenshot(page, "entdecken-live-desktop.png");
  });

  test("entdecken mobile reference", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/entdecken");
    await waitForEntdeckenRanking(page);
    await captureReferenceScreenshot(page, "entdecken-live-mobile.png");
  });

  test("aktuell mobile reference", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/neuheiten");
    await waitForAktuellHighlights(page);
    await captureReferenceScreenshot(page, "aktuell-live-mobile.png");
  });
});
