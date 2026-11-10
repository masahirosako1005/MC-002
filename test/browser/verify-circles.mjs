import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(path.join(root,'test/browser/package.json'));
const {chromium,expect}=require('@playwright/test');
const AxeBuilder=require('@axe-core/playwright').default;
const out=path.join(root,'artifacts/browser/circles');await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:900},locale:'ja-JP'});
const base='http://127.0.0.1:8081',sessions={},results=[],external=[],errors=[],created=[];
const title='森の旅の確認 '+Date.now();let circleId,invitationId;
await context.route('**/*',async r=>{if(new URL(r.request().url()).hostname!=='127.0.0.1'){external.push(new URL(r.request().url()).origin);await r.abort();}else await r.continue();});
const page=await context.newPage();page.on('pageerror',e=>errors.push(e.name));
const left=page.frameLocator('iframe[title="利用者のスマートフォン画面"]'),right=page.frameLocator('iframe[title="事業者のパソコン管理画面"]');
async function click(scope,name){await scope.getByRole('button',{name,exact:true}).click();}
async function login(host,scope,user){await scope.getByLabel('アカウント名',{exact:true}).fill(user);await scope.getByLabel('パスワード',{exact:true}).fill(user+'-local-2026');const response=host.waitForResponse(r=>r.url().endsWith('/stage/login')&&r.request().method()==='POST');await click(scope,'ログイン');sessions[user]=await(await response).json();await expect(scope.locator('.app-shell')).toBeVisible();}
async function api(user,url,method='GET',data,expected=200){const s=sessions[user],r=await context.request.fetch(base+'/api'+url,{method,headers:{Authorization:`Bearer ${s.access_token}`,Origin:base,'X-CSRF-Token':s.csrf_token},data});assert.equal(r.status(),expected,`${url}: ${r.status()} ${await r.text()}`);return r.json();}
async function step(name,fn){await fn();results.push(name);console.log('PASS '+name);}
async function create(scope,mode,name,people){await scope.getByRole('button',{name:mode==='manual'?/仲間を選んでつくる/:/関心から仲間を探す/}).click();const d=scope.getByRole('dialog');await d.getByLabel('講の名前',{exact:true}).fill(name);if(mode==='recommended'){await d.getByRole('button',{name:'カフェ',exact:true}).click();await click(d,'この関心で候補を探す');await expect(d.locator('.circle-member-option').first()).toBeVisible();}for(const person of people)await d.locator('.circle-member-option').filter({hasText:person}).getByRole('checkbox').check();const response=page.waitForResponse(r=>r.url().endsWith('/api/circles')&&r.request().method()==='POST');await click(d,'講をつくって招待を送る');const result=await(await response).json();assert(result.id);created.push(result.id);await expect(scope.getByRole('heading',{name,exact:true})).toBeVisible();return result;}
async function noOverflow(scope){assert(await scope.locator('html').evaluate(el=>el.scrollWidth<=innerWidth+1));}
try{
 await page.goto(base+'/stage');await login(page,left,'aoi');await login(page,right,'forest');await click(left,'講を見つける');
 await step('two creation routes preserve pending member consent',async()=>{
  const suggested=await create(left,'recommended',title+' 関心',['高橋 蓮']);assert.equal(suggested.accepted_count,1);assert.equal(suggested.pending_count,1);await click(left,'← 講の一覧へ');
  const manual=await create(left,'manual',title,['高橋 蓮','小野 美緒']);circleId=manual.id;assert.equal(manual.accepted_count,1);assert.equal(manual.pending_count,2);
  await left.getByLabel('講の内輪の会話に送るメッセージ').fill('仲間だけで集合の希望を話します。');await click(left,'送る');await expect(left.locator('.message').last()).toContainText('仲間だけで');
 });
 await step('invitees independently accept or decline and private history stays protected',async()=>{
  for(const [user,decision] of [['ren','この講に参加する'],['mio','今回は見送る']]){const p=await context.newPage();await p.goto(base+'/stage/visitor');await login(p,p,user);await api(user,`/circles/${circleId}`,'GET',undefined,404);await click(p,'講を見つける');const card=p.locator('.circle-invitation-card').filter({has:p.getByRole('heading',{name:title,exact:true})});await click(card,decision);await expect(card).toHaveCount(0);await p.close();}
  await click(left,'講を更新');const circle=await api('aoi',`/circles/${circleId}`);assert.equal(circle.accepted_count,2);assert.equal(circle.pending_count,0);await api('mio',`/circles/${circleId}`,'GET',undefined,404);await api('forest',`/circles/${circleId}`,'GET',undefined,404);
 });
 await step('multi-turn guidance requires explicit condition confirmation',async()=>{
  await click(left,'AIに相談');for(const body of ['6人で2泊3日、森とカフェに行きたい','1人3万円で、プラン部分の予算です。2026-12-12に出発します。']){await left.getByLabel('案内役に相談する').fill(body);await click(left,'この希望を伝える');await expect(left.locator('.circle-question').last()).toContainText(body);}
  const turns=await api('aoi',`/circles/${circleId}/assistant-turns`);assert.equal(turns.items.length,2);assert.equal((await api('aoi',`/circles/${circleId}`)).requirements,null);
  await left.getByRole('button',{name:'この候補を確認・訂正する',exact:true}).last().click();const d=left.getByRole('dialog',{name:'旅行条件を確認する'});await d.getByLabel('予定している旅行人数',{exact:true}).fill('6');await d.getByLabel('泊数',{exact:true}).fill('2');await d.getByLabel(/予算の目安/).fill('30000');
  for(const [label,option] of [['予算の単位','1人あたり'],['どこまで含む予算？','選ぶプラン部分']]){await d.getByLabel(label,{exact:true}).click();await d.getByRole('option',{name:option,exact:true}).click();}
  await d.getByLabel(/出発日の希望/).fill('2026-12-12');await click(d,'この旅行条件で確定する');await expect(d).toHaveCount(0);const circle=await api('aoi',`/circles/${circleId}`);assert.equal(circle.requirements.planned_people,6);assert.equal(circle.requirements.version,1);await page.screenshot({path:path.join(out,'confirmed-conditions.png')});
 });
 await step('explicit destination sharing then actual provider acceptance opens shared room',async()=>{
  await click(left,'おすすめを更新');const card=left.locator('.market-plan-card').filter({hasText:'森とカフェ'}).first();await expect(card).toBeVisible();await card.getByRole('button',{name:'講に追加',exact:true}).click();await click(left.getByRole('dialog',{name:'講に候補を追加する'}),'候補を保存して講で話す');await left.locator('.saved-candidate').filter({hasText:'森とカフェ'}).getByRole('button',{name:'候補の詳細を見る',exact:true}).click();const detail=left.getByRole('dialog');await detail.getByRole('button',{name:/事業者を招く|この行き先/}).click();const d=left.getByRole('dialog',{name:'行き先を決めて、事業者を招く'});await d.getByLabel('事業者に伝える希望').fill('午後に集まり、森とカフェを巡る行程を相談したいです。');await d.getByRole('checkbox').check();await click(d,'この行き先で事業者を招く');await expect(d).toHaveCount(0);
  let circle=await api('aoi',`/circles/${circleId}`);invitationId=circle.active_provider_invitation.id;assert.equal(circle.active_provider_invitation.status,'pending');assert.equal(circle.active_provider_invitation.consultation_id,null);await api('forest',`/circle-provider-invitations/${invitationId}/room`,'GET',undefined,404);
  await click(right,'講への招待');const invite=right.locator('.circle-invitation-card').filter({hasText:'午後に集まり'});await click(invite,'招待を承諾して参加');await expect(right.getByRole('dialog',{name:'講の共有相談'})).toBeVisible();const room=await api('forest',`/circle-provider-invitations/${invitationId}/room`);assert(!JSON.stringify(room).includes('仲間だけで集合'));assert.equal(room.reservation_status,'not_booked');await click(left,'講を更新');await click(left,'この講で事業者と話す');
 });
 await step('actual two-way messages and revised estimates retain independent confirmations',async()=>{
  const ld=left.getByRole('dialog',{name:'講の共有相談'}),rd=right.getByRole('dialog',{name:'講の共有相談'});
  await ld.getByLabel('講の共有相談に送るメッセージ').fill('午後の集合を希望しています。');await click(ld,'送る');await expect(page.locator('.stage-connection')).toHaveAttribute('data-direction','visitor-to-provider');await click(rd,'会話と提案を更新');await expect(rd.locator('.message').last()).toContainText('午後の集合');
  await rd.getByLabel('講の共有相談に送るメッセージ').fill('13時の集合で行程を提案します。');await click(rd,'送る');await expect(page.locator('.stage-connection')).toHaveAttribute('data-direction','provider-to-visitor');await click(rd,'行程・見積をつくる');const editor=right.getByRole('dialog',{name:'行程と見積を提案する'});await editor.getByLabel('提案の名前').fill('森とカフェの集合案');await editor.getByLabel('含む費用・含まない費用').fill('プラン内の体験費用。出発地からの交通費は含みません。');await editor.getByLabel(/未確認事項/).fill('空席と交通手配は未確定');await click(editor,'この行程と見積を共有する');await expect(editor).toHaveCount(0);await click(rd,'第1版の内容を確認する');await click(ld,'会話と提案を更新');await click(ld,'第1版の内容を確認する');await expect.poll(async()=>(await api('aoi',`/circle-provider-invitations/${invitationId}/room`)).proposal.status).toBe('both_confirmed');
  await click(rd,'行程・見積を改訂');const revise=right.getByRole('dialog',{name:'行程と見積を改訂する'});await revise.getByLabel('提案の名前').fill('森とカフェの集合案・改訂');await click(revise,'この行程と見積を共有する');await expect(revise).toHaveCount(0);const room=await api('aoi',`/circle-provider-invitations/${invitationId}/room`);assert.equal(room.proposal.version,2);assert.equal(room.proposal.confirmations.length,0);assert.equal(room.reservation_status,'not_booked');await click(ld,'会話と提案を更新');await page.screenshot({path:path.join(out,'shared-estimate.png')});
 });
 await step('accessible shared conversation remains usable at 320px and enlarged text',async()=>{
  const scan=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();await fs.writeFile(path.join(out,'axe.json'),JSON.stringify(scan.violations,null,2));assert.equal(scan.violations.length,0,JSON.stringify(scan.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}))));
  const p=await context.newPage();await p.goto(base+'/stage/provider');await login(p,p,'forest');await click(p,'講への招待');await p.locator('.circle-invitation-card').filter({hasText:'午後に集まり'}).getByRole('button',{name:/共有/}).click();for(const width of [390,320]){await p.setViewportSize({width,height:844});await noOverflow(p);await p.screenshot({path:path.join(out,`shared-${width}.png`)});}await p.locator('html').evaluate(el=>el.style.fontSize='200%');await noOverflow(p);const d=p.getByRole('dialog');await expect(d.locator('.message-form')).toBeInViewport();await d.locator('.conversation-history').focus();await d.locator('.conversation-history').press('Home');await click(d,'閉じる');assert.notEqual(await p.locator('html').evaluate(el=>getComputedStyle(el).overflow),'hidden');await p.emulateMedia({reducedMotion:'reduce'});await p.close();assert.equal(external.length,0);assert.equal(errors.length,0);
 });
}catch(e){results.push({failed:String(e.message).slice(0,1800)});await page.screenshot({path:path.join(out,'failure.png')});process.exitCode=1;}
finally{let cleanup=true;for(const id of created){try{const circle=await api('aoi',`/circles/${id}`);if(circle.status==='open')await api('aoi',`/circles/${id}/close`,'POST',{version:circle.version});}catch{cleanup=false;}}const result={checkedAt:new Date().toISOString(),results,external,errors,cleanup,passed:results.length===6&&results.every(r=>typeof r==='string')&&cleanup};await fs.writeFile(path.join(out,'browser.json'),JSON.stringify(result,null,2));await fs.writeFile(path.join(out,`browser-${Date.now()}.json`),JSON.stringify(result,null,2));await browser.close();}
