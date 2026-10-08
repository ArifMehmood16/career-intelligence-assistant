import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";

if (!process.env.E2E_DATABASE_URL) {
  throw new Error("Provide a dedicated loopback E2E_DATABASE_URL ending _e2e.");
}

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 20_000 },
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:13001",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      name: "Isolated SQL API",
      command: "../backend/.venv/bin/python start-api.py",
      url: "http://127.0.0.1:18002/api/ready",
      reuseExistingServer: false,
      gracefulShutdown: { signal: "SIGTERM", timeout: 10_000 },
      timeout: 60_000,
    },
    {
      name: "Real frontend proxy",
      command: "bun run dev",
      cwd: resolve(import.meta.dirname, "../frontend"),
      url: "http://127.0.0.1:13001",
      env: {
        WEB_PORT: "13001",
        WEB_ORIGIN: "http://127.0.0.1:13001",
        API_BASE_URL: "http://127.0.0.1:18002",
      },
      reuseExistingServer: false,
      gracefulShutdown: { signal: "SIGTERM", timeout: 10_000 },
      timeout: 60_000,
    },
  ],
});
