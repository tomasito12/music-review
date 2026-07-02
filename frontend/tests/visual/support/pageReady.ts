import { expect, type Page } from "@playwright/test";

import {
  VISUAL_PROFILE_SESSION,
  VISUAL_PROFILE_STORAGE_KEY,
} from "./visualProfile";

const VISUAL_TEST_STYLE = `
  html[data-visual-test] :where(body, button, input, select, textarea, p, li, span, a) {
    font-family: "Liberation Sans", Arial, Helvetica, sans-serif !important;
    text-rendering: geometricPrecision;
    -webkit-font-smoothing: antialiased;
  }
  html[data-visual-test] :where(h1, h2, h3, .highlight-tile-title) {
    font-family: "Liberation Serif", "Times New Roman", Times, serif !important;
    text-rendering: geometricPrecision;
  }
  html[data-visual-test] .results-load-more {
    visibility: hidden !important;
  }
  html[data-visual-test] .artist-image-source {
    display: none !important;
  }
  html[data-visual-test] :where(.highlight-tile-photo, .recommendation-card-thumbnail, .playlist-artist-mosaic-tile) {
    object-fit: cover;
    background: #d8c8b4;
  }
`;

const LAYOUT_STABLE_MS = 1_500;
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

/** Wait until the app marks the current results page as screenshot-ready. */
export async function waitForVisualPageReady(page: Page): Promise<void> {
  await page.locator('[data-visual-page-ready="true"]').waitFor({
    timeout: 60_000,
  });
  await page.locator('[data-visual-highlights="ready"]').waitFor({
    timeout: 60_000,
  });
}

/** Normalize scroll position and wait for a stable layout before screenshots. */
export async function stabilizeVisualPage(page: Page): Promise<void> {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.evaluate(async () => {
    await document.fonts.ready;
  });
  await waitForVisualLayoutStable(page);
}

/** Wait until the screenshot target height stops changing. */
export async function waitForVisualLayoutStable(
  page: Page,
  timeoutMs: number = LAYOUT_STABLE_TIMEOUT_MS,
  probe = visualLayoutProbe(page),
): Promise<void> {
  const target = probe;
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

/** Wait until Aktuell highlights and ranking have finished loading. */
export async function waitForAktuellHighlights(page: Page): Promise<void> {
  await page.getByRole("heading", { name: "Deine Highlights" }).waitFor({
    timeout: 30_000,
  });
  await page.locator(".highlight-tile").first().waitFor({ timeout: 30_000 });
  await page
    .locator(".highlight-tile-photo, .highlight-tile-accent-panel")
    .first()
    .waitFor({ timeout: 30_000 });
  await waitForVisualPageReady(page);
  await page.locator('[data-visual-images="ready"]').waitFor({ timeout: 60_000 });
  await page.waitForLoadState("networkidle");
  await waitForVisualLayoutStable(page);
}

/** Wait until Entdecken highlights and ranking have finished loading. */
export async function waitForEntdeckenRanking(page: Page): Promise<void> {
  await page.getByRole("heading", { name: "Im Archiv entdecken" }).waitFor({
    timeout: 30_000,
  });
  await page.locator(".highlights-section-loading").waitFor({
    state: "detached",
    timeout: 60_000,
  });
  await waitForVisualPageReady(page);
  await page.locator('[data-visual-photo-slots="ready"]').waitFor({
    timeout: 60_000,
  });
  await expect
    .poll(async () => page.locator(".highlight-tile-media-loading").count(), {
      timeout: 10_000,
    })
    .toBe(0);
  await page.waitForLoadState("networkidle");
  await waitForVisualLayoutStable(page);
}

/** Wait until the playlist generator form is ready for screenshots. */
export async function waitForPlaylistForm(page: Page): Promise<void> {
  await page.getByRole("heading", { name: "Neue Playlist erzeugen" }).waitFor({
    timeout: 30_000,
  });
  await page.getByRole("button", { name: "Playlist vorbereiten" }).waitFor({
    timeout: 30_000,
  });
  await page.locator('[data-visual-playlist-ready="form"]').waitFor({
    timeout: 30_000,
  });
  await page.waitForLoadState("networkidle");
  await waitForVisualLayoutStable(page, LAYOUT_STABLE_TIMEOUT_MS, visualPlaylistLayoutProbe(page));
}

/** Wait until playlist results and artist thumbnails have finished loading. */
export async function waitForPlaylistResults(page: Page): Promise<void> {
  await page.locator(".playlist-results").waitFor({ timeout: 30_000 });
  await page.locator('[data-visual-images="ready"]').waitFor({ timeout: 60_000 });
  await page.locator('[data-visual-playlist-ready="results"]').waitFor({
    timeout: 30_000,
  });
  await page.waitForLoadState("networkidle");
  await waitForVisualLayoutStable(page, LAYOUT_STABLE_TIMEOUT_MS, visualPlaylistLayoutProbe(page));
}

/** Generate a playlist from the current form state in visual tests. */
export async function generatePlaylistFromForm(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Playlist vorbereiten" }).click();
  await waitForPlaylistResults(page);
}

/** Fixed viewport clip used for live visual regression screenshots. */
export function visualScreenshotClip(page: Page): {
  x: number;
  height: number;
  width: number;
} {
  const viewport = page.viewportSize();
  if (viewport === null) {
    throw new Error("Viewport size is not set");
  }
  return {
    x: 0,
    y: 0,
    width: viewport.width,
    height: viewport.height,
  };
}

/** Main results surface polled until layout stops shifting before capture. */
export function visualLayoutProbe(page: Page) {
  return page.locator(".results-page");
}

/** Playlist page surface polled until layout stops shifting before capture. */
export function visualPlaylistLayoutProbe(page: Page) {
  return page.locator(".playlist-page");
}

/** Assert that two consecutive captures would have the same height. */
export async function assertScreenshotLayoutStable(
  page: Page,
  probe = visualLayoutProbe(page),
): Promise<void> {
  const target = probe;
  const firstHeight = await target.evaluate((element) => element.getBoundingClientRect().height);
  await page.waitForTimeout(300);
  await waitForVisualLayoutStable(page, LAYOUT_STABLE_TIMEOUT_MS, probe);
  const secondHeight = await target.evaluate((element) => element.getBoundingClientRect().height);
  expect(firstHeight).toBe(secondHeight);
}