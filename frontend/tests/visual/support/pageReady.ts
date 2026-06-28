import type { Page } from "@playwright/test";

import {
  VISUAL_PROFILE_SESSION,
  VISUAL_PROFILE_STORAGE_KEY,
} from "./visualProfile";

/** Seed the temporary taste profile used by visual regression tests. */
export async function seedVisualProfileSession(page: Page): Promise<void> {
  await page.addInitScript(
    ({ storageKey, session }) => {
      window.sessionStorage.setItem(storageKey, JSON.stringify(session));
    },
    {
      storageKey: VISUAL_PROFILE_STORAGE_KEY,
      session: VISUAL_PROFILE_SESSION,
    },
  );
}

/** Wait until recommendation content has rendered on a results page. */
export async function waitForResultsPage(page: Page): Promise<void> {
  await page.waitForLoadState("networkidle");
  await page.locator(".recommendation-list, .highlights-stack").first().waitFor({
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
    .locator(".highlight-tile-photo, .highlight-tile-text-only")
    .first()
    .waitFor({ timeout: 30_000 });
}

/** Wait until Entdecken rank 1 and the archive list are visible. */
export async function waitForEntdeckenRanking(page: Page): Promise<void> {
  await page.getByRole("heading", { name: "Alle Empfehlungen" }).waitFor({
    timeout: 30_000,
  });
  await page.locator(".entdecken-lead-entry, .recommendation-list").first().waitFor({
    timeout: 30_000,
  });
}
