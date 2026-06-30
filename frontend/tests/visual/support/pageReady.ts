import { expect, type Page } from "@playwright/test";

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

const ENTDECKEN_HIGHLIGHT_TILE_COUNT = 4;
const LAYOUT_STABLE_MS = 750;
const LAYOUT_STABLE_TIMEOUT_MS = 60_000;

/** Seed the temporary taste profile used by visual regression tests. */
export async function seedVisualProfileSession(page: Page): Promise<void> {
  await page.addInitScript(
    ({ storageKey, session, styleContent }) => {
      window.sessionStorage.setItem(storageKey, JSON.stringify(session));
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
      session: VISUAL_PROFILE_SESSION,
      styleContent: VISUAL_TEST_STYLE,
    },
  );
}

/** Normalize fonts and scroll position before taking screenshots. */
export async function stabilizeVisualPage(page: Page): Promise<void> {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.evaluate(async () => {
    await document.fonts.ready;
  });
  await waitForVisualLayoutStable(page);
}

/** Wait until the app shell height stops changing between async layout passes. */
export async function waitForVisualLayoutStable(
  page: Page,
  timeoutMs: number = LAYOUT_STABLE_TIMEOUT_MS,
): Promise<void> {
  const target = visualScreenshotTarget(page);
  let lastHeight = -1;
  let stableSince = Date.now();
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const height = await target.evaluate((element) => element.getBoundingClientRect().height);
    if (height > 0 && height === lastHeight) {
      if (Date.now() - stableSince >= LAYOUT_STABLE_MS) {
        return;
      }
    } else {
      lastHeight = height;
      stableSince = Date.now();
    }
    await page.waitForTimeout(100);
  }

  throw new Error(`Visual layout did not stabilize within ${timeoutMs}ms`);
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
  await waitForVisualLayoutStable(page);
}

/** Wait until Entdecken highlights and the archive list are fully settled. */
export async function waitForEntdeckenRanking(page: Page): Promise<void> {
  await page.getByRole("heading", { name: "Im Archiv entdecken" }).waitFor({
    timeout: 30_000,
  });

  await page.getByRole("heading", { name: "Alle Empfehlungen" }).waitFor({
    timeout: 60_000,
  });

  await page.locator(".highlights-section-loading").waitFor({
    state: "detached",
    timeout: 60_000,
  });

  await expect
    .poll(async () => page.locator(".highlights-stack .highlight-tile").count(), {
      timeout: 60_000,
    })
    .toBe(ENTDECKEN_HIGHLIGHT_TILE_COUNT);

  await page.getByRole("heading", { name: "Liste verfeinern" }).waitFor({
    timeout: 30_000,
  });

  await page
    .locator(".recommendation-list .recommendation-card, .ranking-section .highlight-tile")
    .first()
    .waitFor({ timeout: 30_000 });

  await page.locator('[data-visual-highlights="ready"]').waitFor({
    timeout: 60_000,
  });

  await page.locator('[data-visual-photo-slots="ready"]').waitFor({
    timeout: 60_000,
  });

  await expect
    .poll(
      async () => page.locator('[data-visual-photo-slots="ready"]').count(),
      { timeout: 10_000 },
    )
    .toBeGreaterThan(0);

  let photoSlotsReadySince = 0;
  const photoSlotsDeadline = Date.now() + 60_000;
  while (Date.now() < photoSlotsDeadline) {
    const readyCount = await page.locator('[data-visual-photo-slots="ready"]').count();
    if (readyCount > 0) {
      if (photoSlotsReadySince === 0) {
        photoSlotsReadySince = Date.now();
      }
      if (Date.now() - photoSlotsReadySince >= 500) {
        break;
      }
    } else {
      photoSlotsReadySince = 0;
    }
    await page.waitForTimeout(100);
  }
  if (photoSlotsReadySince === 0) {
    throw new Error("Entdecken photo slots did not stay ready");
  }

  await expect
    .poll(async () => page.locator(".highlight-tile-media-loading").count(), {
      timeout: 10_000,
    })
    .toBe(0);

  await page.waitForLoadState("networkidle");
  await waitForVisualLayoutStable(page);
}

/** Root shell used for viewport screenshots in visual regression. */
export function visualScreenshotTarget(page: Page) {
  return page.locator(".app-shell");
}
