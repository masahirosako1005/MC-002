import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(path.join(root,'qa/package.json'));
const {chromium,expect}=require('@playwright/test');
const phase=process.argv.includes('--before')?'before':'after';
const out=path.join(root,'community/artifacts/refresh');await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:900},locale:'ja-JP',reducedMotion:'reduce'}),page=await context.newPage();
const left=page.frameLocator('iframe[title="旅行者の操作画面"]'),right=page.frameLocator('iframe[title="事業者の操作画面"]');
const report={checkedAt:new Date().toISOString(),phase,viewport:{width:1440,height:900},measurement:'Same synthetic aoi account, default post-login travel home, no selected circle. DOM text intersecting first viewport excludes collapsed/hidden elements. Distances measured within phone.'};
async function login(scope,user){await scope.getByLabel('アカウント名',{exact:true}).fill(user);await scope.getByLabel('パスワード',{exact:true}).fill(user+'-local-2026');await scope.getByLabel('パスワード',{exact:true}).press('Enter');await expect(scope.locator('#main')).toBeVisible();}
try{
 await page.goto('http://127.0.0.1:8081/stage');report.entry=await page.locator('script[src*="/assets/index-"]').getAttribute('src');await login(left,'aoi');await login(right,'forest');await expect(left.locator('.market-plan-card').first()).toBeVisible();
 await left.locator('.market-plan-card img').first().evaluate(el=>el.complete||new Promise(resolve=>el.addEventListener('load',resolve,{once:true})));
 report.home=await left.locator('#main').evaluate(main=>{
  const first=main.querySelector('.market-plan-card img'),box=first?.getBoundingClientRect();
  const walker=document.createTreeWalker(main,NodeFilter.SHOW_TEXT);let chars=0,abovePhoto=0,node;
  while(node=walker.nextNode()){const parent=node.parentElement;if(!parent||parent.closest('.sr-only')||!node.textContent.trim())continue;const range=document.createRange();range.selectNodeContents(node);const rect=range.getBoundingClientRect(),css=getComputedStyle(parent);if(rect.width&&rect.height&&rect.bottom>0&&rect.top<innerHeight&&rect.right>0&&rect.left<innerWidth&&css.visibility!=='hidden'&&css.display!=='none'){const n=node.textContent.replace(/\s/g,'').length;chars+=n;if(rect.bottom<=(box?.top??0))abovePhoto+=n;}}
  return{firstPhotoTop:box?.top,firstPhotoWidth:box?.width,firstPhotoHeight:box?.height,viewportHeight:innerHeight,visibleTextCharacters:chars,textCharactersAboveFirstPhoto:abovePhoto,candidateCount:main.querySelectorAll('.market-plan-card').length,visiblePhotoArea:box?box.width*Math.max(0,Math.min(innerHeight,box.bottom)-Math.max(0,box.top)):0};
 });
 await page.screenshot({path:path.join(out,`${phase}-stage.png`)});
 await left.locator('.market-plan-card').first().scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,`${phase}-card.png`)});
 await left.locator('.market-plan-card').first().getByRole('button',{name:/詳|内容|行程/}).first().click();await expect(left.getByRole('dialog')).toBeVisible();await expect.poll(async()=>left.locator('.plan-detail-cover img').evaluate(el=>el.complete&&el.naturalWidth>0)).toBe(true);await left.locator('.plan-detail-cover img').evaluate(async el=>{await el.decode();await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));});await page.screenshot({path:path.join(out,`${phase}-detail.png`)});
 report.detailPhoto=await left.locator('.plan-detail-cover img').evaluate(img=>{const parent=img.parentElement;return{image:img.getBoundingClientRect().toJSON(),container:parent.getBoundingClientRect().toJSON(),opacity:getComputedStyle(img).opacity,visibility:getComputedStyle(img).visibility,naturalWidth:img.naturalWidth};});
 report.passed=true;
}catch(e){report.passed=false;report.error=String(e.message).slice(0,1000);process.exitCode=1;}
finally{await fs.writeFile(path.join(out,`${phase}.json`),JSON.stringify(report,null,2));console.log(JSON.stringify(report));await browser.close();}
