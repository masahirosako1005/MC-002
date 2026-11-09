import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const {chromium,expect}=createRequire(path.join(root,'qa/package.json'))('@playwright/test');
const base='http://127.0.0.1:8081',out=path.join(root,'community/artifacts/marketplace-browser');
const evidence=JSON.parse(await fs.readFile(path.join(out,'results.json'),'utf8'));
const expectedBundle=process.env.KO_EXPECTED_BUNDLE;
assert(expectedBundle,'set KO_EXPECTED_BUNDLE to the verified build output');
const browser=await chromium.launch({channel:'msedge',headless:true});
try{
 const context=await browser.newContext({viewport:{width:1440,height:900},locale:'ja-JP'});
 const page=await context.newPage();await page.goto(base+'/stage');
 const left=page.frameLocator('iframe[title="旅行者の操作画面"]'),right=page.frameLocator('iframe[title="事業者の操作画面"]');
 const sessions={};
 for(const[frame,user]of[[left,'aoi'],[right,'forest']]){
  await frame.getByRole('radio',{name:new RegExp(user)}).check();await frame.getByLabel('パスワード',{exact:true}).fill(`${user}-local-2026`);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/stage/login')&&r.request().method()==='POST');await frame.getByRole('button',{name:'ログイン',exact:true}).click();sessions[user]=await(await response).json();
  await expect(frame.locator('.market-plan-card').first()).toBeVisible();await expect.poll(()=>frame.locator('.market-plan-card img').first().evaluate(i=>i.complete&&i.naturalWidth>0)).toBe(true);
 }
 await page.screenshot({path:path.join(out,'stage-overview-final.png'),fullPage:true});
 await right.getByRole('button',{name:'届いた相談',exact:true}).click();
 const row=right.locator(`[data-consultation-id="${evidence.syntheticRecords.consultationId}"]`);await expect(row).toContainText('6人');await expect(row).toContainText('2泊3日');await expect(row).toContainText('集合時間を相談');await row.click();await expect(right.getByRole('dialog')).toContainText('13時集合');
 const html=await(await context.request.get(base)).text();assert(html.includes(expectedBundle));
 assert.equal(await left.locator('select').count()+await right.locator('select').count(),0);
 assert(!/デモ|試作|模擬|ダミー/.test((await left.locator('body').innerText())+(await right.locator('body').innerText())));
 await page.screenshot({path:path.join(out,'stage-reply-final.png'),fullPage:true});
 await fs.writeFile(path.join(out,'final-smoke.json'),JSON.stringify({time:new Date().toISOString(),bundle:expectedBundle,passed:true,viewport:{width:1440,height:900},checks:['two phone real logins and images','consultation rows show shared headcount nights date and note','existing reply persisted and rendered','no native selects or production-side demo labels'],screenshot:['stage-overview-final.png','stage-reply-final.png']},null,2));
 console.log('PASS final stage display and consultation summary');
}finally{await browser.close();}
