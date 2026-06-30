import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:5173";
const isCi = Boolean(process.env.CI);

export default defineConfig({
  testDir: "./tests/visual",
  timeout: isCi ? 120_000 : 60_000,
  fullyParallel: false,
  retries: isCi ? 2 : 0,
  reporter: isCi ? [["list"], ["github"]] : "list",
  snapshotPathTemplate: "{testDir}/reference/{arg}{ext}",
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.05,
      animations: "disabled",
      timeout: 15_000,
    },
  },
  use: {
    ...devices["Desktop Chrome"],
    baseURL,
    locale: "de-DE",
    timezoneId: "Europe/Berlin",
    colorScheme: "light",
  },
  webServer: {
    command: "pnpm dev --host 127.0.0.1 --port 5173",
    url: baseURL,
    reuseExistingServer: true,
    timeout: 120_000,
  },
  projects: [
    {
      name: "mock",
      testMatch: /^(?!.*live-screenshots).*\.spec\.ts$/,
    },
    {
      name: "live",
      testMatch: /live-screenshots\.spec\.ts$/,
      retries: isCi ? 2 : 0,
      use: {
        viewport: { width: 1280, height: 900 },
      },
    },
  ],
});
