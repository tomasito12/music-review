import type { Page } from "@playwright/test";

import {
  VISUAL_PROFILE_SESSION,
  VISUAL_PROFILE_STORAGE_KEY,
} from "./visualProfile";

const VISUAL_TEST_STYLE = `
  html[data-visual-test] :where(body, button, input, select, textarea, p, li, span, a) {
    font-family: "Liberation Sans", Arial, Helvetica, sans-serif !important;
  }
  html[data-visual-test] :where(h1, h2, h3, .highlight-tile-title) {
    font-family: "Liberation Serif", "Times New Roman", Times, serif !important;
  }
`;

/** Seed the temporary taste profile used by visual regression tests. */
export async function seedVisualProfileSession(page: Page): Promise<void> {
  await page.addInitScript(
    ({ storageKey, session }) => {
      window.sessionStorage.setItem(storageKey, JSON.stringify(session));
      document.documentElement.dataset.visualTest = "true";
    },
    {
      storageKey: VISUAL_PROFILE_STORAGE_KEY,
      session: VISUAL_PROFILE_SESSION,
    },
  );
}

/** Normalize fonts and scroll position before taking screenshots. */
export async function stabilizeVisualPage(page: Page): Promise<void> {
  await page.addStyleTag({ content: VISUAL_TEST_STYLE });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.evaluate(async () => {
    await document.fonts.ready;
  });
}

/** Wait until recommendation content has rendered on a results page. */
export async function waitForResultsPage(page: Page): Promise<void> {
  await page.waitForLoadState("networkidle");
  await page
    .locator(".recommendation-list, .highlights-stack, .ranking-section")
    .first()
    .waitFor({
      timeout: 30_000,
    });
}

/** Wait until Aktuell highlights have finished their image lookup pass. */
export async function waitForAktuellHighlights(page: Page): Promise<void> {
  await page.getByRole("heading", { name: "Deine Highlights" }).waitFor({
    timeout: 30_000,
  });
  await page.locator(".highlight-tile").first().waitFor({ timeout: 30_000 });
  await page
    .locator(".highlight-tile-photo, .highlight-tile-accent-panel")
    .first()
    .waitFor({ timeout: 30_000 });
}

/** Wait until Entdecken highlights and the archive list are visible. */
export async function waitForEntdeckenRanking(page: Page): Promise<void> {
  await page.getByRole("heading", { name: "Im Archiv entdecken" }).waitFor({
    timeout: 30_000,
  });

  await page.getByRole("heading", { name: "Alle Empfehlungen" }).waitFor({
    timeout: 60_000,
  });

  const highlightsLoading = page.locator(".highlights-section-loading");
  if ((await highlightsLoading.count()) > 0) {
    await highlightsLoading.waitFor({ state: "detached", timeout: 60_000 });
  }

  const highlightSection = page.locator(".highlights-section");
  if ((await highlightSection.count()) > 0) {
    await highlightSection.locator(".highlight-tile").first().waitFor({
      timeout: 30_000,
    });
    await page.getByRole("heading", { name: "Liste verfeinern" }).waitFor({
      timeout: 30_000,
    });
  }

  await page
    .locator(".recommendation-list .recommendation-card, .ranking-section .highlight-tile")
    .first()
    .waitFor({ timeout: 30_000 });

  await page.waitForLoadState("networkidle");
}

/** Root shell used for viewport screenshots in visual regression. */
export function visualScreenshotTarget(page: Page) {
  return page.locator(".app-shell");
}
