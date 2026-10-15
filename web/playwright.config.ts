import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests",
  testMatch: "browser.spec.ts",
  workers: 1,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:3004",
    channel: "msedge",
    headless: true,
    viewport: { width: 1440, height: 1000 },
  },
  webServer: {
    command: "npm run preview:local",
    env: { PORT: "3004" },
    url: "http://127.0.0.1:3004",
    reuseExistingServer: false,
    timeout: 45000,
  },
  reporter: [["list"], ["json", { outputFile: "test-results/results.json" }]],
});
