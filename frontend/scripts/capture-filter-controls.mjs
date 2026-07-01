import { chromium } from "@playwright/test";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
await page.addInitScript(() => {
  sessionStorage.setItem(
    "plattenradar.profile-session.v1",
    JSON.stringify({
      presetId: "balanced",
      presetLabel: "Ausgewogen",
      savedAt: "2026-06-29T12:00:00.000Z",
      profile: {
        name: "Demo",
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
await page.goto("http://127.0.0.1:5173/entdecken");
await page.waitForLoadState("networkidle");
await page.getByText("Filter und Gewichtung anpassen").click();
for (const label of [
  "Filterung anpassen",
  "Gewichtung anpassen",
  "Gewichte pro Stil-Schwerpunkt",
]) {
  await page.getByRole("button", { name: label }).click().catch(async () => {
    await page.locator("summary").filter({ hasText: new RegExp(`^${label}$`) }).click();
  });
}
await page.locator(".filter-advanced").scrollIntoViewIfNeeded();
await page.waitForTimeout(400);
await page
  .locator(".filter-advanced")
  .screenshot({ path: "screenshots/filter-controls-after.png" });
await browser.close();
console.log("saved screenshots/filter-controls-after.png");
