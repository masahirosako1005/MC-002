import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(path.join(root,'qa/package.json'));
const {chromium,expect}=require('@playwright/test');
const out=path.join(root,'community/artifacts/motion');await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:900},locale:'ja-JP'});
const page=await context.newPage(),results=[],external=[],errors=[],measurements=[];
await context.addInitScript(()=>{
 window.motionProbe=[];
 const original=Element.prototype.animate;
 Element.prototype.animate=function(frames,options){
  const animation=original.call(this,frames,options);
  if(this.id==='main'){
   const entry={frames,options,kind:this.dataset.motionKind,trigger:this.dataset.motionTrigger,finished:false,cancelled:false};
   window.motionProbe.push(entry);
   animation.addEventListener('finish',()=>entry.finished=true);
   animation.addEventListener('cancel',()=>entry.cancelled=true);
  }
  return animation;
 };
});
await context.route('**/*',async route=>{if(new URL(route.request().url()).hostname!=='127.0.0.1'){external.push(new URL(route.request().url()).origin);await route.abort();}else await route.continue();});
context.on('page',p=>p.on('pageerror',e=>errors.push(e.name)));page.on('pageerror',e=>errors.push(e.name));
const left=page.frameLocator('iframe[title="旅行者の操作画面"]'),right=page.frameLocator('iframe[title="事業者の操作画面"]');
const probe=scope=>scope.locator('html').evaluate(()=>window.motionProbe);
const main=scope=>scope.locator('#main');
const nav=(scope,name)=>scope.getByRole('navigation',{name:'モバイルメニュー'}).getByRole('button',{name,exact:true});
async function login(scope,user,keyboard=false){await scope.getByLabel('アカウント名',{exact:true}).fill(user);await scope.getByLabel('パスワード',{exact:true}).fill(user+'-local-2026');if(keyboard)await scope.getByLabel('パスワード',{exact:true}).press('Enter');else await scope.getByRole('button',{name:'ログイン',exact:true}).click();await expect(main(scope)).toBeVisible();}
async function step(name,fn){await fn();results.push(name);console.log('PASS '+name);}
try{
 await page.goto('http://127.0.0.1:8081/stage');
 await step('pointer login animates only main content; other phone stays logged out',async()=>{
  await login(left,'aoi');await expect.poll(async()=>(await probe(left)).length).toBe(1);
  let records=await probe(left);assert.equal(records[0].kind,'login');assert.equal(records[0].options.duration,220);assert.equal(records[0].frames[0].transform,'translateY(8px)');
  await expect(right.getByLabel('アカウント名',{exact:true})).toHaveValue('');await expect.poll(async()=>(await probe(left))[0].finished).toBe(true);
  assert.equal(await left.locator('.app-shell').evaluate(el=>getComputedStyle(el).transform),'none');
  await login(right,'forest',true);assert.equal((await probe(right)).length,0);await expect(main(right)).toHaveAttribute('data-motion-trigger','keyboard');
 });
 await step('pointer navigation is short and repeat selection does not replay',async()=>{
  await nav(left,'みんなの記録').click();await expect.poll(async()=>(await probe(left)).length).toBe(2);
  let record=(await probe(left)).at(-1);assert.equal(record.kind,'navigation');assert.equal(record.options.duration,170);
  await nav(left,'みんなの記録').click();assert.equal((await probe(left)).length,2);
  await nav(left,'旅を見つける').click();await expect.poll(async()=>(await probe(left)).length).toBe(3);
  await expect(main(left)).toHaveAttribute('data-motion-state','idle');await page.screenshot({path:path.join(out,'after-stage.png')});
 });
 await step('keyboard navigation is immediate and rapid pointer navigation cancels old motion',async()=>{
  const before=(await probe(left)).length;await nav(left,'みんなの記録').focus();await nav(left,'みんなの記録').press('Enter');assert.equal((await probe(left)).length,before);await expect(main(left)).toHaveAttribute('data-motion-trigger','keyboard');
  await nav(left,'旅を見つける').click();await nav(left,'みんなの記録').click();await expect(main(left)).toHaveAttribute('data-motion-state','idle');
  const records=await probe(left);assert.equal(records.length,before+2);assert(records.at(-2).cancelled,'previous navigation must be cancelled');await expect(nav(left,'みんなの記録')).toHaveAttribute('aria-current','page');
 });
 await step('reduced motion disables entrance and navigation; logout removes authenticated content',async()=>{
  await page.emulateMedia({reducedMotion:'reduce'});const before=(await probe(left)).length;await nav(left,'旅を見つける').click();assert.equal((await probe(left)).length,before);await expect(main(left)).toHaveAttribute('data-motion-policy','reduced');
  await left.getByRole('button',{name:'藤沢 葵 アカウントを切り替える',exact:true}).click();await left.getByRole('button',{name:'ログアウトして切り替える',exact:true}).click();await expect(main(left)).toHaveCount(0);await expect(left.getByLabel('パスワード',{exact:true})).toHaveValue('');await expect(right.locator('.provider-workspace')).toBeVisible();
  await login(left,'ren');assert.equal((await probe(left)).length,before);await expect(main(left)).toHaveAttribute('data-motion-policy','reduced');
 });
 await step('keyboard login, failed authentication and narrow viewport remain usable',async()=>{
  const p=await context.newPage();await p.setViewportSize({width:320,height:844});await p.goto('http://127.0.0.1:8081/stage/visitor');
  await p.getByLabel('アカウント名',{exact:true}).fill('aoi');await p.getByLabel('パスワード',{exact:true}).fill('wrong-password');await p.getByRole('button',{name:'ログイン',exact:true}).click();await expect(p.getByRole('alert')).toBeVisible();assert.equal((await probe(p)).length,0);await login(p,'aoi',true);assert.equal((await probe(p)).length,0);
  assert(await p.locator('html').evaluate(el=>el.scrollWidth<=innerWidth+1));await p.locator('html').evaluate(el=>el.style.fontSize='200%');assert(await p.locator('html').evaluate(el=>el.scrollWidth<=innerWidth+1));await p.screenshot({path:path.join(out,'phone-320-enlarged.png'),fullPage:true});await p.close();assert.equal(external.length,0);assert.equal(errors.length,0);
 });
 measurements.push({left:await probe(left),right:await probe(right)});
}catch(e){results.push({failed:String(e.message).slice(0,1600)});await page.screenshot({path:path.join(out,'failure.png')});process.exitCode=1;}
finally{const report={checkedAt:new Date().toISOString(),results,measurements,external,errors,passed:results.length===5&&results.every(r=>typeof r==='string'),scope:'Headless separate browser; no claim of repairing ordinary Edge. Captured WAAPI timings, actual DOM/auth transitions and viewport behavior.'};await fs.writeFile(path.join(out,'results.json'),JSON.stringify(report,null,2));await fs.writeFile(path.join(out,`results-${Date.now()}.json`),JSON.stringify(report,null,2));await browser.close();}
