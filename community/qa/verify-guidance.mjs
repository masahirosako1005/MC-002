import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(path.join(root,'qa/package.json'));
const {chromium,expect}=require('@playwright/test');
const AxeBuilder=require('@axe-core/playwright').default;
const out=path.join(root,'community/artifacts/guidance');await fs.mkdir(out,{recursive:true});
const report={checkedAt:new Date().toISOString(),external:[],errors:[],checks:[],passed:false};
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:390,height:844},locale:'ja-JP'});
const base='http://127.0.0.1:8081';let posted;
await context.route('**/*',async r=>{if(!['127.0.0.1','localhost'].includes(new URL(r.request().url()).hostname)){report.external.push(new URL(r.request().url()).origin);await r.abort();}else await r.continue();});
const page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.name));
async function api(url,method='GET',data){const me=await(await context.request.get(base+'/api/me')).json();const r=await context.request.fetch(base+'/api'+url,{method,data,headers:{Origin:base,'X-CSRF-Token':me.csrf_token}});assert(r.ok(),url+' '+r.status());return r.json();}
try{
 await page.goto(base);await page.getByLabel('アカウント名',{exact:true}).fill('aoi');await page.getByLabel('パスワード',{exact:true}).fill('aoi-local-2026');await page.getByRole('button',{name:'ログイン',exact:true}).click();
 await expect(page.getByRole('button',{name:'みんなの記録',exact:true})).toBeVisible();
 const bootstrap=await(await context.request.get(base+'/api/bootstrap')).json();assert.equal(bootstrap.model.inference_enabled,false);assert.equal(bootstrap.model.external_ai_enabled,false);report.checks.push('live bootstrap disables inference and external AI');
 await page.getByRole('button',{name:'みんなの記録',exact:true}).click();await page.getByRole('button',{name:/どんな旅をしてきましたか/}).click();
 const dialog=page.getByRole('dialog');const uploadResponse=page.waitForResponse(r=>r.url().endsWith('/api/media')&&r.request().method()==='POST');
 await dialog.locator('input[type=file]').setInputFiles(path.join(root,'community/assets/coffee.png'));
 const uploaded=await(await uploadResponse).json();assert.equal(uploaded.analysis.status,'guided');assert.equal(uploaded.analysis.inference_enabled,false);
 await expect(dialog.getByText('タグの候補',{exact:true})).toBeVisible();await expect(dialog.getByText('写真を準備しています…',{exact:true})).toHaveCount(0);
 await dialog.getByLabel('旅のひとこと').fill('写真タグ案内の保存確認');await dialog.getByRole('button',{name:/カフェ/}).last().click();
 const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();report.axeViolations=axe.violations.map(v=>({id:v.id,impact:v.impact}));assert.equal(axe.violations.length,0);
 await page.screenshot({path:path.join(out,'manual-tag-selection.png'),fullPage:true});
 const saved=page.waitForResponse(r=>r.url().endsWith('/api/posts')&&r.request().method()==='POST');await dialog.getByRole('button',{name:'下書きに保存',exact:true}).click();const created=await(await saved).json();posted=created.id;
 await expect(dialog).toHaveCount(0);const current=(await api('/communities/'+created.community_id+'/feed')).items.find(p=>p.id===posted);assert(current.tags.includes('cafe'));report.checks.push('known photo has predefined hints, manual selection is saved without inference');
 assert.equal(report.external.length,0);assert.equal(report.errors.length,0);report.passed=true;
}catch(e){report.failure=String(e.message).slice(0,1000);await page.screenshot({path:path.join(out,'failure.png'),fullPage:true});process.exitCode=1;}
finally{if(posted){try{await api('/posts/'+posted,'DELETE',{});report.cleanup=true;}catch{report.cleanup=false;report.passed=false;process.exitCode=1;}}await browser.close();await fs.writeFile(path.join(out,'browser.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));}
