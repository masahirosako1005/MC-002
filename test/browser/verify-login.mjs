import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(path.join(root,'test/browser/package.json'));
const {chromium,expect}=require('@playwright/test');const AxeBuilder=require('@axe-core/playwright').default;
const out=path.join(root,'artifacts/browser/login');await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true}),context=await browser.newContext({viewport:{width:1440,height:900},locale:'ja-JP'}),page=await context.newPage();
const base='http://127.0.0.1:8081',external=[],errors=[],images=[],results=[];
page.on('pageerror',e=>errors.push(e.name));page.on('response',r=>{if(r.request().resourceType()==='image')images.push(new URL(r.url()).pathname);});
await context.route('**/*',async r=>{if(new URL(r.request().url()).hostname!=='127.0.0.1'){external.push(new URL(r.request().url()).origin);await r.abort();}else await r.continue();});
const left=page.frameLocator('iframe[title="利用者のスマートフォン画面"]'),right=page.frameLocator('iframe[title="事業者のパソコン管理画面"]');
async function step(name,fn){await fn();results.push(name);console.log('PASS '+name);}
async function login(scope,user){await scope.getByLabel('アカウント名',{exact:true}).fill(user);await scope.getByLabel('パスワード',{exact:true}).fill(user+'-local-2026');await scope.getByLabel('パスワード',{exact:true}).press('Enter');await expect(scope.locator('.app-shell')).toBeVisible();}
async function noOverflow(scope){assert(await scope.locator('html').evaluate(el=>el.scrollWidth<=innerWidth+1));}
try{
 await page.goto(base+'/stage');
 if(process.argv.includes('--before')){await expect(left.getByRole('button',{name:'ログイン',exact:true})).toBeVisible();await page.screenshot({path:path.join(out,'before-stage.png')});}
 else {
 await step('blank named account fields without public account enumeration',async()=>{
  const r=await context.request.get(base+'/api/bootstrap');const b=await r.json();assert(!('accounts' in b));assert(!JSON.stringify(b).includes('aoi'));
  for(const scope of [left,right]){const username=scope.getByLabel('アカウント名',{exact:true}),password=scope.getByLabel('パスワード',{exact:true});await expect(username).toHaveValue('');await expect(password).toHaveValue('');await expect(username).toHaveAttribute('autocomplete','username');await expect(password).toHaveAttribute('autocomplete','current-password');assert.equal(await scope.getByRole('radio').count(),0);await noOverflow(scope);}
  await left.locator('.login-cover img, .login-photo img, img').first().evaluate(el=>el.complete || new Promise(resolve=>el.addEventListener('load',resolve,{once:true})));
  assert(!images.some(url=>url.includes('/api/covers/')));
  await page.screenshot({path:path.join(out,'after-stage.png')});
  const scan=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();await fs.writeFile(path.join(out,'axe.json'),JSON.stringify(scan.violations,null,2));assert.equal(scan.violations.length,0,JSON.stringify(scan.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}))));
 });
 await step('password visibility, failed authentication and Enter success',async()=>{
  const password=left.getByLabel('パスワード',{exact:true});await left.getByLabel('アカウント名',{exact:true}).fill('aoi');await password.fill('wrong-password');await left.getByRole('button',{name:'パスワードを表示',exact:true}).click();await expect(password).toHaveAttribute('type','text');await left.getByRole('button',{name:'パスワードを隠す',exact:true}).click();await expect(password).toHaveAttribute('type','password');
  await password.press('Enter');await expect(left.getByRole('alert')).toBeVisible();await expect(right.getByLabel('アカウント名',{exact:true})).toHaveValue('');await login(left,'aoi');await login(right,'forest');assert.equal((await context.cookies()).length,0);
 });
 await step('one-side logout preserves the other phone and returns empty form',async()=>{
  await left.getByRole('button',{name:'藤沢 葵 アカウントを切り替える',exact:true}).click();await left.getByRole('button',{name:'ログアウトして切り替える',exact:true}).click();await expect(left.getByLabel('アカウント名',{exact:true})).toHaveValue('');await expect(left.getByLabel('パスワード',{exact:true})).toHaveValue('');await expect(right.locator('.provider-workspace')).toBeVisible();
 });
 await step('narrow screens, text enlargement, keyboard and bounded photo requests',async()=>{
  const narrow=await context.newPage();await narrow.goto(base+'/stage/visitor');for(const width of [390,320]){await narrow.setViewportSize({width,height:844});await noOverflow(narrow);await narrow.getByRole('button',{name:'ログイン',exact:true}).scrollIntoViewIfNeeded();await narrow.screenshot({path:path.join(out,`phone-${width}.png`),fullPage:true});}
  await narrow.locator('html').evaluate(el=>el.style.fontSize='200%');await noOverflow(narrow);await narrow.getByLabel('アカウント名',{exact:true}).focus();await narrow.getByLabel('アカウント名',{exact:true}).press('Tab');await expect(narrow.getByLabel('パスワード',{exact:true})).toBeFocused();await narrow.getByRole('button',{name:'ログイン',exact:true}).scrollIntoViewIfNeeded();await expect(narrow.getByRole('button',{name:'ログイン',exact:true})).toBeInViewport();await narrow.emulateMedia({reducedMotion:'reduce'});await narrow.close();assert.equal(external.length,0);assert.equal(errors.length,0);
 });
 }
}catch(e){results.push({failed:String(e.message).slice(0,1600)});await page.screenshot({path:path.join(out,'failure.png')});process.exitCode=1;}
finally{if(!process.argv.includes('--before'))await fs.writeFile(path.join(out,'results.json'),JSON.stringify({checkedAt:new Date().toISOString(),results,external,errors,images,passed:results.length===4&&results.every(r=>typeof r==='string')},null,2));await browser.close();}
