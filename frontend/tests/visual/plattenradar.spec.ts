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
  { name: "aktuell", path: "/neuheiten" },
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

test("capture musikprofil wizard steps desktop", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.addInitScript(() => {
    window.sessionStorage.removeItem("plattenradar.profile-session.v1");
  });
  await mockMusikprofilApi(page);
  await page.goto("/musikprofil");
  await page.getByRole("heading", { name: "Welche groben Richtungen passen zu dir?" }).waitFor();
  await page.screenshot({
    path: path.join(screenshotDir, "musikprofil-step1-broad-desktop.png"),
    fullPage: true,
  });

  await page.getByRole("button", { name: "Rock & Alternative" }).click();
  await page.getByRole("button", { name: "Electronic & Dance" }).click();
  await page.getByRole("button", { name: "Detailstile auswählen" }).click();
  await page.getByRole("heading", { name: "Welche Detailstile sollen dein Profil prägen?" }).waitFor();
  await page.getByRole("button", { name: "Indie Rock" }).click();
  await page.getByRole("button", { name: "Elektronik" }).click();
  await page.getByRole("button", { name: "Indie Pop" }).click();
  await page.getByRole("button", { name: "Post-Punk" }).click();
  await page.getByRole("button", { name: "Dream Pop" }).click();
  await page.screenshot({
    path: path.join(screenshotDir, "musikprofil-step2-details-desktop.png"),
    fullPage: true,
  });

  await page.getByRole("button", { name: "Filter und Gewichtung" }).click();
  await page.getByRole("heading", { name: "Wie sollen Empfehlungen gewichtet werden?" }).waitFor();
  await page.getByText("Etwa 868 Alben im Archiv passen").waitFor();
  await page.screenshot({
    path: path.join(screenshotDir, "musikprofil-step3-filters-desktop.png"),
    fullPage: true,
  });
});

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
            overall_weight_alpha: 0.7,
            overall_weight_beta: 0.1,
            overall_weight_gamma: 0.2,
            sort_mode: "deterministic",
            serendipity: 0,
          },
        },
      }),
    );
  });
  await mockAktuellApi(page);
  await page.goto("/neuheiten");
  await page.waitForLoadState("domcontentloaded");
  await page.getByRole("heading", { name: "Deine Highlights" }).waitFor();
  await page.locator(".highlight-tile-photo").first().waitFor();
  await page.screenshot({
    path: path.join(screenshotDir, "aktuell-redesign.png"),
    fullPage: true,
  });
});

test("capture aktuell fine-tuning panel", async ({ page }) => {
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
            overall_weight_alpha: 0.7,
            overall_weight_beta: 0.1,
            overall_weight_gamma: 0.2,
            sort_mode: "deterministic",
            serendipity: 0,
          },
        },
      }),
    );
  });
  await mockAktuellApi(page);
  await page.goto("/neuheiten");
  await page.waitForLoadState("domcontentloaded");
  await page.getByRole("heading", { name: "Liste verfeinern" }).waitFor();
  const prelude = page.locator(".results-list-prelude");
  await prelude.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: path.join(screenshotDir, "aktuell-fine-tuning-context.png"),
    fullPage: false,
  });
  await prelude.screenshot({
    path: path.join(screenshotDir, "aktuell-fine-tuning-panel.png"),
  });
});

async function mockMusikprofilApi(page: Page): Promise<void> {
  await page.route("http://127.0.0.1:8000/v1/**", async (route) => {
    const url = new URL(route.request().url());
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
            label: "Post-Punk",
            broad_categories: ["Rock & Alternative"],
            example_artists: ["Dry Cleaning"],
          },
          {
            id: "C003",
            label: "Elektronik",
            broad_categories: ["Electronic & Dance"],
            example_artists: ["Low", "The Notwist"],
          },
          {
            id: "C004",
            label: "Indie Pop",
            broad_categories: ["Electronic & Dance"],
            example_artists: ["Japanese Breakfast"],
          },
          {
            id: "C005",
            label: "Dream Pop",
            broad_categories: ["Electronic & Dance"],
            example_artists: ["Beach House"],
          },
        ],
      });
      return;
    }
    if (url.pathname === "/v1/taste-communities/map") {
      await route.fulfill({
        contentType: "application/json",
        json: {
          nodes: [
            { id: "C001", x: 0.22, y: 0.34, size: 12, neighbors: ["C002", "C004"] },
            { id: "C002", x: 0.42, y: 0.58, size: 10, neighbors: ["C001", "C003"] },
            { id: "C003", x: 0.68, y: 0.44, size: 11, neighbors: ["C002", "C005"] },
            { id: "C004", x: 0.31, y: 0.72, size: 9, neighbors: ["C001", "C005"] },
            { id: "C005", x: 0.58, y: 0.78, size: 8, neighbors: ["C003", "C004"] },
          ],
        },
      });
      return;
    }
    if (url.pathname === "/v1/presets") {
      await route.fulfill({
        contentType: "application/json",
        json: [
          {
            id: "balanced",
            label: "Ausgewogen",
            subtitle: "Der beste Startpunkt",
            description: "Ausgewogene Gewichtung aus Stilpassung, Wertung und Album-Stilbreite.",
            icon: "sliders-horizontal",
            filter_settings: {
              rating_min: 6,
              rating_max: 10,
              score_min: 0.4,
              score_max: 1,
              overall_weight_alpha: 0.7,
              overall_weight_beta: 0.1,
              overall_weight_gamma: 0.2,
              sort_mode: "deterministic",
              serendipity: 0,
            },
          },
          {
            id: "precise",
            label: "Treffsicher",
            subtitle: "Nah an deinem Profil",
            description: "Sortiert stärker nach Stilpassung.",
            icon: "crosshair",
            filter_settings: {
              rating_min: 6,
              rating_max: 10,
              score_min: 0.4,
              score_max: 1,
              overall_weight_alpha: 0.8,
              overall_weight_beta: 0.05,
              overall_weight_gamma: 0.1,
              sort_mode: "deterministic",
              serendipity: 0,
            },
          },
        ],
      });
      return;
    }
    if (url.pathname === "/v1/taste-filter-ui") {
      await route.fulfill({
        contentType: "application/json",
        json: {
          default_preset_id: "balanced",
          preset_display: "Ausgewogen",
          preset_display_hint: "Wähle ein Preset als Startpunkt für Filter und Gewichtung.",
          groups: [],
        },
      });
      return;
    }
    if (url.pathname === "/v1/recommendations/archive") {
      await route.fulfill({
        contentType: "application/json",
        json: {
          total: 868,
          items: [],
        },
      });
      return;
    }
    await route.fulfill({ contentType: "application/json", json: {} });
  });
}

async function mockAktuellApi(page: Page): Promise<void> {
  const highlightThumb = buildHighlightThumbDataUri();
  await page.route("http://127.0.0.1:8000/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const imageMatch = url.pathname.match(/^\/v1\/artists\/([^/]+)\/image$/);
    if (
      url.pathname === "/v1/artists/images" &&
      route.request().method() === "POST"
    ) {
      const body = route.request().postDataJSON() as {
        artists?: Array<{ artist_mbid: string; artist_name?: string }>;
      };
      const artists = body.artists ?? [];
      await route.fulfill({
        contentType: "application/json",
        json: {
          items: artists.map((artist) => ({
            artist_mbid: artist.artist_mbid,
            image:
              artist.artist_mbid === "mbid-notwist" ||
              artist.artist_mbid === "mbid-big-thief"
                ? {
                    artist_mbid: artist.artist_mbid,
                    artist_name:
                      artist.artist_mbid === "mbid-notwist"
                        ? "The Notwist"
                        : "Big Thief",
                    thumbnail_url: highlightThumb,
                    attribution_text:
                      "Demo-Foto, CC BY 4.0 via Wikimedia Commons (Playwright-Mock)",
                    license: "CC BY 4.0",
                    source_url: "https://commons.wikimedia.org/wiki/File:Demo.jpg",
                  }
                : null,
          })),
        },
      });
      return;
    }
    if (imageMatch !== null) {
      const artistMbid = decodeURIComponent(imageMatch[1] ?? "");
      if (artistMbid === "mbid-notwist" || artistMbid === "mbid-big-thief") {
        await route.fulfill({
          contentType: "application/json",
          json: {
            artist_mbid: artistMbid,
            artist_name: artistMbid === "mbid-notwist" ? "The Notwist" : "Big Thief",
            thumbnail_url: highlightThumb,
            attribution_text:
              "Demo-Foto, CC BY 4.0 via Wikimedia Commons (Playwright-Mock)",
            license: "CC BY 4.0",
            source_url: "https://commons.wikimedia.org/wiki/File:Demo.jpg",
          },
        });
        return;
      }
      await route.fulfill({
        contentType: "application/json",
        status: 404,
        json: { detail: "No licensed artist image is available." },
      });
      return;
    }
    if (url.pathname === "/v1/recommendations/new-reviews") {
      await route.fulfill({
        contentType: "application/json",
        json: {
          total: 6,
          items: [
            apiRecommendation(
              1,
              "The Notwist",
              "Vertigo Days",
              2021,
              8,
              0.88,
              [
                ["C001", "Indie", 0.9, true],
                ["C002", "Elektronik", 0.72, true],
                ["C004", "Melancholisch", 0.45, false],
              ],
              undefined,
              "mbid-notwist",
            ),
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
              undefined,
              "mbid-big-thief",
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
    if (url.pathname === "/v1/taste-communities/map") {
      await route.fulfill({
        contentType: "application/json",
        json: {
          nodes: [
            { id: "C001", x: 0.25, y: 0.35, size: 12, neighbors: ["C002"] },
            { id: "C002", x: 0.62, y: 0.48, size: 10, neighbors: ["C001", "C003"] },
            { id: "C003", x: 0.48, y: 0.74, size: 9, neighbors: ["C002"] },
          ],
        },
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
  artistMbid?: string,
): Record<string, unknown> {
  return {
    rank,
    artist,
    album,
    artist_mbid: artistMbid ?? null,
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

function buildHighlightThumbDataUri(): string {
  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="140" viewBox="0 0 400 140">' +
    '<rect fill="#d8c8b4" width="400" height="140"/>' +
    '<text x="200" y="74" text-anchor="middle" fill="#4f4034" font-family="sans-serif" font-size="15">Künstlerfoto</text>' +
    "</svg>";
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}
