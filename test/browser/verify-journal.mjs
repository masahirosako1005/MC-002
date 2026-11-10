import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(path.join(root,'test/browser/package.json'));
const {chromium,expect}=require('@playwright/test');
const AxeBuilder=require('@axe-core/playwright').default;
const out=path.join(root,'artifacts/browser/journal');
await fs.mkdir(out,{recursive:true});
const stamp=new Date().toISOString().replaceAll(':','-');
const base='http://127.0.0.1:8081', results=[], errors=[], external=[], sessions={};
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:900},locale:'ja-JP',timezoneId:'Asia/Tokyo'});
await context.route('**/*',async route=>{const u=new URL(route.request().url());if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.origin);await route.abort();}else await route.continue();});
const page=await context.newPage();page.on('pageerror',e=>errors.push(e.name));
const visitor=page.frameLocator('iframe[title="利用者のスマートフォン画面"]');
const provider=page.frameLocator('iframe[title="事業者のパソコン管理画面"]');
let postId,journeyId,originalSharing,memberPage;
const title='秋の東海をめぐる旅 '+stamp.slice(11,19), caption='旅の地図を確かめる写真 '+stamp;
async function click(scope,name){const list=scope.getByRole('button',{name,exact:true});await expect.poll(async()=>{for(let i=0;i<await list.count();i++)if(await list.nth(i).isVisible())return true;return false;},{timeout:15000}).toBe(true);for(let i=0;i<await list.count();i++){if(await list.nth(i).isVisible()){await list.nth(i).click();return;}}throw new Error('Visible button not found: '+name);}
async function choose(scope,label,value){await scope.getByLabel(label,{exact:true}).click();await scope.getByRole('option',{name:value,exact:true}).click();}
async function login(host,scope,user){await scope.getByLabel('アカウント名',{exact:true}).fill(user);await scope.getByLabel('パスワード',{exact:true}).fill(user+'-local-2026');const pending=host.waitForResponse(r=>r.url().endsWith('/stage/login')&&r.request().method()==='POST');await click(scope,'ログイン');const r=await pending;assert(r.ok());sessions[user]=await r.json();await expect(scope.locator('.app-shell')).toBeVisible();}
async function api(user,url,method='GET',data){const s=sessions[user];const r=await context.request.fetch(base+'/api'+url,{method,headers:{Authorization:`Bearer ${s.access_token}`,Origin:base,'X-CSRF-Token':s.csrf_token},data});assert(r.ok(),`${method} ${url}: ${r.status()}`);return r.json();}
async function step(name,fn){try{await fn();results.push({name,passed:true});console.log('PASS '+name);}catch(e){results.push({name,passed:false,error:String(e.message).slice(0,1200)});await page.screenshot({path:path.join(out,`failure-${stamp}.png`),fullPage:true});throw e;}}
async function noOverflow(scope){assert(await scope.locator('html').evaluate(el=>el.scrollWidth<=window.innerWidth+1),'horizontal overflow');}
async function axe(host,name){const a=await new AxeBuilder({page:host}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();await fs.writeFile(path.join(out,`axe-${name}.json`),JSON.stringify(a.violations,null,2));assert.equal(a.violations.length,0,JSON.stringify(a.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}))));}
try {
 await step('EXIF opt-in before upload; published photo remains independently shared',async()=>{
  await page.goto(base+'/stage');await login(page,visitor,'aoi');await login(page,provider,'forest');
  originalSharing=(await api('aoi','/journal/profile/u-aoi')).share_achievements;
  await click(visitor,'みんなの記録');await click(visitor,'投稿');
  const d=visitor.getByRole('dialog');const opt=d.getByRole('checkbox',{name:/これから選ぶ写真の位置情報/});await expect(opt).not.toBeChecked();await opt.check();
  const uploaded=page.waitForResponse(r=>r.url().includes('/api/media?read_location=true')&&r.request().method()==='POST');
  await d.locator('input[type=file]').setInputFiles(path.join(root,'test/fixtures/journal-gps.jpg'));
  const photo=await (await uploaded).json();assert(photo.location_candidate);assert(Math.abs(photo.location_candidate.latitude-35.1856)<.00001);
  await d.getByLabel('旅のひとこと',{exact:true}).fill(caption);
  await d.getByRole('checkbox',{name:/写真とタグを確認しました/}).check();
  const created=page.waitForResponse(r=>r.url().endsWith('/api/posts')&&r.request().method()==='POST');
  await click(d,'このコミュニティに公開');postId=(await (await created).json()).id;
  await expect(d).toHaveCount(0);await expect(visitor.locator('.post-card').filter({hasText:caption})).toBeVisible();
 });
 await step('photo to confirmed visit and saved journey map',async()=>{
  await click(visitor.locator('.post-card').filter({hasText:caption}),'旅の地図に残す');const d=visitor.getByRole('dialog');
  await expect(d.getByText('写真に位置情報がありました',{exact:true})).toBeVisible();
  await d.getByLabel('旅の名前',{exact:true}).fill(title);await choose(d,'訪れた都道府県','愛知県');
  await d.getByLabel('訪れた日',{exact:true}).fill('2026-11-01');await d.getByLabel('訪れた場所',{exact:true}).fill('名古屋城の庭園');
  await click(d,'写真に記録された位置');await expect(d.getByRole('button',{name:'自分だけ',exact:true})).toHaveAttribute('aria-pressed','true');
  await click(d,'コミュニティ');await expect(d.getByRole('button',{name:'訪問記録を保存',exact:true})).toBeDisabled();
  await d.getByRole('checkbox',{name:/この日に自分が訪れた場所/}).check();
  const saved=page.waitForResponse(r=>r.url().endsWith('/api/journal/visits')&&r.request().method()==='POST');await click(d,'訪問記録を保存');const visit=await (await saved).json();journeyId=visit.journey_id;
  assert.equal(visit.source,'exif');await expect(visitor.locator('.journal-visit').filter({hasText:'名古屋城の庭園'})).toBeVisible();
  await expect(visitor.locator('.journey-map svg[role=img]')).toBeVisible();assert.equal((await api('aoi','/journal/profile/u-aoi')).badges[0].earned,false);
 });
 await step('manual locations without GPS complete the four-prefecture badge',async()=>{
  for(const [prefecture,place] of [['岐阜県','長良川の散歩道'],['三重県','伊勢のまち歩き'],['静岡県','海辺の遊歩道']]){
   await click(visitor,'訪問記録を残す');const d=visitor.getByRole('dialog');await choose(d,'残す旅',title);
   await click(d,'写真なし');await choose(d,'訪れた都道府県',prefecture);await d.getByLabel('訪れた日',{exact:true}).fill('2026-11-02');await d.getByLabel('訪れた場所',{exact:true}).fill(place);
   await d.getByRole('checkbox',{name:/この日に自分が訪れた場所/}).check();await click(d,'訪問記録を保存');await expect(d).toHaveCount(0);await expect(visitor.locator('.journal-visit').filter({hasText:place})).toBeVisible();
  }
  await expect(visitor.locator('.journal-badge.earned')).toContainText('4 / 4県');
  const own=await api('aoi','/journal/profile/u-aoi');assert.equal(own.badges[0].earned,true);assert.equal(own.badges[0].achieved_count,4);
  await page.screenshot({path:path.join(out,'stage-map.png'),fullPage:true});
 });
 await step('achievement sharing and another member profile do not reveal exact locations',async()=>{
  await click(visitor,'旅のプロフィール');const d=visitor.getByRole('dialog');const sharing=d.getByRole('checkbox',{name:'県別の実績とバッジを共有する',exact:true});if(!await sharing.isChecked())await sharing.click();await expect(d).toContainText('現在：同じコミュニティに公開');await click(d,'閉じる');
  memberPage=await context.newPage();memberPage.on('pageerror',e=>errors.push(e.name));await memberPage.goto(base+'/stage/visitor');await login(memberPage,memberPage,'ren');await click(memberPage,'旅の地図');await click(memberPage,'仲間の旅を見てみる');await memberPage.locator('.journal-person').filter({hasText:'藤沢 葵'}).click();
  const profile=memberPage.getByRole('dialog');await expect(profile.locator('.journal-badge.earned')).toBeVisible();await expect(profile).toContainText('名古屋城の庭園');await expect(profile).not.toContainText('長良川の散歩道');
  const shared=await api('ren','/journal/profile/u-aoi');assert.equal(shared.badges[0].earned,true);assert.equal(shared.shared_visits.length,1);assert.equal(shared.shared_visits[0].latitude,null);assert.equal(shared.shared_visits[0].longitude,null);assert.equal(shared.shared_visits[0].media_id,null);assert(shared.shared_visits[0].media_url);
  const photo=profile.locator('.journal-visit img');await expect.poll(()=>photo.evaluate(img=>img.complete&&img.naturalWidth>0)).toBe(true);
  await memberPage.screenshot({path:path.join(out,'member-profile.png'),fullPage:true});await axe(memberPage,'profile');
 });
 await step('visit correction and deletion update saved badge progress',async()=>{
  const card=visitor.locator('.journal-visit').filter({hasText:'海辺の遊歩道'});await click(card,'記録を編集');let d=visitor.getByRole('dialog');await d.getByLabel('訪れた場所',{exact:true}).fill('静岡の海辺の遊歩道');await d.getByRole('checkbox',{name:/この日に自分が訪れた場所/}).check();await click(d,'変更を保存');await expect(d).toHaveCount(0);
  await click(visitor.locator('.journal-visit').filter({hasText:'静岡の海辺の遊歩道'}),'削除');d=visitor.getByRole('dialog');await expect(d).toContainText('実績とバッジも再計算');await click(d,'削除する');await expect(d).toHaveCount(0);await expect(visitor.locator('.journal-badge')).toContainText('3 / 4県');assert.equal((await api('ren','/journal/profile/u-aoi')).badges[0].earned,false);
 });
 await step('two-phone layout, keyboard, narrow widths and reduced motion',async()=>{
  await noOverflow(page);await noOverflow(visitor);await noOverflow(provider);assert.equal(await page.locator('select').count(),0);assert.equal(await visitor.locator('select').count(),0);await axe(page,'stage');
  await click(visitor,'訪問記録を残す');const d=visitor.getByRole('dialog');const choice=d.getByLabel('訪れた都道府県',{exact:true});await choice.focus();await choice.press('ArrowDown');await d.getByRole('option',{name:'都道府県を選ぶ',exact:true}).press('End');await d.getByRole('option',{name:'沖縄県',exact:true}).press('Enter');await expect(choice).toContainText('沖縄県');await click(d,'閉じる');
  await click(memberPage.getByRole('dialog'),'閉じる');
  for(const width of [390,320]){await memberPage.setViewportSize({width,height:844});await noOverflow(memberPage);await memberPage.screenshot({path:path.join(out,`narrow-${width}.png`),fullPage:true});}
  await memberPage.locator('html').evaluate(el=>el.style.fontSize='200%');await noOverflow(memberPage);await memberPage.locator('html').evaluate(el=>el.style.fontSize='');
  await page.emulateMedia({reducedMotion:'reduce'});assert.equal(await visitor.locator('select').count(),0);
  assert.equal(external.length,0);assert.equal(errors.length,0);assert.equal(await page.locator('.stage-connection').getAttribute('data-transfer-count'),'0');
 });
} finally {
 let cleanup=true;
 try {
  if(sessions.aoi&&originalSharing!==undefined){const profile=await api('aoi','/journal/profile/u-aoi');if(profile.share_achievements!==originalSharing)await api('aoi','/journal/profile','PUT',{share_achievements:originalSharing,version:profile.version});}
  if(journeyId){const j=await api('aoi',`/journal/journeys/${journeyId}`);await api('aoi',`/journal/journeys/${journeyId}`,'DELETE',{version:j.journey.version});}
  if(postId)await api('aoi',`/posts/${postId}`,'DELETE',{});
 }catch{cleanup=false;}
 const report={checkedAt:new Date().toISOString(),scope:'Isolated headless Edge; synthetic test photo and visits; not ordinary Edge repair or physical travel verification',results,errors,external,cleanup,passed:results.length===6&&results.every(r=>r.passed)&&cleanup};
 await fs.writeFile(path.join(out,`browser-${stamp}.json`),JSON.stringify(report,null,2));await fs.writeFile(path.join(out,'browser.json'),JSON.stringify(report,null,2));await browser.close();if(!report.passed)process.exitCode=1;
}
