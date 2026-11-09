import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const { chromium, expect } = createRequire(path.join(root, 'qa/package.json'))('@playwright/test');
const browser = await chromium.launch({ channel: 'msedge', headless: true });
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, locale: 'ja-JP' });
  const origin = 'http://127.0.0.1:8081';
  const login = await context.request.post(origin + '/api/login', { headers: { Origin: origin }, data: { username: 'aoi', password: 'aoi-local-2026' } });
  if (!login.ok()) throw new Error('Synthetic account could not log in');
  const page = await context.newPage();
  await page.goto(origin);
  await expect(page.locator('.post-card').first()).toBeVisible();
  await expect.poll(() => page.locator('.post-card img').first().evaluate(image => image.complete && image.naturalWidth > 0)).toBe(true);
  for (const photo of await page.locator('.post-card img').all()) {
    await photo.scrollIntoViewIfNeeded();
    await expect.poll(() => photo.evaluate(image => image.complete && image.naturalWidth > 0)).toBe(true);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(root, 'community/artifacts/browser/final-desktop.png'), fullPage: true });
} finally { await browser.close(); }
