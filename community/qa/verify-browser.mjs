import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const require = createRequire(path.join(root, 'qa/package.json'));
const { chromium, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;
const output = path.join(root, 'community/artifacts', process.env.KO_BROWSER_OUTPUT || 'browser');
const baseURL = process.env.KO_URL || 'http://127.0.0.1:8081';
await fs.mkdir(output, { recursive: true });
const results = [];
const external = [];
const errors = [];
const browser = await chromium.launch({ channel: 'msedge', headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1050 }, locale: 'ja-JP', timezoneId: 'Asia/Tokyo',
});
await context.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (!['127.0.0.1', 'localhost'].includes(url.hostname)) {
    external.push(url.origin);
    await route.abort();
  } else await route.continue();
});
const page = await context.newPage();
page.on('pageerror', error => errors.push(error.message));

async function check(name, action) {
  const start = Date.now();
  try {
    await action();
    results.push({ name, status: 'passed', milliseconds: Date.now() - start });
    console.log(`PASS ${name}`);
  } catch (error) {
    results.push({ name, status: 'failed', message: String(error.message).slice(0, 1800) });
    await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true });
    throw error;
  }
}
async function clickVisible(name, scope = page) {
  const buttons = scope.getByRole('button', { name, exact: typeof name === 'string' });
  await expect.poll(async () => {
    for (let i = 0; i < await buttons.count(); i++) if (await buttons.nth(i).isVisible()) return true;
    return false;
  }, { timeout: 15000 }).toBe(true);
  for (let i = 0; i < await buttons.count(); i++) {
    if (await buttons.nth(i).isVisible()) { await buttons.nth(i).click(); return; }
  }
  throw new Error(`Visible button not found: ${name}`);
}
async function login(username) {
  const names = { aoi: '藤沢 葵', ren: '高橋 蓮', mio: '小野 美緒' };
  await page.goto(baseURL);
  await page.getByLabel('アカウント名', {exact:true}).fill(username);
  await page.getByLabel('パスワード', { exact: true }).fill(`${username}-local-2026`);
  await page.getByRole('button', { name: 'ログイン', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).not.toContainText('好きな景色');
  await expect(page.locator('.post-card').first()).toBeVisible({ timeout: 20000 });
}
async function logout() {
  const session = await (await context.request.get(`${baseURL}/api/me`)).json();
  const response = await context.request.post(`${baseURL}/api/logout`, {
    headers: { Origin: baseURL, 'X-CSRF-Token': session.csrf_token }, data: {},
  });
  assert.equal(response.status(), 200);
}
async function jsonAPI(route, method = 'GET', data) {
  const session = await (await context.request.get(`${baseURL}/api/me`)).json();
  const response = await context.request.fetch(`${baseURL}/api${route}`, {
    method, headers: { Origin: baseURL, 'X-CSRF-Token': session.csrf_token }, data,
  });
  assert(response.ok(), `${method} ${route}: ${response.status()} ${await response.text()}`);
  return response.json();
}
async function axe(name) {
  const report = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  await fs.writeFile(path.join(output, `axe-${name}.json`), JSON.stringify(report.violations, null, 2));
  assert.equal(report.violations.length, 0, JSON.stringify(report.violations.map(v => ({ id: v.id, impact: v.impact, targets: v.nodes.map(n => n.target) }))));
}
async function noOverflow() {
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Horizontal document overflow');
}

async function openPreferences() {
  const options = page.getByRole('button', { name: '自分の好み', exact: true });
  let available = false;
  for (let i = 0; i < await options.count(); i++) if (await options.nth(i).isVisible()) available = true;
  if (!available) {
    await clickVisible(/アカウントを切り替える$/);
    await clickVisible('自分の好みを確認する');
  } else await clickVisible('自分の好み');
}

let postedId, proposalId, groupId;
try {
  await check('real login, desktop feed, local photo assets and accessibility', async () => {
    await login('aoi');
    // Remove only this script's prior synthetic post when retrying an interrupted run.
    const earlier = await jsonAPI('/communities/peers/feed');
    for (const post of earlier.items) {
      if (post.can_edit && post.body === '森を歩いたあと、窓辺でコーヒー。次はみんなで来たい。') await jsonAPI(`/posts/${post.id}`, 'DELETE', {});
    }
    await page.reload();
    await expect(page.locator('.post-card img').first()).toBeVisible();
    await expect.poll(() => page.locator('.post-card img').first().evaluate(image => image.complete && image.naturalWidth > 0)).toBe(true);
    await noOverflow();
    await axe('desktop-feed');
    await page.screenshot({ path: path.join(output, 'feed-desktop.png'), fullPage: true });
  });
  await check('mobile feed, readable layout and accessibility', async () => {
    await page.setViewportSize({ width: 390, height: 844 });
    await noOverflow();
    await axe('mobile-feed');
    await page.screenshot({ path: path.join(output, 'feed-mobile.png'), fullPage: true });
  });
  await check('photo upload, actual local analysis, corrected tags and publication', async () => {
    await clickVisible(/どんな旅をしてきましたか？/);
    const dialog = page.getByRole('dialog');
    await dialog.locator('input[type=file]').setInputFiles(path.join(root, 'community/assets/coffee.png'));
    await expect(dialog.getByText('タグ候補を確認できます', { exact: true })).toBeVisible({ timeout: 45000 });
    await dialog.getByLabel('旅のひとこと').fill('森を歩いたあと、窓辺でコーヒー。次はみんなで来たい。');
    const cafe = dialog.getByRole('button', { name: /カフェ/ });
    if (await cafe.count()) await cafe.last().click();
    await dialog.getByRole('checkbox').check();
    await axe('photo-composer');
    const created = page.waitForResponse(response => response.url().endsWith('/api/posts') && response.request().method() === 'POST');
    await dialog.getByRole('button', { name: 'このコミュニティに公開', exact: true }).click();
    postedId = (await (await created).json()).id;
    await expect(dialog).not.toBeVisible();
    await expect(page.getByText('森を歩いたあと、窓辺でコーヒー。次はみんなで来たい。', { exact: true })).toBeVisible();
  });
  await check('preferences and independent community grants persist', async () => {
    await openPreferences();
    await expect(page.getByRole('heading', { name: '自分の好み', exact: true })).toBeVisible();
    await axe('preferences');
    await page.getByRole('checkbox', { name: /自分の公開投稿からも、好みの候補を見つける/ }).check();
    await clickVisible('好みと許可を保存');
    await expect(page.getByText('好みと共有範囲を保存しました。', { exact: true })).toBeVisible();
    await expect(page.getByText('投稿にあるタグ', { exact: true })).toBeVisible();
    await page.reload();
    await openPreferences();
    await expect(page.getByRole('checkbox', { name: '自分の好みを仲間探しに使う', exact: true }).first()).toBeChecked();
  });
  await check('create a three-person proposal through the interface', async () => {
    await clickVisible('講を見つける');
    await clickVisible('仲間と旅を考える');
    const dialog = page.getByRole('dialog');
    await dialog.getByLabel('どんな旅にしたい？').fill('軽井沢で、森とカフェをめぐる');
    await dialog.locator('.trip-choice').first().click();
    await dialog.getByLabel('自分を含めた人数', { exact: true }).click();
    await dialog.getByRole('option', { name: '3人', exact: true }).click();
    const proposed = page.waitForResponse(response => response.url().endsWith('/proposals') && response.request().method() === 'POST');
    await dialog.getByRole('button', { name: '共通の好みから仲間を探す', exact: true }).click();
    proposalId = (await (await proposed).json()).id;
    await expect(dialog).not.toBeVisible({ timeout: 20000 });
    await expect(page.getByRole('heading', { name: '軽井沢で、森とカフェをめぐる', exact: true }).first()).toBeVisible();
    await clickVisible('この旅に参加する');
  });
  await check('each other user accepts; a group forms only after the last acceptance', async () => {
    await logout();
    await login('ren');
    await clickVisible('講を見つける');
    await clickVisible('この旅に参加する');
    let proposal = await jsonAPI(`/proposals/${proposalId}`);
    assert.equal(proposal.group_id, null);
    await logout();
    await login('mio');
    await clickVisible('講を見つける');
    await clickVisible('この旅に参加する');
    await expect(page.getByText('みんなの参加がそろいました', { exact: true }).first()).toBeVisible();
    proposal = await jsonAPI(`/proposals/${proposalId}`);
    assert.equal(proposal.status, 'formed');
    groupId = proposal.group_id;
    const groups = await jsonAPI('/groups');
    assert.equal(groups.items.filter(g => g.id === groupId).length, 1);
  });
  await check('voluntary contribution and trip plan are saved', async () => {
    const panel = page.locator('.group-card').first();
    await panel.getByRole('radio', { name: '写真を撮る', exact: true }).check();
    await clickVisible('できることを保存', panel);
    await expect(panel.getByText('できることを保存しました。', { exact: true })).toBeVisible();
    await panel.getByText('旅の計画をひらく', { exact: true }).click();
    await panel.getByLabel('出発日', { exact: true }).fill('2026-11-28');
    await panel.getByLabel('待ち合わせ', { exact: true }).fill('軽井沢駅の改札前、10時');
    await panel.getByLabel('行程メモ', { exact: true }).fill('森を歩いてからカフェへ。昼食のお店は当日みんなで相談。');
    await clickVisible('旅の計画を保存', panel);
    await expect(panel.getByText('旅の計画を保存しました。', { exact: true })).toBeVisible();
    const group = await jsonAPI(`/groups/${groupId}`);
    assert.equal(group.plan.date, '2026-11-28');
    assert.equal(group.contributions.find(c => c.name === '小野 美緒').role, 'photos');
    await axe('group-plan');
    await page.screenshot({ path: path.join(output, 'group-mobile.png'), fullPage: true });
  });
  await check('200 percent text and keyboard navigation remain usable', async () => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
    await noOverflow();
    await page.keyboard.press('Tab');
    assert(await page.evaluate(() => document.activeElement !== document.body));
    await page.screenshot({ path: path.join(output, 'group-text-200.png'), fullPage: true });
    await page.evaluate(() => { document.documentElement.style.fontSize = ''; });
  });
  await check('no external requests or uncaught browser errors', async () => {
    assert.deepEqual(external, []);
    assert.deepEqual(errors, []);
  });
  await logout();
  await login('aoi');
  if (postedId) await jsonAPI(`/posts/${postedId}`, 'DELETE', {});
  await page.reload();
  await page.setViewportSize({ width: 1440, height: 1050 });
  await expect(page.locator('.post-card').first()).toBeVisible();
  await expect.poll(() => page.locator('.post-card img').first().evaluate(image => image.complete && image.naturalWidth > 0)).toBe(true);
  await page.screenshot({ path: path.join(output, 'final-desktop.png'), fullPage: true });
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
} finally {
  await fs.writeFile(path.join(output, 'results.json'), JSON.stringify({ baseURL, created: { postedId, proposalId, groupId }, results, externalRequests: external, pageErrors: errors }, null, 2));
  await browser.close();
}
