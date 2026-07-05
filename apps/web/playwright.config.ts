import { defineConfig } from '@playwright/test';

// Local containers pass PW_LOCAL_CHROMIUM (e.g. /opt/pw-browsers/chromium) to
// point Playwright at the pre-installed browser build. CI omits it and relies
// on `npx playwright install chromium`. This env seam is the only portable way
// to select the browser binary — no container-specific path is committed here.
const localChromium = process.env.PW_LOCAL_CHROMIUM;

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    ...(localChromium
      ? { launchOptions: { executablePath: localChromium } }
      : {}),
  },
  webServer: [
    {
      command: 'bash ./e2e/serve-api.sh',
      url: 'http://localhost:8000/health',
      timeout: 60000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
    },
  ],
});
