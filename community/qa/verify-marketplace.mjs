import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(path.join(root,'qa/package.json'));
const {chromium,expect}=require('@playwright/test');
const AxeBuilder=require('@axe-core/playwright').default;
const output=path.join(root,'community/artifacts/marketplace-browser');
await fs.mkdir(output,{recursive:true});
const base='http://127.0.0.1:8081', results=[],errors=[],external=[],sessions={};
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1050},locale:'ja-JP',timezoneId:'Asia/Tokyo'});
await context.route('**/*',async route=>{const u=new URL(route.request().url());if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.origin);await route.abort();}else await route.continue();});
const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
let partyId,consultationId,createdPlanId;
const visitor=page.frameLocator('iframe[title="旅行者の操作画面"]');
const provider=page.frameLocator('iframe[title="事業者の操作画面"]');
async function click(name,scope=page){const list=scope.getByRole('button',{name,exact:typeof name==='string'});await expect.poll(async()=>{for(let i=0;i<await list.count();i++)if(await list.nth(i).isVisible())return true;return false;},{timeout:20000}).toBe(true);for(let i=0;i<await list.count();i++)if(await list.nth(i).isVisible()){await list.nth(i).click();return;}}
async function step(name,fn){try{await fn();results.push({name,status:'passed'});console.log('PASS '+name);}catch(e){results.push({name,status:'failed',message:String(e.message).slice(0,1800)});await page.screenshot({path:path.join(output,'failure.png'),fullPage:true});throw e;}}
async function login(scope,username){await scope.getByRole('radio',{name:new RegExp(username)}).check();await scope.getByLabel('パスワード',{exact:true}).fill(`${username}-local-2026`);const response=page.waitForResponse(r=>r.url().endsWith('/api/stage/login')&&r.request().method()==='POST');await click('ログイン',scope);const r=await response;assert(r.ok());sessions[username]=await r.json();assert.equal(r.headers()['set-cookie'],undefined);}
async function api(user,url,method='GET',data){const s=sessions[user];const r=await context.request.fetch(base+'/api'+url,{method,headers:{Authorization:`Bearer ${s.access_token}`,Origin:base,'X-CSRF-Token':s.csrf_token},data});assert(r.ok(),`${method} ${url}: ${r.status()}`);return r.json();}
async function axe(name){const report=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();await fs.writeFile(path.join(output,`axe-${name}.json`),JSON.stringify(report.violations,null,2));assert.equal(report.violations.length,0,JSON.stringify(report.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}))));}
async function noOverflow(scope){assert(await scope.locator('html').evaluate(el=>el.scrollWidth<=window.innerWidth+1),'horizontal overflow');}
async function choose(scope,label,option){await scope.getByLabel(label,{exact:true}).click();await scope.getByRole('option',{name:option,exact:true}).click();}
try{
 await step('two independent phone logins and private photo loading',async()=>{
  await page.goto(base+'/stage');await login(visitor,'aoi');await login(provider,'forest');
  await click('みんなの記録',visitor);await expect(visitor.locator('.post-card').first()).toBeVisible();await expect(provider.locator('.provider-workspace')).toBeVisible();
  const photo=visitor.locator('.post-card img').first();await expect.poll(()=>photo.evaluate(i=>i.complete&&i.naturalWidth>0)).toBe(true);assert((await photo.getAttribute('src')).startsWith('blob:'));
  assert.equal((await context.cookies()).length,0);assert.notEqual(sessions.aoi.user.id,sessions.forest.user.id);
  assert.equal(await visitor.locator('select').count(),0);assert.equal(await provider.locator('select').count(),0);
  await noOverflow(visitor);await noOverflow(provider);await page.screenshot({path:path.join(output,'stage-initial.png'),fullPage:true});
 });
 await step('travel conversation creates only an unconfirmed condition draft',async()=>{
  await click('旅を見つける',visitor);await click('旅を計画',visitor);await visitor.getByLabel('旅の名前',{exact:true}).fill('高原で過ごす、同期の週末');
  const created=page.waitForResponse(r=>r.url().endsWith('/travel-parties')&&r.request().method()==='POST');await click('旅の計画をつくる',visitor);partyId=(await (await created).json()).id;
  await visitor.getByLabel('講のメンバーとの会話に送るメッセージ').fill('6人で2泊3日、1人3万円くらいで森とカフェに行こう。内輪の集合相談。');await click('送る',visitor);
  await expect(visitor.locator('.message').last()).toContainText('内輪の集合相談');await click('最近の会話から条件を整理',visitor);
  await expect(visitor.getByRole('heading',{name:'旅行条件を確かめる'})).toBeVisible();assert.equal((await api('aoi',`/travel-parties/${partyId}`)).requirements,null);
  await click('予算に 30,000円を使う',visitor);await visitor.getByLabel('出発日の希望',{exact:false}).fill('2026-12-12');
  await click('この旅行条件で確定する',visitor);await expect(visitor.locator('.requirements-summary')).toContainText('6人');
  await expect(visitor.locator('.party-header')).toContainText('アカウント 1人');
 });
 await step('matching reasons and explicit selection gate',async()=>{
  const before=(await api('forest','/consultations')).items.map(c=>c.id);
  await click('条件から候補を探す',visitor);await expect(visitor.locator('.market-plan-card')).toHaveCount(1);await expect(visitor.locator('.market-plan-card')).toContainText('6人で森とカフェ');
  await click('日別の行程を見る',visitor);const detail=visitor.getByRole('dialog');await expect(detail).toContainText('交通費');await expect(detail).toContainText('3日目');await click('共有する内容を確認',detail);
  const preview=visitor.getByRole('dialog');await expect(preview).not.toContainText('内輪の集合相談');await expect(preview.getByRole('button',{name:'この内容で相談を送る'})).toBeDisabled();
  assert.deepEqual((await api('forest','/consultations')).items.map(c=>c.id),before);
  await preview.getByLabel('最初に相談したいこと').fill('6人で森の散策とカフェを楽しみたいです。集合時間を相談できますか。');await preview.getByRole('checkbox').check();
  const selected=page.waitForResponse(r=>r.url().endsWith('/selections')&&r.request().method()==='POST');await click('この内容で相談を送る',preview);consultationId=(await (await selected).json()).id;
  await expect(page.locator('.stage-activity')).toContainText('選んだ事業者に相談が届く');
  const record=await api('forest',`/consultations/${consultationId}`);assert(!JSON.stringify(record).includes('内輪の集合相談'));assert(!('interests' in record.selection.shared_conditions));
 });
 await step('provider receives selected plan and sends an actual reply',async()=>{
  await click('届いた相談',provider);
  const refreshed=page.waitForResponse(r=>r.url().endsWith('/api/consultations')&&r.request().method()==='GET');
  await click('更新',provider);const rows=(await (await refreshed).json()).items;
  const selectedRow=rows.findIndex(c=>c.id===consultationId);assert(selectedRow>=0);
  await expect(provider.getByRole('button',{name:'更新',exact:true})).toBeEnabled();
  await provider.locator('.consultation-row').nth(selectedRow).click();const dialog=provider.getByRole('dialog');
  await expect(dialog).toContainText('集合時間を相談');await expect(dialog).not.toContainText('内輪の集合相談');
  await dialog.getByLabel('旅行者との相談に送るメッセージ').fill('ご相談ありがとうございます。初日は13時集合で、森の散策から始める行程をご案内できます。');await click('送る',dialog);
  await expect(dialog.locator('.message').last()).toContainText('13時集合');await click('閉じる',dialog);
  await visitor.locator('.consultation-row').first().click();await expect(visitor.getByRole('dialog')).toContainText('13時集合');
  await page.screenshot({path:path.join(output,'stage-consultation.png'),fullPage:true});await click('閉じる',visitor.getByRole('dialog'));
 });
 await step('large group comparison and direct catalogue path',async()=>{
  await click('旅行条件',visitor);await visitor.getByLabel('予定している旅行人数').fill('35');await visitor.getByLabel('予算の目安（円・任意）').fill('900000');
  await choose(visitor,'予算の単位','全員分');await click('この旅行条件で確定する',visitor);await click('条件から候補を探す',visitor);
  await expect(visitor.locator('.market-plan-card')).toHaveCount(1);await expect(visitor.locator('.market-plan-card')).toContainText('30人からの海辺');
  await visitor.getByText('条件に合わなかったプランを確認',{exact:true}).click();await expect(visitor.locator('.mismatch-details')).toContainText('人数');
  await click('事業者の全プラン',visitor);assert((await visitor.locator('.market-plan-card').count())>=3);
  // Restore the six-person consultation scenario for the visible demonstration.
  await click('旅行条件',visitor);await visitor.getByLabel('予定している旅行人数').fill('6');await visitor.getByLabel('予算の目安（円・任意）').fill('30000');await choose(visitor,'予算の単位','1人あたり');await click('この旅行条件で確定する',visitor);
 });
 await step('provider drafts and publishes a plan with a real day itinerary',async()=>{
  await click('自社のプラン',provider);await click('プランをつくる',provider);const d=provider.getByRole('dialog');
  await d.getByLabel('プランの名前',{exact:true}).fill('午後の森とコーヒー');await d.getByLabel('紹介',{exact:true}).fill('仲間と歩いたあと、喫茶室でゆっくり過ごす午後。');await d.getByLabel('泊数',{exact:true}).fill('0');await d.getByLabel('概算費用（円）').fill('6000');await d.getByLabel('含むもの・含まないもの').fill('散策と喫茶代の概算。出発地からの交通費は含みません。');await d.getByLabel('店・場所の名前').fill('森の喫茶室');await d.getByLabel('ここでできること').fill('散策後にコーヒーを楽しむ。');
  const saved=page.waitForResponse(r=>/\/providers\/[^/]+\/plans$/.test(new URL(r.url()).pathname)&&r.request().method()==='POST');await click('下書きに保存',d);createdPlanId=(await (await saved).json()).id;
  assert(!(await api('aoi','/provider-plans')).items.some(p=>p.id===createdPlanId));
  const card=provider.locator('.market-plan-card').filter({hasText:'午後の森とコーヒー'}).filter({has:provider.getByRole('button',{name:'プランを編集する'})}).last();
  const own=provider.locator('.provider-plan-list > div').filter({hasText:'下書き'}).filter({hasText:'午後の森とコーヒー'}).last();
  await click('プランを編集する',own);
  const published=page.waitForResponse(r=>r.url().endsWith(`/provider-plans/${createdPlanId}`)&&r.request().method()==='PATCH');
  await click('この内容で公開する',provider.getByRole('dialog'));assert.equal((await (await published).json()).status,'published');
  await expect(provider.getByRole('dialog')).not.toBeVisible();
  assert((await api('aoi','/provider-plans')).items.some(p=>p.id===createdPlanId));
 });
 await step('two phone accessibility, reduced motion and no horizontal overflow',async()=>{
  await click('旅を見つける',visitor);await noOverflow(page);await noOverflow(visitor);await noOverflow(provider);await axe('stage');
  await page.emulateMedia({reducedMotion:'reduce'});const animation=await page.locator('.hub-symbol > span').first().evaluate(el=>getComputedStyle(el,'::after').animationName);assert.equal(animation,'none');
  await page.screenshot({path:path.join(output,'stage-final.png'),fullPage:true});
 });
 await step('mobile 390 and 320, enlarged type and keyboard choice',async()=>{
  const p=await context.newPage();p.on('pageerror',e=>errors.push(e.message));await p.setViewportSize({width:390,height:844});await p.goto(base+'/stage/visitor');
  await p.getByRole('radio',{name:/aoi/}).check();await p.getByLabel('パスワード',{exact:true}).fill('aoi-local-2026');await click('ログイン',p);await click('旅を見つける',p);await expect(p.locator('.market-plan-card').first()).toBeVisible();await noOverflow(p);await p.screenshot({path:path.join(output,'mobile-390.png'),fullPage:true});
  await p.setViewportSize({width:320,height:740});await noOverflow(p);await p.screenshot({path:path.join(output,'mobile-320.png'),fullPage:true});
  await p.setViewportSize({width:390,height:844});await p.evaluate(()=>document.documentElement.style.fontSize='200%');await noOverflow(p);await p.evaluate(()=>document.documentElement.style.fontSize='');
  const choice=p.getByLabel('旅行の計画',{exact:true});await choice.focus();await p.keyboard.press('ArrowDown');await expect(p.getByRole('listbox')).toBeVisible();await p.keyboard.press('End');await p.keyboard.press('Escape');await expect(choice).toBeFocused();await p.close();
 });
 await step('no external network requests or browser errors',async()=>{assert.deepEqual(external,[]);assert.deepEqual(errors,[]);});
}finally{
 if(createdPlanId&&sessions.forest){try{const plan=await api('forest',`/provider-plans/${createdPlanId}`);const{id,provider,source_note,...body}=plan;await api('forest',`/provider-plans/${id}`,'PATCH',{...body,status:'archived'});}catch(e){results.push({name:'archive only this QA-created provider plan',status:'failed',message:String(e.message)});}}
 await fs.writeFile(path.join(output,'results.json'),JSON.stringify({time:new Date().toISOString(),url:base,results,externalRequests:external,browserErrors:errors,syntheticRecords:{partyId,consultationId,createdPlanId}},null,2));await browser.close();
}
