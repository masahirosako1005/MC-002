import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {performance} from 'node:perf_hooks';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const {chromium,expect}=createRequire(path.join(root,'qa/package.json'))('@playwright/test');
const browser=await chromium.launch({channel:'msedge',headless:true});
const errors=[],external=[],switches=[];
const report={scope:'Isolated headless Edge profile; does not reproduce the existing visible Edge profile, extensions or compositor',browser:browser.version(),errors,external,switches};
try {
  const context=await browser.newContext({viewport:{width:1440,height:900},locale:'ja-JP'});
  await context.route('**/*',async route=>{
    const u=new URL(route.request().url());
    if(!['127.0.0.1','localhost'].includes(u.hostname)){external.push(u.origin);await route.abort();}
    else await route.continue();
  });
  await context.addInitScript(()=>{
    window.__performanceAudit=[];
    new PerformanceObserver(list=>{
      for(const task of list.getEntries()) window.__performanceAudit.push(Math.round(task.duration));
    }).observe({type:'longtask',buffered:true});
  });
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.name));
  const start=performance.now();await page.goto('http://127.0.0.1:8081/stage');
  const left=page.frameLocator('iframe[title="旅行者の操作画面"]');
  const right=page.frameLocator('iframe[title="事業者の操作画面"]');
  await expect(left.getByRole('button',{name:'ログイン',exact:true})).toBeVisible();
  await expect(right.getByRole('button',{name:'ログイン',exact:true})).toBeVisible();
  report.bothLoginScreensMs=Math.round(performance.now()-start);
  for(const [frame,name] of [[left,'aoi'],[right,'forest']]){
    await frame.getByLabel('アカウント名',{exact:true}).fill(name);
    await frame.getByLabel('パスワード',{exact:true}).fill(`${name}-local-2026`);
    await frame.getByRole('button',{name:'ログイン',exact:true}).click();
    await expect(frame.locator('.market-plan-card').first()).toBeVisible();
  }
  const targets=[
    [left,'みんなの記録','.post-card'],[left,'旅を見つける','.market-plan-card'],
    [right,'届いた相談','.consultation-row'],[right,'自社のプラン','.market-plan-card'],
  ];
  for(let cycle=0;cycle<10;cycle++)for(const [frame,label,selector] of targets){
    const begun=performance.now();await frame.getByRole('button',{name:label,exact:true}).click();
    await expect(frame.locator(selector).first()).toBeVisible();
    switches.push({section:label,ms:Math.round(performance.now()-begun)});
  }
  report.frames=await Promise.all(page.frames().map(async f=>({path:new URL(f.url()).pathname,...await f.evaluate(()=>({longTasks:window.__performanceAudit||[],domNodes:document.getElementsByTagName('*').length}))})));
  const sorted=switches.map(v=>v.ms).sort((a,b)=>a-b);
  report.summary={count:sorted.length,medianMs:sorted[Math.floor(sorted.length/2)],p95Ms:sorted[Math.ceil(sorted.length*.95)-1],maxMs:sorted.at(-1)};
  assert.equal(errors.length,0);assert.equal(external.length,0);report.passed=true;
  console.log(JSON.stringify({bothLoginScreensMs:report.bothLoginScreensMs,...report.summary,passed:true}));
} catch(e) {report.passed=false;report.failureType=e.name;throw e;}
finally {
  report.checkedAt=new Date().toISOString();
  await fs.writeFile(path.join(root,'community/artifacts/navigation-performance.json'),JSON.stringify(report,null,2));
  await browser.close();
}
