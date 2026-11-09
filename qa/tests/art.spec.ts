import { test, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';

test('生成した景観8点をローカル配信し狭幅の見取り図も読める', async ({ page, request }) => {
  const manifest = JSON.parse(await fs.readFile(path.resolve('../artifacts/art-manifest.json'), 'utf8'));
  const assets: { name: string; bytes: number }[] = [];
  for (const asset of manifest.assets) {
    for (const file of asset.files) {
      const url = '/' + file.path.replace('frontend/public/', '');
      const response = await request.get(url);
      expect(response.ok(), url).toBeTruthy();
      expect(response.headers()['content-type']).toContain('image/webp');
      const body = await response.body();
      expect(body.length).toBe(file.bytes);
      assets.push({ name: url, bytes: body.length });
    }
  }
  const external: string[] = [];
  page.on('request', request => {
    const url = new URL(request.url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) external.push(url.origin);
  });
  await page.goto('/');
  await expect(page.locator('.hero-picture img')).toBeVisible();
  await expect.poll(() => page.locator('.hero-picture img').evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBeTruthy();
  await page.getByText('街の見取り図をひらく', { exact: false }).click();
  await page.locator('.city-map').scrollIntoViewIfNeeded();
  for (const width of [320, 390, 430]) {
    await page.setViewportSize({ width, height: 844 });
    await expect(page.locator('.city-map')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
    const failed = await page.locator('.city-map img').evaluateAll(images => images.filter(image => !(image as HTMLImageElement).complete || (image as HTMLImageElement).naturalWidth === 0).length);
    expect(failed).toBe(0);
  }
  expect(external).toEqual([]);
  await fs.writeFile(path.resolve('../artifacts/art-delivery-check.json'), JSON.stringify({ assets, externalRequests: external, mobileWidths: [320, 390, 430] }, null, 2));
});
