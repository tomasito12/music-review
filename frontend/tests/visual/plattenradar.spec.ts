import path from "node:path";
import { fileURLToPath } from "node:url";

import { test, type Page } from "@playwright/test";

const screenshotDir = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../screenshots",
);

const routes = [
  { name: "willkommen", path: "/" },
  { name: "musikprofil", path: "/musikprofil" },
  { name: "entdecken", path: "/entdecken" },
  { name: "aktuell", path: "/aktuell" },
  { name: "playlists", path: "/playlists" },
] as const;

for (const route of routes) {
  test(`capture ${route.name} screen`, async ({ page }) => {
    await page.goto(route.path);
    await page.waitForLoadState("domcontentloaded");
    await page.screenshot({
      path: path.join(screenshotDir, `${route.name}.png`),
      fullPage: true,
    });
  });
}

test("capture entdecken mobile navigation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/entdecken");
  await page.waitForLoadState("domcontentloaded");
  await page.screenshot({
    path: path.join(screenshotDir, "entdecken-mobile.png"),
    fullPage: true,
  });
});

test("capture aktuell redesign reference screen", async ({ page }) => {
  await page.addInitScript(() => {
    window.sessionStorage.setItem(
      "plattenradar.profile-session.v1",
      JSON.stringify({
        presetId: "balanced",
        presetLabel: "Ausgewogen",
        savedAt: "2026-06-27T12:00:00.000Z",
        profile: {
          name: "Temporäres Musikprofil",
          selected_communities: ["C001", "C002", "C003"],
          community_weights_raw: { C001: 0.5, C002: 0.5, C003: 0.5 },
          filter_settings: {
            rating_min: 6,
            rating_max: 10,
            score_min: 0.4,
            score_max: 1,
            overall_weight_alpha: 0.5,
            overall_weight_beta: 0.25,
            overall_weight_gamma: 0.25,
            community_spectrum_crossover: 0.5,
            sort_mode: "deterministic",
            serendipity: 0,
          },
        },
      }),
    );
  });
  await mockAktuellApi(page);
  await page.goto("/aktuell");
  await page.waitForLoadState("domcontentloaded");
  await page.getByRole("heading", { name: /neue Rezensionen liegen nah/i }).waitFor();
  await page.screenshot({
    path: path.join(screenshotDir, "aktuell-redesign.png"),
    fullPage: true,
  });
});

async function mockAktuellApi(page: Page): Promise<void> {
  await page.route("http://127.0.0.1:8000/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/v1/recommendations/new-reviews") {
      await route.fulfill({
        contentType: "application/json",
        json: {
          total: 6,
          items: [
            apiRecommendation(1, "The Notwist", "Vertigo Days", 2021, 8, 0.88, [
              ["C001", "Indie", 0.9, true],
              ["C002", "Elektronik", 0.72, true],
              ["C004", "Melancholisch", 0.45, false],
            ]),
            apiRecommendation(
              2,
              "Big Thief",
              "Dragon New Warm Mountain I Believe In You",
              2022,
              8,
              0.82,
              [
                ["C001", "Indie Folk", 0.84, true],
                ["C005", "Songwriter", 0.58, false],
              ],
            ),
            apiRecommendation(3, "Japanese Breakfast", "Jubilee", 2021, 7, 0.74, [
              ["C003", "Indie Pop", 0.76, true],
              ["C006", "Dream Pop", 0.44, false],
            ]),
            apiRecommendation(4, "Dry Cleaning", "New Long Leg", 2021, 8, 0.7, [
              ["C007", "Post-Punk", 0.62, false],
              ["C001", "Indie Rock", 0.52, true],
            ]),
            apiRecommendation(5, "Low", "HEY WHAT", 2021, 9, 0.68, [
              ["C008", "Experimental", 0.65, false],
              ["C002", "Elektronik", 0.5, true],
            ]),
            apiRecommendation(6, "Wednesday", "Rat Saw God", 2023, 8, 0.64, [
              ["C001", "Indie Rock", 0.67, true],
              ["C009", "Country", 0.3, false],
            ]),
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
            example_artists: ["The Notwist", "Big Thief"],
          },
          {
            id: "C002",
            label: "Elektronik",
            broad_categories: ["Electronic & Dance"],
            example_artists: ["The Notwist", "Low"],
          },
          {
            id: "C003",
            label: "Indie Pop",
            broad_categories: ["Pop & Indie"],
            example_artists: ["Japanese Breakfast"],
          },
        ],
      });
      return;
    }
    if (url.pathname === "/v1/presets") {
      await route.fulfill({
        contentType: "application/json",
        json: [],
      });
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
    await route.fulfill({ contentType: "application/json", json: {} });
  });
}

function apiRecommendation(
  rank: number,
  artist: string,
  album: string,
  year: number,
  rating: number,
  score: number,
  tags: Array<[string, string, number, boolean]>,
  releaseDate?: string,
): Record<string, unknown> {
  return {
    rank,
    artist,
    album,
    year,
    release_date: releaseDate ?? `${year}-06-15`,
    rating,
    overall_score: score,
    labels: "Demo Label",
    text_excerpt:
      "Ein Fundstück mit genug Ecken, Wärme und Nachhall, um nicht nach zwei Wochen wieder aus dem Kopf zu verschwinden.",
    url: "https://www.plattentests.de/",
    source: "new_reviews",
    matched_tags: tags.map(([id, label, affinity, matched]) => ({
      id,
      label,
      affinity,
      matched,
    })),
  };
}
