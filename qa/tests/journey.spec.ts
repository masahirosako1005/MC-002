import { test, expect, type Locator, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const artifacts = path.resolve('..', 'artifacts');
async function home(page: Page) {
  await page.goto('/');
  await expect(page.getByRole('heading', {level:1})).toContainText('ひとつの街を');
}
async function navigate(page: Page, name: string) {
  await page.getByRole('navigation', {name:'主なメニュー'}).getByRole('button', {name, exact:false}).click();
}
async function checkAxe(page: Page, name: string) {
  const results = await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
  await fs.writeFile(path.join(artifacts, `axe-${name}.json`),JSON.stringify(results.violations,null,2));
  expect(results.violations, JSON.stringify(results.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)})))).toEqual([]);
}
async function focusByKeyboard(page: Page, target: Locator) {
  await expect(target).toBeVisible();
  for(let step=0;step<100;step++) {
    if(await target.evaluate(element=>element===document.activeElement)) return;
    await page.keyboard.press('Tab');
  }
  throw new Error('100回のTab移動で目的の操作に到達できませんでした。');
}
async function activateByKeyboard(page: Page, target: Locator) {
  await focusByKeyboard(page,target);
  await page.keyboard.press('Enter');
}
test('主要画面の表示・外部通信なし・アクセシビリティ', async ({page})=>{
  const external:string[]=[];
  const errors:string[]=[];
  page.on('pageerror', e=>errors.push(e.message));
  await page.route('**/*',async route=>{
    const url=new URL(route.request().url());
    if(!['127.0.0.1','localhost'].includes(url.hostname)) {external.push(url.origin);await route.abort();}
    else await route.continue();
  });
  await home(page);
  await page.screenshot({path:path.join(artifacts,'home-mobile.png'),fullPage:true});
  await page.screenshot({path:path.join(artifacts,'home-screen.png')});
  await checkAxe(page,'home');
  await navigate(page,'旅の手帳');
  await expect(page.getByRole('heading',{name:'旅の手帳',exact:true})).toBeVisible();
  await checkAxe(page,'journal');
  await navigate(page,'次の旅');
  await expect(page.getByRole('heading',{name:'次の旅',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'冬',exact:true}).click();
  await expect(page.locator('.recommendation-card').first()).toBeVisible();
  await page.screenshot({path:path.join(artifacts,'next-mobile.png'),fullPage:true});
  await page.screenshot({path:path.join(artifacts,'next-screen.png')});
  await checkAxe(page,'next');
  expect(external).toEqual([]); expect(errors).toEqual([]);
  await fs.writeFile(path.join(artifacts,'browser-network.json'),JSON.stringify({externalRequests:external,pageErrors:errors,mode:'external requests blocked; local HTTP allowed'},null,2));
});

test('現地コードから水門の謎・実績・次季保存まで',async({page})=>{
  await home(page);
  await page.getByRole('button',{name:'四季の謎をひらく'}).click();
  await page.getByLabel('訪問コード',{exact:true}).fill('INVALID');
  await page.getByRole('button',{name:'記す',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('一致しません');
  await page.getByLabel('訪問コード',{exact:true}).fill('GATE-314');
  await page.getByRole('button',{name:'記す',exact:true}).click();
  await expect(page.getByText('今日の訪問を手帳に記しました。')).toBeVisible();
  await page.getByRole('button',{name:'水門の謎に挑む'}).click();
  await expect(page.getByRole('heading',{name:'水辺の手掛かり'})).toBeVisible();
  await page.screenshot({path:path.join(artifacts,'puzzle-mobile.png'),fullPage:true});
  await page.screenshot({path:path.join(artifacts,'puzzle-screen.png')});
  await checkAxe(page,'puzzle');
  await page.getByRole('button',{name:'水の流れを確かめる'}).click();
  await expect(page.getByText(/まだ水量が合いません/)).toBeVisible();
  await page.getByRole('button',{name:'ヒントを読む',exact:true}).click();
  await expect(page.locator('.hint-card')).toBeVisible();
  // Solve from the displayed clue, not from an exposed answer API.
  const clue=await page.locator('.clue-card').innerText();
  const sum=Number(clue.match(/合計は(\d+)/)?.[1]);
  const blue=Number(clue.match(/碧の水門は(\d+)/)?.[1]);
  const red=Number(clue.match(/朱の水門は(\d+)/)?.[1]);
  expect(Number.isFinite(sum+red+blue)).toBeTruthy();
  const values=[red,sum-red-blue,blue];
  for(let i=0;i<3;i++) {
    const range=page.locator(`#gate-${i}`);await range.focus();await range.press('Home');
    for(let n=0;n<values[i];n++) await range.press('ArrowRight');
  }
  await page.getByRole('button',{name:'水の流れを確かめる'}).click();
  await expect(page.getByText('旅の手帳に実績を記しました',{exact:true})).toBeVisible();
  await expect(page.locator('.result-score')).toContainText('75');
  await page.locator('.return-invitation').getByRole('button',{name:/次の旅に保存$/}).click();
  await expect(page.locator('.return-invitation')).toContainText('保存');
  await navigate(page,'旅の手帳');
  await expect(page.locator('.timeline')).toContainText('四季の水門');
  await expect(page.locator('.timeline')).toContainText('水門・はじめて');
  await page.screenshot({path:path.join(artifacts,'journal-mobile.png'),fullPage:true});
  await page.reload();
  await navigate(page,'旅の手帳');
  await expect(page.locator('.journal-totals')).toContainText('1');
  const cookie=(await page.context().cookies()).find(c=>c.name==='journey_session');
  expect(cookie?.httpOnly).toBe(true);expect(cookie?.sameSite).toBe('Strict');
  expect(await page.evaluate(()=>document.cookie)).not.toContain('journey_session');
});

test('会議周遊の制約・保存・取消と人生行事',async({page})=>{
  await home(page);await navigate(page,'次の旅');
  await page.getByRole('button',{name:'冬',exact:true}).click();
  await page.getByLabel('使える時間').selectOption('30');
  await page.getByLabel('気になること').selectOption('coast');
  await expect(page.getByText('この条件では見つかりませんでした')).toBeVisible();
  await page.getByLabel('使える時間').selectOption('180');
  const candidate=page.locator('.recommendation-card').first();
  await expect(candidate).toContainText('冬の堤防で釣り');
  await expect(candidate.locator('.duration-badge')).toContainText('120');
  await candidate.getByRole('button',{name:/次の旅に保存$/}).click();
  await expect(page.locator('.saved-trips .plan-card')).toHaveCount(1);
  await page.locator('.saved-trips .remove-button').click();
  await page.getByRole('button',{name:'残す',exact:true}).click();
  await expect(page.locator('.saved-trips .plan-card')).toHaveCount(1);
  await page.locator('.saved-trips .remove-button').click();
  await page.getByRole('button',{name:'次の旅から外す',exact:true}).click();
  await expect(page.locator('.saved-trips .plan-card')).toHaveCount(0);
  await page.getByLabel('気になること').selectOption('shrine');
  await expect(page.locator('.recommendation-list')).toContainText('お宮参り');
  await expect(page.locator('.recommendation-list')).toContainText('希望する時期に');
});

for (const width of [320,390,430]) {
  test(`幅${width}pxと文字拡大で横溢れなし`,async({page})=>{
    await page.setViewportSize({width,height:844});await home(page);
    await page.getByRole('button',{name:'文字サイズ'}).click();
    for(const name of ['旅のしおり','旅の手帳','次の旅']) {
      await navigate(page,name);
      await expect(page.locator('h1')).toBeVisible();
      const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
      expect(overflow).toBeLessThanOrEqual(1);
    }
  });
}

test('通信失敗から再試行できる',async({page})=>{
  await home(page);
  await page.route('**/api/recommendations?*',route=>route.abort());
  await navigate(page,'次の旅');
  await expect(page.getByRole('alert')).toBeVisible();
  await page.unroute('**/api/recommendations?*');
  await page.getByRole('button',{name:/もう一度|再試行/}).click();
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.locator('.recommendation-reason')).toBeVisible();
});

test('キーボードと動きを減らす設定',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});await home(page);
  await page.keyboard.press('Tab');
  const focused=await page.evaluate(()=>document.activeElement?.tagName);
  expect(['A','BUTTON']).toContain(focused);
  const motion=await page.evaluate(()=>matchMedia('(prefers-reduced-motion: reduce)').matches);
  expect(motion).toBe(true);
  await checkAxe(page,'reduced-motion');
});

test('別ブラウザーで手帳を引き継ぐ',async({page,browser})=>{
  await home(page);await navigate(page,'次の旅');
  await page.getByRole('button',{name:'冬',exact:true}).click();
  await page.locator('.recommendation-card').first().getByRole('button',{name:/次の旅に保存$/}).click();
  await expect(page.locator('.saved-trips .plan-card')).toHaveCount(1);
  const savedTitle=await page.locator('.saved-trips h3').first().innerText();
  await page.getByRole('button',{name:'手帳の引き継ぎをひらく'}).click();
  await checkAxe(page,'recovery');
  await page.getByRole('button',{name:'合言葉を発行する'}).click();
  const code=await page.getByLabel('今回の合言葉',{exact:true}).inputValue();
  expect(code.length).toBeGreaterThan(40);
  await page.getByRole('button',{name:'引き継ぎを閉じる'}).click();
  await expect(page.locator('#issued-code')).toHaveCount(0);
  // Prepare the unsaved card while this browser is still authenticated.
  await page.getByRole('button',{name:'春',exact:true}).click();
  await expect(page.locator('.recommendation-card').first()).toContainText('春');
  const context=await browser.newContext({viewport:{width:390,height:844},locale:'ja-JP'});
  const other=await context.newPage();
  await other.goto(process.env.APP_URL || 'http://127.0.0.1:8080');
  await expect(other.locator('h1')).toContainText('ひとつの街');
  await other.getByRole('button',{name:'手帳の引き継ぎをひらく'}).click();
  await other.getByLabel('合言葉',{exact:true}).fill(code);
  await other.getByRole('button',{name:'この手帳を引き継ぐ'}).click();
  await expect(other.getByText('手帳を引き継ぎました。訪問や次の旅を確認できます。')).toBeVisible();
  await other.getByRole('button',{name:'引き継ぎを閉じる'}).click();
  await navigate(other,'次の旅');
  await expect(other.locator('.saved-trips')).toContainText(savedTitle);
  // Recovery has really invalidated the old browser session on the server.
  // A rejected write must not be retried under a newly created anonymous identity.
  let writes=0;
  page.on('request',r=>{if(r.url().endsWith('/api/plans') && r.method()==='POST') writes++;});
  await page.locator('.recommendation-card').first().getByRole('button',{name:/次の旅に保存$/}).click();
  await expect(page.getByRole('heading',{name:'手帳を開けませんでした'})).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('引き継ぎ');
  await page.getByRole('button',{name:'もう一度読み込む'}).click();
  await expect(page.getByRole('alert')).toContainText('引き継ぎ');
  expect(writes).toBe(1);
  await page.getByRole('button',{name:'手帳の引き継ぎをひらく'}).click();
  await page.getByLabel('合言葉',{exact:true}).fill(code);
  await page.getByRole('button',{name:'この手帳を引き継ぐ'}).click();
  await expect(page.getByText('手帳を引き継ぎました。訪問や次の旅を確認できます。')).toBeVisible();
  await page.getByRole('button',{name:'引き継ぎを閉じる'}).click();
  await navigate(page,'次の旅');
  await expect(page.locator('.saved-trips')).toContainText(savedTitle);
  await expect(page.locator('.saved-trips .plan-card')).toHaveCount(1);
  await context.close();
});

test('過年度の謎の季節がカタログに依存せず残る',async({page})=>{
  await page.route('**/api/journal',async route=>route.fulfill({json:{visits:[],achievements:[],plans:[],attempts:[{id:'old-attempt',game_id:'retired-2025-game',title:'昨年の秋の水門',season:'autumn',status:'completed',score:100,hints_used:0,created_at:'2025-11-09T10:00:00+09:00',completed_at:'2025-11-09T10:05:00+09:00'}]}}));
  await home(page);await navigate(page,'旅の手帳');
  await expect(page.locator('.collection-seasons .collected')).toHaveCount(1);
  await expect(page.locator('.collection-seasons .collected')).toContainText('秋');
});

test('文字200パーセントで主要画面を操作できる',async({page})=>{
  await home(page);
  await page.evaluate(()=>{document.documentElement.style.fontSize='200%';});
  expect(await page.evaluate(()=>getComputedStyle(document.documentElement).fontSize)).toBe('32px');
  for(const name of ['旅のしおり','旅の手帳','次の旅']) {
    await navigate(page,name);
    await expect(page.locator('h1')).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth)).toBeLessThanOrEqual(1);
  }
});

test('初期読込の再試行でセッション情報も再取得する',async({page})=>{
  let reads=0;let fail=true;
  page.on('request',r=>{if(r.url().endsWith('/api/session') && r.method()==='GET') reads++;});
  await page.route('**/api/journal',async route=>{if(fail) await route.fulfill({status:503,json:{detail:'記録を読み書きできませんでした。'}});else await route.continue();});
  await page.goto('/');
  await expect(page.getByRole('alert')).toBeVisible();
  fail=false;await page.getByRole('button',{name:/もう一度|再試行/}).click();
  await expect(page.locator('h1')).toContainText('ひとつの街');
  expect(reads).toBeGreaterThanOrEqual(2);
});

test('同じブラウザーの別タブで引き継いでも再読込後は同じ手帳に保存する',async({page})=>{
  await home(page);
  await navigate(page,'次の旅');
  await page.getByRole('button',{name:'冬',exact:true}).click();
  await page.locator('.recommendation-card').first().getByRole('button',{name:/次の旅に保存$/}).click();
  await expect(page.locator('.saved-trips .plan-card')).toHaveCount(1);
  const originalTitle=await page.locator('.saved-trips h3').first().innerText();

  await page.getByRole('button',{name:'手帳の引き継ぎをひらく'}).click();
  await page.getByRole('button',{name:'合言葉を発行する'}).click();
  const code=await page.getByLabel('今回の合言葉',{exact:true}).inputValue();
  expect(code.length).toBeGreaterThan(40);
  await page.getByRole('button',{name:'引き継ぎを閉じる'}).click();
  const springLoaded=page.waitForResponse(response=>new URL(response.url()).pathname==='/api/recommendations' && new URL(response.url()).searchParams.get('season')==='spring');
  await page.getByRole('button',{name:'春',exact:true}).click();
  await springLoaded;
  await expect(page.locator('.recommendations')).toHaveAttribute('aria-busy','false');
  const unsaved=page.locator('.recommendation-card').filter({has:page.getByRole('button',{name:/次の旅に保存$/})}).first();
  await expect(unsaved.getByRole('button',{name:/次の旅に保存$/})).toBeEnabled();
  const nextTitle=await unsaved.getByRole('heading',{level:3}).innerText();
  expect(nextTitle).not.toBe(originalTitle);

  // Tabs share the cookie jar, but each running app holds its own CSRF token in memory.
  const other=await page.context().newPage();
  try {
    await other.goto(process.env.APP_URL || 'http://127.0.0.1:8080');
    await expect(other.locator('h1')).toContainText('ひとつの街');
    await other.getByRole('button',{name:'手帳の引き継ぎをひらく'}).click();
    await other.getByLabel('合言葉',{exact:true}).fill(code);
    await other.getByRole('button',{name:'この手帳を引き継ぐ'}).click();
    await expect(other.getByText('手帳を引き継ぎました。訪問や次の旅を確認できます。')).toBeVisible();
    await other.getByRole('button',{name:'引き継ぎを閉じる'}).click();
    await navigate(other,'次の旅');
    await expect(other.locator('.saved-trips')).toContainText(originalTitle);
    await expect(other.locator('.saved-trips .plan-card')).toHaveCount(1);

    let writes=0;
    let anonymousCreations=0;
    page.on('request',request=>{
      const pathname=new URL(request.url()).pathname;
      if(request.method()==='POST' && pathname==='/api/plans') writes++;
      if(request.method()==='POST' && pathname==='/api/session') anonymousCreations++;
    });
    const rejectedWrite=page.waitForResponse(response=>new URL(response.url()).pathname==='/api/plans' && response.request().method()==='POST');
    await unsaved.getByRole('button',{name:/次の旅に保存$/}).click();
    const rejected=await rejectedWrite;
    expect(rejected.status()).toBe(403);
    expect(rejected.headers()['x-session-invalid']).toBe('true');
    await expect(page.getByRole('heading',{name:'手帳を開けませんでした'})).toBeVisible();
    await expect(page.getByRole('alert')).toContainText('接続が変わりました');
    expect(writes).toBe(1);

    // The on-screen retry refreshes the token. It must not replay the failed mutation.
    await page.getByRole('button',{name:'もう一度読み込む'}).click();
    await expect(page.getByRole('heading',{name:'次の旅',exact:true})).toBeVisible();
    await expect(page.locator('.saved-trips .plan-card')).toHaveCount(1);
    await expect(page.locator('.saved-trips')).toContainText(originalTitle);
    expect(writes).toBe(1);
    expect(anonymousCreations).toBe(0);

    await page.getByRole('button',{name:'春',exact:true}).click();
    const candidate=page.locator('.recommendation-card').filter({has:page.getByRole('heading',{name:nextTitle,exact:true})});
    await candidate.getByRole('button',{name:/次の旅に保存$/}).click();
    await expect(page.locator('.saved-trips .plan-card')).toHaveCount(2);
    await expect(page.locator('.saved-trips')).toContainText(originalTitle);
    await expect(page.locator('.saved-trips')).toContainText(nextTitle);
    expect(writes).toBe(2);
    expect(anonymousCreations).toBe(0);

    // The other tab sees both records after a read, proving no separate journal was created.
    await other.reload();
    await expect(other.locator('h1')).toContainText('ひとつの街');
    await navigate(other,'次の旅');
    await expect(other.locator('.saved-trips .plan-card')).toHaveCount(2);
    await expect(other.locator('.saved-trips')).toContainText(originalTitle);
    await expect(other.locator('.saved-trips')).toContainText(nextTitle);
  } finally {
    await other.close();
  }
});

test('キーボードだけで現地訪問から水門達成・次季保存・手帳確認まで操作する',async({page})=>{
  await home(page);
  const recovery=page.getByRole('button',{name:'手帳の引き継ぎをひらく'});
  await activateByKeyboard(page,recovery);
  await expect(page.getByRole('dialog',{name:'手帳の引き継ぎ'})).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog',{name:'手帳の引き継ぎ'})).not.toBeVisible();
  await expect(recovery).toBeFocused();

  await activateByKeyboard(page,page.getByRole('button',{name:'四季の謎をひらく'}));
  await focusByKeyboard(page,page.getByLabel('訪問コード',{exact:true}));
  await page.keyboard.type('GATE-314');
  await activateByKeyboard(page,page.getByRole('button',{name:'記す',exact:true}));
  await expect(page.getByText('今日の訪問を手帳に記しました。')).toBeVisible();

  const advanced=page.getByRole('button',{name:'じっくり',exact:true});
  const beginner=page.getByRole('button',{name:'はじめて',exact:true});
  await activateByKeyboard(page,advanced);
  await expect(advanced).toHaveAttribute('aria-pressed','true');
  await activateByKeyboard(page,beginner);
  await expect(beginner).toHaveAttribute('aria-pressed','true');
  await activateByKeyboard(page,page.getByRole('button',{name:'水門の謎に挑む'}));
  await expect(page.getByRole('heading',{name:'水辺の手掛かり'})).toBeVisible();

  await activateByKeyboard(page,page.getByRole('button',{name:'水の流れを確かめる'}));
  await expect(page.getByText(/まだ水量が合いません/)).toBeVisible();
  const clue=await page.locator('.clue-card').innerText();
  const sum=Number(clue.match(/合計は(\d+)/)?.[1]);
  const blue=Number(clue.match(/碧の水門は(\d+)/)?.[1]);
  const red=Number(clue.match(/朱の水門は(\d+)/)?.[1]);
  expect(Number.isFinite(sum+red+blue)).toBeTruthy();
  const values=[red,sum-red-blue,blue];
  for(let index=0;index<values.length;index++) {
    const range=page.locator(`#gate-${index}`);
    await focusByKeyboard(page,range);
    await page.keyboard.press('Home');
    for(let value=0;value<values[index];value++) await page.keyboard.press('ArrowRight');
    await expect(range).toHaveValue(String(values[index]));
  }
  await activateByKeyboard(page,page.getByRole('button',{name:'水の流れを確かめる'}));
  await expect(page.getByText('旅の手帳に実績を記しました',{exact:true})).toBeVisible();
  await expect(page.locator('.result-score')).toContainText('95');
  await activateByKeyboard(page,page.locator('.return-invitation').getByRole('button',{name:/次の旅に保存$/}));
  await expect(page.locator('.return-invitation').getByRole('button',{name:/保存済み$/})).toBeDisabled();

  const nav=page.getByRole('navigation',{name:'主なメニュー'});
  await activateByKeyboard(page,nav.getByRole('button',{name:'旅の手帳',exact:true}));
  await expect(page.getByRole('heading',{name:'旅の手帳',exact:true})).toBeVisible();
  await expect(page.locator('.timeline')).toContainText('水門・はじめて');
  await expect(page.locator('.collection-seasons .collected')).toHaveCount(1);
  await activateByKeyboard(page,nav.getByRole('button',{name:/次の旅/}));
  await expect(page.getByRole('heading',{name:'次の旅',exact:true})).toBeVisible();
  await expect(page.locator('.saved-trips .plan-card')).toHaveCount(1);
  await expect(page.locator('.saved-trips')).toContainText('水門');
});

test('別タブで引き継いだ後に古い引き継ぎ画面からも復帰できる',async({page})=>{
  test.setTimeout(120000);
  // All local browsers share the gateway address and the real 5/minute recovery
  // bucket. Let prior scenarios expire rather than weaken production protection.
  await new Promise(resolve=>setTimeout(resolve,61000));
  await home(page);
  await page.getByRole('button',{name:'手帳の引き継ぎをひらく'}).click();
  await page.getByRole('button',{name:'合言葉を発行する'}).click();
  const code=await page.getByLabel('今回の合言葉',{exact:true}).inputValue();
  await page.getByRole('button',{name:'引き継ぎを閉じる'}).click();
  const other=await page.context().newPage();
  await other.goto(process.env.APP_URL || 'http://127.0.0.1:8080');
  await expect(other.locator('h1')).toContainText('ひとつの街');
  await other.getByRole('button',{name:'手帳の引き継ぎをひらく'}).click();
  await other.getByLabel('合言葉',{exact:true}).fill(code);
  await other.getByRole('button',{name:'この手帳を引き継ぐ'}).click();
  await expect(other.getByText('手帳を引き継ぎました。訪問や次の旅を確認できます。')).toBeVisible();
  await page.getByRole('button',{name:'手帳の引き継ぎをひらく'}).click();
  await page.getByLabel('合言葉',{exact:true}).fill(code);
  await page.getByRole('button',{name:'この手帳を引き継ぐ'}).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.getByRole('heading',{name:'手帳を開けませんでした'})).toBeVisible();
  await page.getByRole('button',{name:'もう一度読み込む'}).click();
  await expect(page.locator('h1')).toContainText('ひとつの街');
  await page.getByRole('button',{name:'手帳の引き継ぎをひらく'}).click();
  await expect(page.getByRole('alert')).toHaveCount(0);
  // Invalid recovery codes remain a local error, with no destructive account switch.
  await page.getByLabel('合言葉',{exact:true}).fill('TC-invalid-code-abcdefghijk');
  await page.getByRole('button',{name:'この手帳を引き継ぐ'}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('復旧できません');
  await page.getByLabel('合言葉',{exact:true}).fill(code);
  await page.getByRole('button',{name:'この手帳を引き継ぐ'}).click();
  await expect(page.getByText('手帳を引き継ぎました。訪問や次の旅を確認できます。')).toBeVisible();
  await other.close();
});
