import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(path.join(root,'test/browser/package.json'));
const {chromium,expect}=require('@playwright/test');
const AxeBuilder=require('@axe-core/playwright').default;
const out=path.join(root,'artifacts/browser/personalization');await fs.mkdir(out,{recursive:true});
const base='http://127.0.0.1:8081';const sessions={},originals={};let fixtureCircle;
const report={checkedAt:new Date().toISOString(),checks:[],external:[],errors:[],passed:false};
async function api(user,route,method='GET',body){const s=sessions[user];const r=await fetch(base+'/api'+route,{method,headers:{Origin:base,'Content-Type':'application/json',...(s?{Authorization:'Bearer '+s.access_token,'X-CSRF-Token':s.csrf_token}:{})},body:body?JSON.stringify(body):undefined});assert(r.ok,route+' '+r.status);return r.json();}
async function state(user,patch){const current=await api(user,'/me/resume-state');return api(user,'/me/resume-state','PUT',{...current,...patch,version:current.version});}
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:390,height:844},locale:'ja-JP'});
await context.route('**/*',async r=>{if(!['127.0.0.1','localhost'].includes(new URL(r.request().url()).hostname)){report.external.push(new URL(r.request().url()).origin);await r.abort();}else await r.continue();});
const page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.name));
const search=page.getByRole('searchbox',{name:'取得した候補を場所・プラン名で絞り込む'});
async function login(user){await page.getByLabel('アカウント名',{exact:true}).fill(user);await page.getByLabel('パスワード',{exact:true}).fill(user+'-local-2026');await page.getByRole('button',{name:'ログイン',exact:true}).click();await expect(page.locator('.app-shell')).toBeVisible();}
async function logout(){await page.getByRole('button',{name:/アカウントを切り替える$/}).last().click();await page.getByRole('button',{name:'ログアウトして切り替える',exact:true}).click();await expect(page.getByRole('button',{name:'ログイン',exact:true})).toBeVisible();}
try{
 for(const user of ['aoi','ren']){sessions[user]=await api(user,'/stage/login','POST',{username:user,password:user+'-local-2026'});originals[user]=await api(user,'/me/resume-state');await state(user,{page:'market',community_id:'peers',circle_id:null,filters:{query:'',category:'',duration:'all',schedule:'all',area:''}});}
 fixtureCircle=await api('aoi','/circles','POST',{community_id:'peers',title:'本人再開の確認 '+Date.now(),mode:'manual',tags:['nature'],desired_count:2,invitee_ids:[],client_request_id:crypto.randomUUID()});
 await page.goto(base);await login('aoi');await expect(search).toHaveValue('');
 await expect(page.getByRole('region',{name:'自分の関心'})).toBeVisible();
 await search.fill('森');await expect.poll(async()=> (await api('aoi','/me/resume-state')).filters.query).toBe('森');
 await page.reload();await expect(search).toHaveValue('森');await expect(page.locator('.market-plan-card').first()).toBeVisible();report.checks.push('own search and page restored after reload');
 const circles=(await api('aoi','/circles')).items.filter(c=>c.status==='open'&&c.community_id==='peers');
 const chosen=circles.find(c=>circles.filter(other=>other.title===c.title).length===1);assert(chosen,'Expected an existing accepted open fixture circle');
 await page.getByLabel('どの講で行く旅を探す？',{exact:true}).click();await page.getByRole('option',{name:chosen.title,exact:true}).click();
 await expect.poll(async()=> (await api('aoi','/me/resume-state')).circle_id).toBe(chosen.id);
 await page.reload();await expect(page.getByLabel('どの講で行く旅を探す？',{exact:true})).toContainText(chosen.title);
 await page.getByLabel('どの講で行く旅を探す？',{exact:true}).click();await page.getByRole('option',{name:'自分の関心から探す',exact:true}).click();
 await expect.poll(async()=> (await api('aoi','/me/resume-state')).circle_id).toBe(null);report.checks.push('accepted circle selection restored after reload');

 await page.getByRole('button',{name:'みんなの記録',exact:true}).click();await expect.poll(async()=> (await api('aoi','/me/resume-state')).page).toBe('feed');
 await page.reload();await expect(page.locator('.post-card').first()).toBeVisible();report.checks.push('last opened page restored');
 await page.getByRole('button',{name:'旅を探す',exact:true}).click();await expect(search).toHaveValue('森');
 await expect.poll(async()=> (await api('aoi','/me/resume-state')).page).toBe('market');
 // A second session updates the DB; the stale page must discard its pending edit.
 await state('aoi',{filters:{query:'海',category:'',duration:'all',schedule:'all',area:''}});
 await search.fill('カフェ');await expect(search).toHaveValue('海');assert.equal((await api('aoi','/me/resume-state')).filters.query,'海');report.checks.push('CAS conflict loads latest state without overwriting it');
 let delayed;let held=false;
 await page.route('**/api/me/resume-state',async route=>{if(route.request().method()==='PUT'&&!held){held=true;delayed=route;}else await route.continue();});
 await search.fill('前アカウントの未保存条件');await expect.poll(()=>!!delayed).toBe(true);
 await logout();await login('ren');await expect(search).toHaveValue('');
 await delayed.fulfill({status:401,contentType:'application/json',body:JSON.stringify({detail:'ログインしてください。'})});
 await page.waitForLoadState('networkidle');await expect(page.locator('.app-shell')).toBeVisible();await expect(search).toHaveValue('');
 await page.unroute('**/api/me/resume-state');assert.equal((await api('aoi','/me/resume-state')).filters.query,'海');report.checks.push('late old-account 401 cannot clear the new account');
 await search.fill('カフェ');await expect.poll(async()=> (await api('ren','/me/resume-state')).filters.query).toBe('カフェ');
 await logout();await login('aoi');await expect(search).toHaveValue('海');report.checks.push('two accounts keep independent private filters');
 await state('aoi',{page:'market',community_id:null,circle_id:null});await page.reload();
 await expect(page.getByLabel('コミュニティ',{exact:true})).toContainText('コミュニティを選ぶ');assert.equal((await api('aoi','/me/resume-state')).community_id,null);
 await page.getByLabel('コミュニティ',{exact:true}).click();await page.getByRole('option',{name:'同期の旅じたく',exact:true}).click();
 await expect.poll(async()=> (await api('aoi','/me/resume-state')).community_id).toBe('peers');report.checks.push('cleared community stays unselected until explicit choice');

 const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();report.axeViolations=axe.violations.map(v=>({id:v.id,impact:v.impact}));assert.equal(axe.violations.length,0);
 for(const width of [390,320]){await page.setViewportSize({width,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:path.join(out,'personal-home-'+width+'.png'),fullPage:true});}
 await page.locator('html').evaluate(el=>el.style.fontSize='200%');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:path.join(out,'personal-home-200.png'),fullPage:true});
 assert.equal(report.errors.length,0);assert.equal(report.external.length,0);report.passed=true;
}catch(e){report.failure=String(e.message).slice(0,1400);await page.screenshot({path:path.join(out,'browser-failure.png'),fullPage:true});process.exitCode=1;}
finally{await browser.close();if(fixtureCircle){try{const current=await api('aoi','/circles/'+fixtureCircle.id);await api('aoi','/circles/'+fixtureCircle.id+'/close','POST',{version:current.version});}catch{report.cleanup=false;report.passed=false;process.exitCode=1;}}for(const [user,original] of Object.entries(originals)){try{await state(user,original);}catch{report.cleanup=false;report.passed=false;process.exitCode=1;}}if(report.cleanup!==false)report.cleanup=true;await fs.writeFile(path.join(out,'browser.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));}
