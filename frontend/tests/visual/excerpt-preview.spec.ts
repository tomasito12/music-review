import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test, type Page } from "@playwright/test";

const screenshotDir = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../screenshots",
);

const longExcerpt =
  "Ernüchternd: Beim ESC 2026 ist Luxemburg schon im zweiten Halbfinale ausgeschieden – bloß zwei Jahre, nachdem es erst wieder am Mega-Wettbewerb teilnehmen durfte. Wie schon in der Rezension zu Lighthouse erörtert, dem Debüt der Lëtzebuerger Musikerin Jana Bahrich und ihres Projekts Francis Of Delirium, klingt das Album nach vielem – jedoch alles andere als austauschbar.";

const profileSession = {
  presetId: "balanced",
  presetLabel: "Ausgewogen",
  savedAt: "2026-06-27T12:00:00.000Z",
  profile: {
    name: "Temporäres Musikprofil",
    selected_communities: ["C001", "C112", "C015"],
    community_weights_raw: { C001: 0.5, C112: 0.5, C015: 0.5 },
    filter_settings: {
      rating_min: 6,
      rating_max: 10,
      score_min: 0.4,
      score_max: 1,
      overall_weight_alpha: 0.5,
      overall_weight_beta: 0.25,
      overall_weight_gamma: 0.25,
      sort_mode: "deterministic",
      serendipity: 0,
    },
  },
};

for (const route of [
  { name: "entdecken-excerpt-fix", path: "/entdecken" },
  { name: "aktuell-excerpt-fix", path: "/aktuell" },
] as const) {
  test(`capture ${route.name} excerpt screen`, async ({ page }) => {
    await seedProfileSession(page);
    await mockRecommendationApi(page);
    await page.goto(route.path);
    await page.waitForLoadState("networkidle");
    await page.locator(".excerpt").first().waitFor({ timeout: 30_000 });
    await page.screenshot({
      path: path.join(screenshotDir, `${route.name}.png`),
      fullPage: true,
    });
  });
}

test("excerpt previews end with [...] when truncated", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 900 });
  await seedProfileSession(page);
  await mockRecommendationApi(page);
  await page.goto("/entdecken");
  await page.waitForLoadState("networkidle");
  await page.locator(".excerpt").first().waitFor({ timeout: 30_000 });

  const excerptStates = await page.locator(".excerpt").evaluateAll((nodes) =>
    nodes.map((node) => {
      const text = node.textContent ?? "";
      const styles = window.getComputedStyle(node);
      const lineHeight = Number.parseFloat(styles.lineHeight);
      const maxLines = 3;
      const exceedsThreeLines =
        Number.isFinite(lineHeight) &&
        lineHeight > 0 &&
        node.scrollHeight > lineHeight * maxLines + 0.5;
      return {
        text,
        endsWithMarker: text.endsWith("[...]"),
        exceedsThreeLines,
      };
    }),
  );

  const truncated = excerptStates.filter(
    (entry) => entry.exceedsThreeLines || entry.endsWithMarker,
  );
  const truncatedWithoutMarker = truncated.filter((entry) => !entry.endsWithMarker);

  expect(truncatedWithoutMarker).toEqual([]);
  expect(truncated.some((entry) => entry.endsWithMarker)).toBe(true);
});

async function seedProfileSession(page: Page): Promise<void> {
  await page.addInitScript((session) => {
    window.sessionStorage.setItem(
      "plattenradar.profile-session.v1",
      JSON.stringify(session),
    );
  }, profileSession);
}

async function mockRecommendationApi(page: Page): Promise<void> {
  await page.route("http://127.0.0.1:8000/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/v1/recommendations/archive") {
      await route.fulfill({
        contentType: "application/json",
        json: {
          source: "archive",
          total: 3,
          limit: 20,
          offset: 0,
          items: [
            recommendation(1, "Francis Of Delirium", "Lighthouse"),
            recommendation(2, "Travis Scott", "Utopia"),
            recommendation(3, "Big Thief", "Dragon New Warm Mountain I Believe In You"),
          ],
        },
      });
      return;
    }
    if (url.pathname === "/v1/recommendations/new-reviews") {
      await route.fulfill({
        contentType: "application/json",
        json: {
          source: "new_reviews",
          total: 3,
          limit: 20,
          offset: 0,
          items: [
            recommendation(1, "The Notwist", "Vertigo Days"),
            recommendation(2, "Wednesday", "Rat Saw God"),
            recommendation(3, "Low", "HEY WHAT"),
          ],
        },
      });
      return;
    }
    if (url.pathname === "/v1/taste-communities") {
      await route.fulfill({
        contentType: "application/json",
        json: [
          {
            id: "C001",
            label: "Indie Rock",
            broad_categories: ["Rock & Alternative"],
            example_artists: ["The Notwist"],
          },
          {
            id: "C112",
            label: "Elektronik",
            broad_categories: ["Electronic & Dance"],
            example_artists: ["Low"],
          },
          {
            id: "C015",
            label: "Indie Pop",
            broad_categories: ["Pop & Indie"],
            example_artists: ["Big Thief"],
          },
        ],
      });
      return;
    }
    if (url.pathname === "/v1/presets") {
      await route.fulfill({ contentType: "application/json", json: [] });
      return;
    }
    if (url.pathname === "/v1/taste-filter-ui") {
      await route.fulfill({
        contentType: "application/json",
        json: {
          default_preset_id: "balanced",
          preset_display: "Ausgewogen",
          preset_display_hint: "Guter Startpunkt für neue Rezensionen.",
          groups: [],
        },
      });
      return;
    }
    if (
      url.pathname === "/v1/artists/images" &&
      route.request().method() === "POST"
    ) {
      await route.fulfill({
        contentType: "application/json",
        json: { items: [] },
      });
      return;
    }
    await route.fulfill({ contentType: "application/json", json: {} });
  });
}

function recommendation(
  rank: number,
  artist: string,
  album: string,
): Record<string, unknown> {
  return {
    rank,
    review_id: rank,
    artist,
    album,
    artist_mbid: null,
    year: 2024,
    release_date: "2024-06-15",
    rating: 8,
    overall_score: 0.82,
    labels: "Demo Label",
    text_excerpt: longExcerpt,
    text_excerpt_continues: true,
    url: "https://www.plattentests.de/",
    source: "archive",
    matched_tags: [
      { id: "C001", label: "Indie Rock", affinity: 0.8, matched: true },
    ],
  };
}
