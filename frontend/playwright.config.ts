import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:5173";
const isCi = Boolean(process.env.CI);

export default defineConfig({
  testDir: "./tests/visual",
  timeout: 60_000,
  fullyParallel: false,
  reporter: isCi ? [["list"], ["github"]] : "list",
  snapshotPathTemplate: "{testDir}/reference/{arg}{ext}",
  use: {
    baseURL,
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
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 900 },
      },
    },
  ],
});
