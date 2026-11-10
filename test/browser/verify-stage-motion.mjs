import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
await fs.mkdir(path.join(root,'artifacts/browser'),{recursive:true});
const {chromium,expect}=createRequire(path.join(root,'test/browser/package.json'))('@playwright/test');
const browser=await chromium.launch({channel:'msedge',headless:true});
const results=[],coverRequests=[];
const p=await browser.newPage({viewport:{width:1440,height:900}});
const connection=p.locator('.stage-connection');
async function notify(type,side='visitor',status='success'){
 const frame=p.frames().find(f=>f.url().endsWith('/stage/'+side));
 await frame.evaluate(args=>parent.postMessage({source:'ko-stage',type:args.type,status:args.status},location.origin),{type,status});
}
async function step(name,fn){await fn();results.push({name,passed:true});console.log('PASS '+name);}
try{
 p.on('request',r=>{if(r.url().includes('/api/covers/'))coverRequests.push(new URL(r.url()).pathname)});
 await p.goto('http://127.0.0.1:8081/stage');
 for(const side of ['旅行者','事業者'])await expect(p.frameLocator(`iframe[title="${side}の操作画面"]`).getByRole('button',{name:'ログイン',exact:true})).toBeVisible();
 await step('hidden login images are not created or fetched',async()=>{
  for(const f of p.frames())assert.equal(await f.locator('.login-photo img').count(),0);
  assert.equal(coverRequests.length,0);
  const file=path.join(root,'artifacts/browser/stage-lightening.json'),report=JSON.parse(await fs.readFile(path.join(root,'artifacts/community/stage-lightening.json'),'utf8'));
  report.after={checkedAt:new Date().toISOString(),cover_requests:coverRequests,hidden_login_images:0};
  report.before.single_resource_bytes=355761;report.limit='Request count reduction, not a measured total network or process memory reduction.';
  await fs.writeFile(file,JSON.stringify(report,null,2));
 });
 await step('idle and internal actions do not animate',async()=>{
  assert.equal(await p.evaluate(()=>document.getAnimations().length),0);
  for(const type of ['conversation','conditions','requirements','recommendations','provider-plan'])await notify(type);
  await expect(connection).toHaveAttribute('data-transfer-count','0');
 });
 await step('single shot finishes and cancelled CSS cannot leave active state stuck',async()=>{
  await notify('selection');await expect(connection).toHaveAttribute('data-animating','true');
  await p.locator('.stage-connection-packet').evaluate(el=>el.style.animation='none');
  await expect(connection).toHaveAttribute('data-animating','false');
  assert.equal(await p.evaluate(()=>document.getAnimations().length),0);
 });
 await step('repeated successful notifications each complete in both directions',async()=>{
  await notify('reply','provider');await notify('reply','visitor');
  await expect(connection).toHaveAttribute('data-transfer-count','3');
  await expect(connection).toHaveAttribute('data-direction','visitor-to-provider');
  await expect(connection).toHaveAttribute('data-animating','false');
 });
 await step('reduced motion and narrow layout keep a static connection',async()=>{
  await p.emulateMedia({reducedMotion:'reduce'});await notify('reply','provider');
  await expect(connection).toHaveAttribute('data-transfer-count','4');await expect(connection).toHaveAttribute('data-animating','false');
  assert.equal(await p.evaluate(()=>document.getAnimations().length),0);
  await p.emulateMedia({reducedMotion:'no-preference'});await p.setViewportSize({width:390,height:844});
  await notify('reply');await expect(connection).toHaveAttribute('data-transfer-count','5');await expect(connection).not.toBeVisible();await expect(connection).toHaveAttribute('data-animating','false');
 });
}finally{
 await fs.writeFile(path.join(root,'artifacts/browser/stage-motion.json'),JSON.stringify({checkedAt:new Date().toISOString(),results,scope:'Synthetic notifications from authorized iframe sources for motion edge cases. Real saved consultation directions are verified separately by verify-marketplace.mjs.',passed:results.length===5},null,2));
 await browser.close();
}
