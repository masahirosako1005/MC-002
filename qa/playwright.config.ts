import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  outputDir: '../artifacts/browser-results',
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  reporter: [['list'], ['json', { outputFile: '../artifacts/browser-tests.json' }]],
  use: {
    baseURL: process.env.APP_URL || 'http://127.0.0.1:8080',
    browserName: 'chromium',
    channel: 'msedge',
    viewport: { width: 390, height: 844 },
    locale: 'ja-JP',
    timezoneId: 'Asia/Tokyo',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
});
