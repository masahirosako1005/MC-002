import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(path.join(root,'qa/package.json'));
const {chromium,expect}=require('@playwright/test');
const AxeBuilder=require('@axe-core/playwright').default;
const out=path.join(root,'community/artifacts/discovery');
await fs.mkdir(out,{recursive:true});
const base='http://127.0.0.1:8081';
const run=Date.now(),planTitle=`森の日帰り散策 ${run}`,circleTitle=`日帰りの仲間 ${run}`;
const day=new Date(Date.now()+35*86400000).toISOString().slice(0,10);
const sessions={},results=[],external=[],errors=[],fixtures={};
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:900},locale:'ja-JP',timezoneId:'Asia/Tokyo'});
await context.route('**/*',async route=>{
  const url=new URL(route.request().url());
  if(url.hostname!=='127.0.0.1'){external.push(url.origin);await route.abort();}
  else await route.continue();
});
context.on('page',p=>p.on('pageerror',e=>errors.push(e.name)));
const page=await context.newPage();
const left=page.frameLocator('iframe[title="旅行者の操作画面"]');
const right=page.frameLocator('iframe[title="事業者の操作画面"]');
async function click(scope,name){await scope.getByRole('button',{name:name==='旅を見つける'?/^(旅を見つける|旅を探す)$/:name,exact:true}).click();}
async function choose(scope,label,name){await scope.getByLabel(label,{exact:true}).click();await scope.getByRole('option',{name,exact:true}).click();}
async function login(host,scope,user){
  await scope.getByLabel('アカウント名',{exact:true}).fill(user);
  await scope.getByLabel('パスワード',{exact:true}).fill(user+'-local-2026');
  const response=host.waitForResponse(r=>r.url().endsWith('/stage/login')&&r.request().method()==='POST');
  await click(scope,'ログイン');sessions[user]=await(await response).json();
  await expect(scope.locator('.app-shell')).toBeVisible();
}
async function api(user,url,method='GET',data){
  const s=sessions[user];
  const r=await context.request.fetch(base+'/api'+url,{method,headers:{Authorization:`Bearer ${s.access_token}`,Origin:base,'X-CSRF-Token':s.csrf_token},data});
  assert.equal(r.status(),200,`${method} ${url}: ${r.status()}`);return r.json();
}
async function step(name,fn){await fn();results.push(name);console.log('PASS '+name);}
async function savePlan(dialog){
  const response=page.waitForResponse(r=>r.request().method().match(/POST|PATCH/)&&/\/api\/(providers\/[^/]+\/plans|provider-plans\/[^/]+)$/.test(new URL(r.url()).pathname));
  await click(dialog,'この内容で公開する');
  const r=await response;assert.equal(r.status(),200);const plan=await r.json();fixtures.planId=plan.id;
  await expect(dialog).toHaveCount(0);return plan;
}
async function noOverflow(scope){
  const state=await scope.locator('html').evaluate(el=>({width:innerWidth,scrollWidth:el.scrollWidth,fontSize:getComputedStyle(el).fontSize,items:[...document.querySelectorAll('body *')].filter(node=>{const r=node.getBoundingClientRect();return r.width>0&&(r.right>innerWidth+1||r.left< -1);}).slice(0,20).map(node=>({tag:node.tagName,className:node.className,right:node.getBoundingClientRect().right,width:node.getBoundingClientRect().width,text:node.textContent?.slice(0,100)}))}));
  if(state.scrollWidth>state.width+1){await fs.writeFile(path.join(out,'overflow.json'),JSON.stringify(state,null,2));await scope.screenshot({path:path.join(out,'overflow.png'),fullPage:true});}
  assert(state.scrollWidth<=state.width+1,`Horizontal page overflow: viewport ${state.width}, content ${state.scrollWidth}, font ${state.fontSize}`);
}
async function inspectAxe(name){
  const scan=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
  await fs.writeFile(path.join(out,`axe-${name}.json`),JSON.stringify(scan.violations,null,2));
  assert.equal(scan.violations.length,0,JSON.stringify(scan.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}))));
}

try{
  await page.goto(base+'/stage');await login(page,left,'aoi');await login(page,right,'forest');
  await step('provider creates and edits a dated public plan through the screen',async()=>{
    await click(right,'プランをつくる');
    let d=right.getByRole('dialog',{name:'新しいプランをつくる',exact:true});
    await d.getByLabel('プランの名前',{exact:true}).fill(planTitle);
    await d.getByLabel('紹介',{exact:true}).fill('森を歩いて、季節の景色を楽しむ日帰りの散策です。');
    await d.getByLabel('地域',{exact:true}).fill('岐阜県');
    await choose(d,'日程の決め方','開催日時を指定する');
    await d.getByLabel('開催開始（日本時間）',{exact:true}).fill(day+'T09:00');
    await d.getByLabel('開催終了（日本時間）',{exact:true}).fill(day+'T18:00');
    await d.getByLabel('最少人数',{exact:true}).fill('2');
    await d.getByLabel('最大人数',{exact:true}).fill('8');
    await d.getByLabel('泊数',{exact:true}).fill('0');
    await d.getByLabel('概算費用（円）',{exact:true}).fill('4000');
    await d.getByLabel('含むもの・含まないもの',{exact:true}).fill('ガイド料を含みます。往復交通費と食事は含みません。');
    await d.getByRole('button',{name:'自然',exact:true}).click();
    await d.getByLabel('店・場所の名前',{exact:true}).fill('岐阜の森の散策路');
    await d.getByLabel('ここでできること',{exact:true}).fill('ガイドと森を歩きます。');
    const plan=await savePlan(d);assert.equal(plan.schedule_type,'dated');
    assert.equal(Date.parse(plan.starts_at),Date.parse(day+'T09:00:00+09:00'));
    const card=right.locator('.market-plan-card').filter({has:right.getByRole('heading',{name:planTitle,exact:true})});
    await click(card,'プランを編集する');d=right.getByRole('dialog',{name:'プランを編集する',exact:true});
    await expect(d.getByLabel('開催開始（日本時間）',{exact:true})).toHaveValue(day+'T09:00');
    await d.getByLabel('開催終了（日本時間）',{exact:true}).fill(day+'T19:00');
    const updated=await savePlan(d);assert.equal(updated.version,plan.version+1);
    assert.equal(Date.parse(updated.ends_at),Date.parse(day+'T19:00:00+09:00'));
    await expect(card).toContainText('開催');
    await page.screenshot({path:path.join(out,'provider-dates.png')});
  });
  await step('traveler creates a circle and explicitly confirms matching travel conditions',async()=>{
    await click(left,'講を見つける');
    await left.getByRole('button',{name:/仲間を選んでつくる/}).click();
    let d=left.getByRole('dialog');await d.getByLabel('講の名前',{exact:true}).fill(circleTitle);
    const response=page.waitForResponse(r=>r.url().endsWith('/api/circles')&&r.request().method()==='POST');
    await click(d,'講をつくって招待を送る');const c=await(await response).json();assert(c.id);fixtures.circleId=c.id;
    await expect(left.getByRole('heading',{name:circleTitle,exact:true})).toBeVisible();
    await click(left,'旅行条件を確認');d=left.getByRole('dialog',{name:'旅行条件を確認する',exact:true});
    await d.getByLabel('予定している旅行人数',{exact:true}).fill('6');
    await d.getByLabel('泊数',{exact:true}).fill('0');
    await d.getByLabel(/予算の目安/).fill('5000');
    await choose(d,'予算の単位','1人あたり');await choose(d,'どこまで含む予算？','選ぶプラン部分');
    await d.getByLabel(/出発日の希望/).fill(day);await d.getByRole('button',{name:'自然',exact:true}).click();
    await click(d,'この旅行条件で確定する');await expect(d).toHaveCount(0);
    const circle=await api('aoi',`/circles/${fixtures.circleId}`);assert.equal(circle.requirements.nights,0);assert.equal(circle.requirements.date_start,day);
  });
  // The remaining steps use the public discovery and shared-candidate controls.
  await step('ranked discovery adds a candidate and opens the internal circle conversation',async()=>{
    await click(left,'← 講の一覧へ');
    await click(left,'旅を見つける');
    await choose(left,'どの講で行く旅を探す？',circleTitle);
    await expect(left.locator('.plan-discovery')).toBeVisible();
    await expect(left.getByText('あなたの講へのおすすめ順',{exact:true})).toBeVisible();
    await expect(left.locator('.plan-discovery .market-plan-card').first()).toBeVisible();
    const card=left.locator('.market-plan-card').filter({has:left.getByRole('heading',{name:planTitle,exact:true})});
    for(let pages=0;pages<25&&!(await card.count());pages++){
      const next=left.locator('.plan-discovery .discovery-pager').getByRole('button',{name:'次へ',exact:true});
      if(!(await next.count())||!(await next.isEnabled()))break;
      await next.click();
    }
    const search=left.getByRole('searchbox',{name:'取得した候補を場所・プラン名で絞り込む',exact:true});
    await search.fill('存在しない候補 '+run);await expect(left.getByText('絞り込みに合う候補はありません',{exact:true})).toBeVisible();
    await search.fill(planTitle);await expect(card).toBeVisible();
    await left.getByRole('button',{name:'絞り込み',exact:true}).click();
    const filters=left.getByRole('dialog',{name:'候補を絞り込む',exact:true});
    await choose(filters,'所要日数','宿泊を含む');await expect(filters.getByRole('button',{name:'0件の候補を表示',exact:true})).toBeVisible();
    await choose(filters,'所要日数','日帰り');await choose(filters,'開催日程','日時が決まっている');await choose(filters,'開催エリア','岐阜県');
    await click(filters,'1件の候補を表示');await expect(card).toBeVisible();await expect(card).toContainText('2〜8人');await expect(card).toContainText('4,000円 / 1人');await expect(card).toContainText('概算');
    await click(card,'日別の行程を見る');
    const firstDetail=left.getByRole('dialog',{name:'プランの行程と費用',exact:true});await expect(firstDetail).toContainText('日本時間');await expect(firstDetail).toContainText('往復交通費と食事は含みません');await inspectAxe('plan-detail');await click(firstDetail,'閉じる');
    await click(card,'講に追加');
    const save=left.getByRole('dialog',{name:'講に候補を追加する',exact:true});
    await expect(save.getByLabel('追加する講',{exact:true})).toContainText(circleTitle);
    await click(save,'候補を保存して講で話す');await expect(save).toHaveCount(0);
    await expect(left.getByRole('heading',{name:circleTitle,exact:true})).toBeVisible();
    await expect(left.getByLabel('講の内輪の会話に送るメッセージ')).toBeVisible();
    const saved=await api('aoi',`/circles/${fixtures.circleId}/candidate-cards`);
    assert.equal(saved.items.length,1);assert.equal(saved.items[0].plan_id,fixtures.planId);
    assert.equal(saved.items[0].current_state,'available');
    const circle=await api('aoi',`/circles/${fixtures.circleId}`);assert.equal(circle.active_provider_invitation,null);
    await page.screenshot({path:path.join(out,'candidate-conversation.png')});await inspectAxe('candidate');
  });
  await step('saved candidate survives reopening and explicit destination sharing creates only a pending invitation',async()=>{
    await click(left,'← 講の一覧へ');
    await left.locator('.circle-list-card').filter({hasText:circleTitle}).click();
    const saved=left.locator('.saved-candidate').filter({hasText:planTitle});
    await expect(saved).toBeVisible();await click(saved,'候補の詳細を見る');
    const detail=left.getByRole('dialog');await detail.getByRole('button',{name:/事業者を招く|この行き先/}).click();
    const d=left.getByRole('dialog',{name:'行き先を決めて、事業者を招く',exact:true});
    await d.getByLabel('事業者に伝える希望').fill('6人で森の散策を希望しています。集合場所を相談したいです。');
    await expect(d.getByRole('button',{name:'この行き先で事業者を招く',exact:true})).toBeDisabled();
    await d.getByRole('checkbox').check();await click(d,'この行き先で事業者を招く');await expect(d).toHaveCount(0);
    const circle=await api('aoi',`/circles/${fixtures.circleId}`);
    assert.equal(circle.active_provider_invitation.snapshot.plan.id,fixtures.planId);
    assert.equal(circle.active_provider_invitation.status,'pending');assert.equal(circle.active_provider_invitation.consultation_id,null);
    await click(right,'講への招待');await expect(right.locator('.circle-invitation-card').filter({hasText:planTitle})).toBeVisible();
    await page.screenshot({path:path.join(out,'destination-invitation.png')});
  });
  await step('candidate screens fit narrow phones and enlarged text without external requests',async()=>{
    const p=await context.newPage();await p.goto(base+'/stage/visitor');await login(p,p,'aoi');await click(p,'講を見つける');
    await p.locator('.circle-list-card').filter({hasText:circleTitle}).click();
    for(const width of [390,320]){await p.setViewportSize({width,height:844});await noOverflow(p);await p.screenshot({path:path.join(out,`candidate-${width}.png`)});}
    await p.locator('html').evaluate(el=>el.style.fontSize='200%');await noOverflow(p);
    await p.getByLabel('講の内輪の会話に送るメッセージ').scrollIntoViewIfNeeded();await expect(p.getByLabel('講の内輪の会話に送るメッセージ')).toBeInViewport();
    await p.locator('html').evaluate(el=>el.style.fontSize='');await click(p,'旅を見つける');await choose(p,'どの講で行く旅を探す？',circleTitle);
    await p.getByRole('searchbox',{name:'取得した候補を場所・プラン名で絞り込む',exact:true}).fill(planTitle);
    const card=p.locator('.market-plan-card').filter({hasText:planTitle});await expect(card).toBeVisible();
    for(const width of [390,320]){
      await p.setViewportSize({width,height:844});await noOverflow(p);await card.scrollIntoViewIfNeeded();await p.screenshot({path:path.join(out,`plan-${width}.png`)});
      await click(card,'日別の行程を見る');const detail=p.getByRole('dialog',{name:'プランの行程と費用',exact:true});await expect(detail).toContainText('日本時間');await noOverflow(p);await p.screenshot({path:path.join(out,`detail-${width}.png`)});await click(detail,'閉じる');
    }
    await p.locator('html').evaluate(el=>el.style.fontSize='200%');await noOverflow(p);await card.scrollIntoViewIfNeeded();await p.screenshot({path:path.join(out,'plan-320-enlarged.png')});
    await click(card,'日別の行程を見る');const detail=p.getByRole('dialog',{name:'プランの行程と費用',exact:true});await noOverflow(p);
    const inner=await detail.locator('.modal-body, .browse-plan-detail, .plan-detail-facts, .price-summary').evaluateAll(nodes=>nodes.map(node=>({className:node.className,client:node.clientWidth,scroll:node.scrollWidth,left:node.getBoundingClientRect().left,right:node.getBoundingClientRect().right})));
    await fs.writeFile(path.join(out,'detail-layout.json'),JSON.stringify(inner,null,2));assert(inner.every(item=>item.scroll<=item.client+1&&item.left>=-1&&item.right<=321),JSON.stringify(inner));
    await p.screenshot({path:path.join(out,'detail-320-enlarged.png')});await click(detail,'閉じる');
    await p.close();assert.equal(external.length,0);assert.equal(errors.length,0);
  });
}catch(e){
  results.push({failed:String(e.message).slice(0,1800)});await page.screenshot({path:path.join(out,'failure.png')});process.exitCode=1;
}finally{
  const cleanup={circle:!fixtures.circleId,plan:!fixtures.planId};
  if(fixtures.circleId)try{const c=await api('aoi',`/circles/${fixtures.circleId}`);assert.equal(c.title,circleTitle);if(c.status==='open')await api('aoi',`/circles/${c.id}/close`,'POST',{version:c.version});cleanup.circle=true;}catch{process.exitCode=1;}
  if(fixtures.planId)try{const p=await api('forest',`/provider-plans/${fixtures.planId}`);assert.equal(p.title,planTitle);const {id,provider,source_note,...body}=p;await api('forest',`/provider-plans/${id}`,'PATCH',{...body,status:'archived'});cleanup.plan=true;}catch{process.exitCode=1;}
  const record={checkedAt:new Date().toISOString(),results,external,errors,cleanup,fixtureRetention:'Only this run’s plan is archived and circle closed; no rows deleted.',passed:results.length===5&&results.every(r=>typeof r==='string')&&cleanup.circle&&cleanup.plan};
  await fs.writeFile(path.join(out,'browser.json'),JSON.stringify(record,null,2));await fs.writeFile(path.join(out,`browser-${run}.json`),JSON.stringify(record,null,2));await browser.close();
}
