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
    baseURL,
    locale: "de-DE",
    timezoneId: "Europe/Berlin",
    deviceScaleFactor: 1,
    colorScheme: "light",
    ...devices["Desktop Chrome"],
  },
  projects: [
    {
      name: "mock",
      testMatch: /^(?!.*live-screenshots).*\.spec\.ts$/,
      webServer: {
        command: "pnpm dev --host 127.0.0.1 --port 5173",
        url: baseURL,
        reuseExistingServer: !isCi,
        timeout: 120_000,
      },
    },
    {
      name: "live",
      testMatch: /live-screenshots\.spec\.ts$/,
      retries: isCi ? 2 : 0,
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 900 },
      },
    },
  ],
});
