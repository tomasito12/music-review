import path from "node:path";
import { fileURLToPath } from "node:url";

import { test } from "@playwright/test";

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
