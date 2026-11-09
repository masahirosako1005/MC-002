import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(path.join(root,'qa/package.json'));
const {chromium,expect}=require('@playwright/test');
const AxeBuilder=require('@axe-core/playwright').default;
const out=path.join(root,'community/artifacts/reflections');await fs.mkdir(out,{recursive:true});
const base='http://127.0.0.1:8081',run=Date.now();
const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const positive='この事業者の案内は分かりやすかった。';
const negative='この事業者の案内は分かりにくかった。';
const fixtures=[],sessions={},results=[],external=[],errors=[],layout=[];
let main,providerPlan,reflectionId,messageId;
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:900},locale:'ja-JP',timezoneId:'Asia/Tokyo'});
await context.route('**/*',async r=>{const url=new URL(r.request().url());if(url.hostname!=='127.0.0.1'){external.push(url.origin);await r.abort();}else await r.continue();});
context.on('page',p=>p.on('pageerror',e=>errors.push(e.name)));
const page=await context.newPage(),left=page.frameLocator('iframe[title="旅行者の操作画面"]'),right=page.frameLocator('iframe[title="事業者の操作画面"]');
async function click(scope,name){await scope.getByRole('button',{name:name==='旅を見つける'?/^(旅を見つける|旅を探す)$/:name,exact:true}).click();}
async function choose(scope,label,name){await scope.getByLabel(label,{exact:true}).click();await scope.getByRole('option',{name,exact:true}).click();}
async function login(host,scope,user){
  await scope.getByLabel('アカウント名',{exact:true}).fill(user);await scope.getByLabel('パスワード',{exact:true}).fill(user+'-local-2026');
  const response=host.waitForResponse(r=>r.url().endsWith('/stage/login')&&r.request().method()==='POST');await click(scope,'ログイン');sessions[user]=await(await response).json();await expect(scope.locator('.app-shell')).toBeVisible();
}
async function api(user,url,method='GET',data){const s=sessions[user],r=await context.request.fetch(base+'/api'+url,{method,headers:{Authorization:`Bearer ${s.access_token}`,Origin:base,'X-CSRF-Token':s.csrf_token},data});assert.equal(r.status(),200,`${method} ${url}: ${r.status()}`);return r.json();}
async function step(name,fn){await fn();results.push(name);console.log('PASS '+name);}
function key(label){return `${run}-${label}`;}
async function ownParticipation(user,rid){let r=await api(user,`/reflections/${rid}`);r=await api(user,`/reflections/${rid}/participation`,'PUT',{used_service:true,version:r.my_state.version});return api(user,`/reflections/${rid}/consent`,'PUT',{allowed:true,version:r.my_state.version});}
async function setupCircle(user,extra=false){
  const title=`森を歩いた旅 ${run} ${user}`;
  let c=await api(user,'/circles','POST',{community_id:'peers',title,mode:'manual',tags:['nature'],desired_count:2,invitee_ids:extra?['u-ren']:[],client_request_id:key('circle-'+user)});
  const fixture={owner:user,circleId:c.id,title,reflectionId:null};fixtures.push(fixture);
  if(extra){const list=await api('ren','/circles');const invitation=list.invitations.find(i=>i.circle_id===c.id);assert(invitation);await api('ren',`/circle-invitations/${invitation.id}/respond`,'POST',{decision:'accepted',version:invitation.version,client_request_id:key('join')});}
  const people=Math.min(providerPlan.max_people,Math.max(providerPlan.min_people,6));
  const req=await api(user,`/travel-parties/${c.id}/requirements`,'PUT',{planned_people:people,nights:providerPlan.nights,budget_yen:100000,budget_basis:'per_person',budget_scope:providerPlan.price_scope,date_start:null,interests:['nature'],departure_label:'',version:0});
  c=await api(user,`/circles/${c.id}`);
  const invitation=await api(user,`/circles/${c.id}/provider-invitations`,'POST',{plan_id:providerPlan.id,plan_version:providerPlan.version,requirements_version:req.requirements.version,share_note:'森の散策について相談します。',sharing_confirmed:true,version:c.version,client_request_id:key('provider-'+user)});
  await api('forest',`/circle-provider-invitations/${invitation.id}/respond`,'POST',{decision:'accepted',version:invitation.version,client_request_id:key('accepted-'+user)});
  fixture.invitationId=invitation.id;return fixture;
}
async function setupReferenceTrip(user){const f=await setupCircle(user);const r=await api(user,`/circles/${f.circleId}/reflections`,'POST',{invitation_id:f.invitationId,ended_on:today,trip_finished:true,client_request_id:key('reflection-'+user)});f.reflectionId=r.id;await ownParticipation(user,r.id);await api(user,`/reflections/${r.id}/messages`,'POST',{body:positive,client_request_id:key('message-'+user)});}
async function openMain(scope){await click(scope,'講を見つける');await expect(scope.locator('.circles-page,.circle-workspace')).toBeVisible();const back=scope.getByRole('button',{name:/講の一覧へ/});if(await back.isVisible())await back.click();await scope.locator('.circle-list-card').filter({hasText:main.title}).click();await click(scope,'振り返り');}
async function reopenReflection(){await click(left,'旅を見つける');await openMain(left);await click(left,'この旅の振り返りをひらく');}
async function summary(){return api('aoi',`/providers/${providerPlan.provider.id}/experience-summary`);}
async function waitMessage(status){await expect.poll(async()=>{const r=await api('aoi',`/reflections/${reflectionId}`);return r.messages.find(m=>m.id===messageId)?.extraction.status;}).toBe(status);}
async function noOverflow(scope,label){
  const state=await scope.locator('html').evaluate(el=>({viewport:innerWidth,height:innerHeight,content:el.scrollWidth,font:getComputedStyle(el).fontSize,inner:[...document.querySelectorAll('dialog[open] .conversation, dialog[open] .conversation-history, dialog[open] .message-form, dialog[open] .message-form textarea, dialog[open] .message-form button')].map(node=>{const r=node.getBoundingClientRect();return {tag:node.tagName,className:node.className,client:node.clientWidth,scroll:node.scrollWidth,left:r.left,right:r.right,top:r.top,bottom:r.bottom};})}));layout.push({label,...state});
  const bad=state.content>state.viewport+1||state.inner.some(item=>item.scroll>item.client+1||item.left< -1||item.right>state.viewport+1||((item.tag==='TEXTAREA'||item.tag==='BUTTON')&&(item.top< -1||item.bottom>state.height+1)));
  if(bad){await scope.screenshot({path:path.join(out,'overflow.png'),fullPage:true});await fs.writeFile(path.join(out,'overflow.json'),JSON.stringify(state,null,2));}assert(!bad,JSON.stringify(state));
}
async function showPublicReference(){
  await click(left,'旅を見つける');await choose(left,'どの講で行く旅を探す？',main.title);
  await expect(left.locator('.plan-discovery .market-plan-card').first()).toBeVisible();
  const card=left.locator('.discovery-plan').filter({has:left.getByRole('heading',{name:providerPlan.title,exact:true})});
  for(let n=0;n<25&&!(await card.count());n++){const next=left.locator('.plan-discovery .discovery-pager').getByRole('button',{name:'次へ',exact:true});if(!(await next.count())||!(await next.isEnabled()))break;await next.click();}
  await expect(card).toBeVisible();
  const disclosure=card.locator('.discovery-card-details');
  if(await disclosure.count())await disclosure.locator(':scope > summary').click();
  return card.locator('.experience-reference');
}

try{
  await page.goto(base+'/stage');await login(page,left,'aoi');await login(page,right,'forest');
  for(const user of ['ren','mio']){const p=await context.newPage();await p.goto(base+'/stage/visitor');await login(p,p,user);await p.close();}
  providerPlan=await api('forest','/provider-plans/forest-day');
  // Two explicitly consented fixture trips exercise the minimum-publication threshold.
  // Only the third trip's user-facing workflow is the subject of the browser assertions.
  await setupReferenceTrip('ren');await setupReferenceTrip('mio');main=await setupCircle('aoi',true);
  await step('trip completion is explicit and consent starts off before any automatic analysis',async()=>{
    await openMain(left);await click(left,'旅行を終えて振り返る');
    let d=left.getByRole('dialog',{name:'旅行後の振り返りをひらく',exact:true});
    await choose(d,'振り返る事業者',`${providerPlan.provider.name} · ${providerPlan.title}`);await d.getByLabel('旅行を終えた日',{exact:true}).fill(today);
    await expect(d.getByRole('checkbox')).not.toBeChecked();await expect(d.getByRole('button',{name:'旅行終了を記録して振り返る',exact:true})).toBeDisabled();
    await d.getByRole('checkbox').check();const response=page.waitForResponse(r=>r.url().endsWith(`/circles/${main.circleId}/reflections`)&&r.request().method()==='POST');await click(d,'旅行終了を記録して振り返る');const created=await(await response).json();reflectionId=created.id;main.reflectionId=reflectionId;assert(reflectionId);await expect(d).toHaveCount(0);
    assert.equal(created.my_state.used_service,false);assert.equal(created.my_state.consented,false);assert.equal(created.ready_for_analysis,false);assert.equal(created.target_count,2);
    await expect(left.getByRole('button',{name:'参考集計への同意を確認',exact:true})).toBeDisabled();
    await ownParticipation('ren',reflectionId);await click(left,'振り返りを更新');await click(left,'この旅を振り返って話す');d=left.getByRole('dialog',{name:'旅行後の振り返り',exact:true});
    await d.getByLabel('振り返りに送るメッセージ',{exact:true}).fill(positive);await click(d,'送る');await expect(d.locator('.reflection-message').last()).toContainText('同意・利用確認待ち');
    const r=await api('aoi',`/reflections/${reflectionId}`);messageId=r.messages[0].id;assert.equal(r.messages[0].extraction.effective.length,0);await click(d,'閉じる');
  });
  await step('personal use and all-traveler consent activate clear automatic extraction',async()=>{
    await click(left,'自分が利用したことを確認');let d=left.getByRole('dialog',{name:'実際の利用を確認',exact:true});await expect(d.getByRole('checkbox')).not.toBeChecked();await d.getByRole('checkbox').check();await click(d,'自分の実利用を記録');await expect(d).toHaveCount(0);
    await click(left,'参考集計への同意を確認');d=left.getByRole('dialog',{name:'参考集計への同意',exact:true});await expect(d.getByRole('checkbox')).not.toBeChecked();await expect(d).toContainText('発言ごとの追加承認は行わず');await d.getByRole('checkbox').check();await click(d,'同意を保存');await expect(d).toHaveCount(0);await waitMessage('auto_included');
    await click(left,'この旅を振り返って話す');d=left.getByRole('dialog',{name:'旅行後の振り返り',exact:true});await expect(d.locator('.reflection-message')).toContainText('自動集計に使用中');await expect(d.locator('.reflection-message')).toContainText('肯定的');
    await page.screenshot({path:path.join(out,'automatic-extraction.png')});const scan=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();await fs.writeFile(path.join(out,'axe.json'),JSON.stringify(scan.violations,null,2));assert.equal(scan.violations.length,0,JSON.stringify(scan.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}))));await click(d,'閉じる');
    const s=await summary();assert.equal(s.status,'available');assert.equal(s.facets.find(f=>f.aspect_id==='guidance').status,'positive');
    const reference=await showPublicReference();await expect(reference).toContainText('の旅からまとめた参考集計');await expect(reference).toContainText('肯定的な体験');await expect(reference).not.toContainText(positive);await expect(reference).not.toContainText(main.title);await reference.scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,'public-reference.png')});
  });
  await step('author correction and exclusion update the reference without changing the source',async()=>{
    await reopenReflection();await click(left,'この旅を振り返って話す');const chat=left.getByRole('dialog',{name:'旅行後の振り返り',exact:true});await click(chat,'抽出結果を見直す');let d=left.getByRole('dialog',{name:'自分の抽出結果を見直す',exact:true});await click(d,'この発言を参考集計から除外');await expect(d).toHaveCount(0);await waitMessage('author_corrected');
    await expect(chat.locator('.reflection-message')).toContainText('本人が参考集計から除外');
    let r=await api('aoi',`/reflections/${reflectionId}`);assert.equal(r.messages[0].body,positive);assert(r.messages[0].extraction.effective.every(v=>v.sentiment==='excluded'));assert.equal((await summary()).status,'insufficient');
    await click(chat,'抽出結果を見直す');d=left.getByRole('dialog',{name:'自分の抽出結果を見直す',exact:true});await choose(d,'案内の分かりやすさ','肯定的');await click(d,'この訂正を保存');await expect(d).toHaveCount(0);await expect.poll(async()=>(await summary()).status).toBe('available');await expect(chat.locator('.reflection-message')).toContainText('本人が訂正した内容を使用');
  });
  await step('editing and deleting the original invalidate prior extraction and author corrections',async()=>{
    const chat=left.getByRole('dialog',{name:'旅行後の振り返り',exact:true});const before=(await api('aoi',`/reflections/${reflectionId}`)).messages[0];await click(chat,'発言を編集');let d=left.getByRole('dialog',{name:'自分の振り返りを編集する',exact:true});await d.getByLabel('振り返りの内容').fill(negative);await click(d,'発言を保存して整理し直す');await expect(d).toHaveCount(0);await waitMessage('auto_included');
    await expect(chat.locator('.reflection-message-body')).toHaveText(negative);
    const changed=(await api('aoi',`/reflections/${reflectionId}`)).messages[0];assert.equal(changed.source_version,before.source_version+1);assert.equal(changed.extraction.effective.find(v=>v.aspect_id==='guidance').sentiment,'negative');assert.equal((await summary()).status,'insufficient');
    await click(chat,'削除');d=left.getByRole('dialog',{name:'この振り返りを削除しますか？',exact:true});await click(d,'発言と抽出結果を削除');await expect(d).toHaveCount(0);await expect(chat.locator('.reflection-message')).toHaveCount(0);
    await chat.getByLabel('振り返りに送るメッセージ',{exact:true}).fill(positive);await click(chat,'送る');await expect(chat.locator('.reflection-message')).toContainText('自動集計に使用中');assert.equal((await summary()).status,'available');await click(chat,'閉じる');
  });
  await step('withdrawal immediately withholds the trip and the public discovery reference',async()=>{
    await click(left,'参考集計への同意を撤回');const d=left.getByRole('dialog',{name:'同意を撤回しますか？',exact:true});await click(d,'同意を撤回する');await expect(d).toHaveCount(0);const r=await api('aoi',`/reflections/${reflectionId}`);assert.equal(r.ready_for_analysis,false);assert.equal(r.my_state.consented,false);assert.equal((await summary()).status,'insufficient');
    const reference=await showPublicReference();await expect(reference).toContainText('公開できる参考情報はまだありません');await reference.scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,'withdrawn-reference.png')});
  });
  await step('private reflection conversation stays usable at narrow width and enlarged text',async()=>{
    const p=await context.newPage();await p.goto(base+'/stage/visitor');await login(p,p,'aoi');await openMain(p);await click(p,'この旅の振り返りをひらく');await click(p,'この旅を振り返って話す');const d=p.getByRole('dialog',{name:'旅行後の振り返り',exact:true});
    for(const width of [390,320]){await p.setViewportSize({width,height:844});await noOverflow(p,String(width));await expect(d.locator('.message-form')).toBeInViewport();await p.screenshot({path:path.join(out,`reflection-${width}.png`)});}
    await p.locator('html').evaluate(el=>el.style.fontSize='200%');await noOverflow(p,'320+200%');await expect(d.locator('.message-form')).toBeInViewport();await p.screenshot({path:path.join(out,'reflection-320-enlarged.png')});await d.locator('.conversation-history').focus();await d.locator('.conversation-history').press('Home');await click(d,'閉じる');assert.notEqual(await p.locator('html').evaluate(el=>getComputedStyle(el).overflow),'hidden');await p.close();assert.equal(external.length,0);assert.equal(errors.length,0);
  });
}catch(e){results.push({failed:String(e.message).slice(0,1800)});await page.screenshot({path:path.join(out,'failure.png')});process.exitCode=1;}
finally{
  let cleanup=true;
  for(const f of fixtures){
    if(f.reflectionId)try{const r=await api(f.owner,`/reflections/${f.reflectionId}`);if(r.trip_finished)await api(f.owner,`/reflections/${r.id}/completion`,'PUT',{trip_finished:false,version:r.version});}catch{cleanup=false;}
    try{const c=await api(f.owner,`/circles/${f.circleId}`);assert.equal(c.title,f.title);if(c.status==='open')await api(f.owner,`/circles/${c.id}/close`,'POST',{version:c.version});}catch{cleanup=false;}
  }
  if(!cleanup)process.exitCode=1;
  const record={checkedAt:new Date().toISOString(),results,layout,external,errors,cleanup,setup:'Two independently consented fixture trips establish the publication threshold. The third is exercised through the UI.',retention:'Only this run’s reflection completion claims are cancelled and circles closed. No seed plans, existing conversations, or rows are deleted.',passed:results.length===6&&results.every(r=>typeof r==='string')&&cleanup};
  await fs.writeFile(path.join(out,'browser.json'),JSON.stringify(record,null,2));await fs.writeFile(path.join(out,`browser-${run}.json`),JSON.stringify(record,null,2));await browser.close();
}

