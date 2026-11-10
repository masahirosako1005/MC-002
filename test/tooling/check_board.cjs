const { chromium } = require('../browser/node_modules/@playwright/test');
const { pathToFileURL } = require('node:url');
const path = require('node:path');
const fs = require('node:fs');
const root = path.resolve(__dirname, '../..');
const output = path.join(root, 'artifacts/tooling/board');
fs.mkdirSync(output, { recursive: true });

(async () => {
  const snapshot = JSON.parse(fs.readFileSync(path.join(root, 'project/tickets.json'), 'utf8'));
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1450, height: 1000 } });
  const errors = [];
  const network = [];
  const checks = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', route => {
    if (/^https?:/.test(route.request().url())) {
      network.push(route.request().url());
      return route.abort();
    }
    return route.continue();
  });
  const assert = (name, condition) => {
    checks.push({ name, passed: Boolean(condition) });
    if (!condition) throw new Error(name);
  };
  try {
    await page.goto(pathToFileURL(path.join(root, 'outputs/project-board.html')).href);
    assert('ローカルHTMLに正本の全チケットを表示', await page.locator('.card').count() === snapshot.tickets.length);
    const columns = await page.locator('.column').evaluateAll(elements => elements.map(element => element.getBoundingClientRect().x));
    assert('デスクトップに4列を表示', new Set(columns).size === 4);
    await page.getByLabel('チケットを検索').fill('年度が変わると獲得した季節');
    assert('件名検索で1件に絞り込み', await page.locator('.card').count() === 1);
    await page.locator('.card').click();
    assert('詳細に受入条件と証拠を表示', await page.locator('dialog .criterion').count() >= 2 && await page.locator('dialog .evidence-item').count() >= 1);
    await page.getByRole('button', { name: '詳細を閉じる' }).click();
    await page.getByRole('button', { name: '条件を戻す' }).click();
    await page.locator('#status').selectOption('done');
    assert('完了フィルターは正本の完了チケットだけ表示', await page.locator('.card').count() === snapshot.tickets.filter(ticket => ticket.status === 'done').length);
    await page.getByRole('button', { name: '条件を戻す' }).click();
    await page.locator('#priority').selectOption('P0');
    assert('優先度フィルターで緊急課題を表示', await page.locator('.card').count() === snapshot.tickets.filter(ticket => ticket.priority === 'P0').length);
    await page.getByRole('button', { name: '条件を戻す' }).click();
    await page.screenshot({ path: path.join(output, 'board-preview.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    assert('スマホ幅で横にはみ出さない', await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    assert('外部通信を要求しない', network.length === 0);
    assert('JavaScriptエラーがない', errors.length === 0);
  } finally {
    fs.writeFileSync(path.join(output, 'board-check.json'), JSON.stringify({ checked_at: new Date().toISOString(), browser: 'Microsoft Edge / Playwright', viewport: { desktop: '1450x1000', mobile: '390x844' }, checks, errors, external_requests: network }, null, 2));
    await browser.close();
  }
  process.stdout.write(JSON.stringify({ passed: checks.filter(check => check.passed).length, total: checks.length }) + '\n');
})().catch(error => { console.error(error.message); process.exitCode = 1; });
