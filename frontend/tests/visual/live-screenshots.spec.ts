import { expect, test, type Page } from "@playwright/test";

import {
  assertScreenshotLayoutStable,
  generatePlaylistFromForm,
  seedVisualProfileSession,
  stabilizeVisualPage,
  visualPlaylistLayoutProbe,
  visualScreenshotClip,
  waitForAktuellHighlights,
  waitForEntdeckenRanking,
  waitForPlaylistForm,
  waitForPlaylistResults,
  waitForVisualLayoutStable,
} from "./support/pageReady";
import { VISUAL_PROFILE_STORAGE_KEY } from "./support/visualProfile";

function screenshotOptions(page: Page) {
  return {
    animations: "disabled" as const,
    mask: [
      page.locator(
        ".highlight-tile-photo, .artist-image-source, .recommendation-card-thumbnail, .playlist-artist-mosaic-tile, .playlist-track-row .recommendation-card-thumbnail",
      ),
    ],
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

async function capturePlaylistReferenceScreenshot(
  page: Page,
  snapshotName: string,
): Promise<void> {
  const probe = visualPlaylistLayoutProbe(page);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.evaluate(async () => {
    await document.fonts.ready;
  });
  await waitForVisualLayoutStable(page, 60_000, probe);
  await assertScreenshotLayoutStable(page, probe);
  await page.waitForTimeout(250);
  await waitForVisualLayoutStable(page, 60_000, probe);
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

  test("playlists form desktop reference", async ({ page }) => {
    await page.goto("/playlists");
    await waitForPlaylistForm(page);
    await capturePlaylistReferenceScreenshot(page, "playlists-form-desktop.png");
  });

  test("playlists form mobile reference", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/playlists");
    await waitForPlaylistForm(page);
    await capturePlaylistReferenceScreenshot(page, "playlists-form-mobile.png");
  });

  test("playlists archive form desktop reference", async ({ page }) => {
    await page.goto("/playlists");
    await waitForPlaylistForm(page);
    await page.getByRole("button", { name: "Entdecken" }).click();
    await page.locator('[data-visual-playlist-ready="form"]').waitFor({
      timeout: 30_000,
    });
    await page.locator(".playlist-pool-summary").waitFor({
      timeout: 30_000,
    });
    await waitForPlaylistForm(page);
    await capturePlaylistReferenceScreenshot(page, "playlists-archive-form-desktop.png");
  });

  test("playlists results desktop reference", async ({ page }) => {
    await page.goto("/playlists");
    await waitForPlaylistForm(page);
    await generatePlaylistFromForm(page);
    await waitForPlaylistResults(page);
    await capturePlaylistReferenceScreenshot(page, "playlists-results-desktop.png");
  });

  test("playlists results mobile reference", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/playlists");
    await waitForPlaylistForm(page);
    await generatePlaylistFromForm(page);
    await waitForPlaylistResults(page);
    await capturePlaylistReferenceScreenshot(page, "playlists-results-mobile.png");
  });
});

test.describe("playlists gate reference screenshots", () => {
  test("playlists without profile desktop reference", async ({ page }) => {
    await page.addInitScript(
      ({ storageKey, styleContent }) => {
        window.sessionStorage.removeItem(storageKey);
        document.documentElement.dataset.visualTest = "true";
        const existingStyle = document.getElementById("plattenradar-visual-test-fonts");
        if (existingStyle === null) {
          const style = document.createElement("style");
          style.id = "plattenradar-visual-test-fonts";
          style.textContent = styleContent;
          document.documentElement.appendChild(style);
        }
      },
      {
        storageKey: VISUAL_PROFILE_STORAGE_KEY,
        styleContent: `
          html[data-visual-test] :where(body, button, input, select, textarea, p, li, span, a) {
            font-family: "Liberation Sans", Arial, Helvetica, sans-serif !important;
          }
        `,
      },
    );
    await page.goto("/playlists");
    await page.locator('[data-visual-playlist-ready="gate"]').waitFor({
      timeout: 30_000,
    });
    await capturePlaylistReferenceScreenshot(page, "playlists-gate-desktop.png");
  });
});
