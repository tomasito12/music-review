import { expect, test, type Page } from "@playwright/test";

import {
  seedVisualProfileSession,
  stabilizeVisualPage,
  visualScreenshotTarget,
  waitForAktuellHighlights,
  waitForEntdeckenRanking,
  waitForResultsPage,
} from "./support/pageReady";

function screenshotOptions(page: Page) {
  return {
    animations: "disabled" as const,
    mask: [page.locator(".highlight-tile-photo, .artist-image-source")],
  };
}

test.describe("live API reference screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await seedVisualProfileSession(page);
  });

  test("aktuell desktop reference", async ({ page }) => {
    await page.goto("/aktuell");
    await waitForAktuellHighlights(page);
    await stabilizeVisualPage(page);
    await expect(visualScreenshotTarget(page)).toHaveScreenshot(
      "aktuell-live-desktop.png",
      screenshotOptions(page),
    );
  });

  test("entdecken desktop reference", async ({ page }) => {
    await page.goto("/entdecken");
    await waitForEntdeckenRanking(page);
    await waitForResultsPage(page);
    await stabilizeVisualPage(page);
    await expect(visualScreenshotTarget(page)).toHaveScreenshot(
      "entdecken-live-desktop.png",
      screenshotOptions(page),
    );
  });

  test("entdecken mobile reference", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/entdecken");
    await waitForEntdeckenRanking(page);
    await waitForResultsPage(page);
    await stabilizeVisualPage(page);
    await expect(visualScreenshotTarget(page)).toHaveScreenshot(
      "entdecken-live-mobile.png",
      screenshotOptions(page),
    );
  });

  test("aktuell mobile reference", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/aktuell");
    await waitForAktuellHighlights(page);
    await stabilizeVisualPage(page);
    await expect(visualScreenshotTarget(page)).toHaveScreenshot(
      "aktuell-live-mobile.png",
      screenshotOptions(page),
    );
  });
});
