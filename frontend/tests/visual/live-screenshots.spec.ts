import { expect, test } from "@playwright/test";

import {
  seedVisualProfileSession,
  waitForAktuellHighlights,
  waitForEntdeckenRanking,
  waitForResultsPage,
} from "./support/pageReady";

const screenshotOptions = {
  fullPage: true,
  animations: "disabled" as const,
  maxDiffPixelRatio: 0.02,
};

test.describe("live API reference screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await seedVisualProfileSession(page);
  });

  test("aktuell desktop reference", async ({ page }) => {
    await page.goto("/aktuell");
    await waitForAktuellHighlights(page);
    await expect(page).toHaveScreenshot("aktuell-live-desktop.png", screenshotOptions);
  });

  test("entdecken desktop reference", async ({ page }) => {
    await page.goto("/entdecken");
    await waitForEntdeckenRanking(page);
    await waitForResultsPage(page);
    await expect(page).toHaveScreenshot("entdecken-live-desktop.png", screenshotOptions);
  });

  test("entdecken mobile reference", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/entdecken");
    await waitForEntdeckenRanking(page);
    await waitForResultsPage(page);
    await expect(page).toHaveScreenshot("entdecken-live-mobile.png", screenshotOptions);
  });

  test("aktuell mobile reference", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/aktuell");
    await waitForAktuellHighlights(page);
    await expect(page).toHaveScreenshot("aktuell-live-mobile.png", screenshotOptions);
  });
});
