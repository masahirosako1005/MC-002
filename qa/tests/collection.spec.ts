import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const artifacts = path.resolve('../artifacts');
async function openJournal(page: Page) {
  await page.getByRole('navigation', { name: '主なメニュー' }).getByRole('button', { name: '旅の手帳' }).click();
  await expect(page.locator('.keepsake-slot')).toHaveCount(12);
}
async function home(page: Page) {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('ひとつの街を');
}
async function axe(page: Page, name: string) {
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  await fs.writeFile(path.join(artifacts, `axe-${name}.json`), JSON.stringify(result.violations, null, 2));
  expect(result.violations, JSON.stringify(result.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) })))).toEqual([]);
}

test('未獲得の条件・次季への接続・狙う一品の再読込保持', async ({ page }) => {
  await home(page);
  await openJournal(page);
  const trigger = page.getByRole('button', { name: /灯りをつなぐ水路、.*詳細をひらく/ });
  await trigger.click();
  const dialog = page.getByRole('dialog', { name: '灯りをつなぐ水路' });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText('冬に水門を訪れ');
  await dialog.getByRole('button', { name: '次に狙う一品にする', exact: true }).click();
  await expect(dialog.getByRole('status')).toContainText('いちばん上');
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
  await page.reload();
  await openJournal(page);
  await expect(page.locator('.trophy-feature')).toContainText('灯りをつなぐ水路');
  await expect(page.locator('.trophy-feature')).toContainText('次に狙う一品');
  const state = await (await page.request.get('/api/collection')).json();
  expect(state.summary.earned).toBe(0);
  expect(state.target_id).toBe('season-winter');
  await page.getByRole('button', { name: '灯りをつなぐ水路の記念品をひらく', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: '四季の水門の案内をひらく' }).click();
  await expect(page.getByRole('button', { name: '冬', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('四季の水門');
});

test('訪問で記念品が現れ日時・別日条件・狭幅と拡大で詳細を確認できる', async ({ page }) => {
  await home(page);
  await page.getByRole('button', { name: '四季の謎をひらく' }).click();
  await page.getByLabel('訪問コード', { exact: true }).fill('GATE-314');
  await page.getByRole('button', { name: '記す', exact: true }).click();
  await expect(page.getByText('今日の訪問を手帳に記しました。')).toBeVisible();
  await openJournal(page);
  await expect(page.locator('.shelf-count')).toContainText('1 / 12');
  await expect(page.locator('.starter-result')).toContainText('1 / 2');
  await page.getByRole('button', { name: /水門の鍵、完成、詳細をひらく/ }).click();
  const dialog = page.getByRole('dialog', { name: '水門の鍵' });
  await expect(dialog.locator('.keepsake-date')).toContainText('最初に集めた日');
  await expect(dialog.locator('.trophy-stages')).toContainText('に達成');
  await dialog.getByRole('button', { name: 'この記念品を棚に飾る' }).click();
  await expect(dialog.getByRole('status')).toContainText('いちばん上');
  await page.keyboard.press('Escape');
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
  await page.screenshot({ path: path.join(artifacts, 'collection-mobile.png'), fullPage: true });
  await page.screenshot({ path: path.join(artifacts, 'collection-screen.png') });
  await axe(page, 'collection-earned');
  await page.getByRole('button', { name: /また来た道、.*詳細をひらく/ }).click();
  await expect(page.getByRole('dialog')).toContainText('別の日にあと1回');
  await expect(page.getByRole('dialog').getByRole('progressbar', { name: 'また来た道の進捗' })).toHaveAttribute('value', '1');
  await expect(page.getByRole('dialog').getByRole('progressbar', { name: 'また来た道の進捗' })).toHaveAttribute('max', '2');
  await axe(page, 'collection-detail');
  for (const width of [320, 390, 430]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
    expect(await page.getByRole('dialog').evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBeTruthy();
  }
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
  expect(await page.getByRole('dialog').evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBeTruthy();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
});

test('目標保存の失敗を案内して手動で再試行できる', async ({ page }) => {
  await home(page);
  await openJournal(page);
  await page.getByRole('button', { name: /また来た道、.*詳細をひらく/ }).click();
  let failed = false;
  await page.route('**/api/collection/target', async route => {
    if (!failed) { failed = true; await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: '記録を読み書きできませんでした。' }) }); }
    else await route.continue();
  });
  const dialog = page.getByRole('dialog');
  await dialog.getByRole('button', { name: '次に狙う一品にする' }).click();
  await expect(dialog.getByRole('alert')).toContainText('記録を読み書きできません');
  expect((await (await page.request.get('/api/collection')).json()).target_id).toBeNull();
  await dialog.getByRole('button', { name: 'もう一度読み込む' }).click();
  await expect(dialog.getByRole('status')).toContainText('いちばん上');
  await expect(dialog.getByRole('button', { name: '選んだ一品から外す' })).toBeVisible();
});

test('旅の選択部品はキーボードで変更でき選択と焦点が見える', async ({ page }) => {
  await home(page);
  await page.getByRole('navigation', { name: '主なメニュー' }).getByRole('button', { name: '次の旅' }).click();
  const time = page.getByLabel('使える時間');
  await time.focus();
  await time.press('Home');
  await time.press('ArrowDown');
  await expect(time).toHaveValue('60');
  const border = await time.evaluate(el => getComputedStyle(el).outlineStyle);
  expect(border).not.toBe('none');
  await page.getByLabel('気になること').selectOption('coast');
  await expect(page.getByLabel('気になること')).toHaveValue('coast');
  await page.setViewportSize({ width: 320, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
  await page.screenshot({ path: path.join(artifacts, 'select-controls.png') });
});
