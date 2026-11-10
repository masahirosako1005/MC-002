import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {spawnSync} from 'node:child_process';
import {performance} from 'node:perf_hooks';
import assert from 'node:assert/strict';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const output=path.join(root,'artifacts/community/intro-video');
const python=path.join(root,'.venv/Scripts/python.exe');
process.env.PLAYWRIGHT_BROWSERS_PATH=path.join(root,'.tools/playwright-browsers');
const require=createRequire(path.join(root,'test/browser/package.json'));
const {chromium,expect}=require('@playwright/test');
const mode=process.argv[2];
if(mode!=='--record') {
  const check=spawnSync(python,['-c','import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())'],{encoding:'utf8'});
  if(check.status!==0) throw new Error('Project imageio-ffmpeg dependency is missing');
  console.log(JSON.stringify({ready:true,viewport:[1440,900],seconds:20,ffmpeg:check.stdout.trim(),browserStarted:false,recordCommand:'node scripts/create_intro_video.mjs --record'}));
  process.exit(0);
}
await fs.mkdir(path.join(output,'raw'),{recursive:true});
const report={targetSeconds:20,viewport:{width:1440,height:900},actions:[],blockedRequests:[],errors:[],network:{reads:0,loginWrites:0},scope:'Actual local UI; public synthetic accounts; login and read-only browse/detail only; no recording of typed credentials'};
const browser=await chromium.launch({channel:'msedge',headless:true});
report.browser=browser.version();
const context=await browser.newContext({viewport:report.viewport,deviceScaleFactor:1,locale:'ja-JP',recordVideo:{dir:path.join(output,'raw'),size:report.viewport}});
let page,video,started;
try {
  await context.route('**/*',async route=>{
    const request=route.request(),url=new URL(request.url());
    const local=['127.0.0.1','localhost'].includes(url.hostname);
    const write=!['GET','HEAD','OPTIONS'].includes(request.method());
    const login=write&&request.method()==='POST'&&url.pathname==='/api/stage/login';
    if(!local||(write&&!login)) {
      report.blockedRequests.push({type:local?'non-login-write':'external',method:request.method()});
      return route.abort();
    }
    if(login) report.network.loginWrites++;
    else report.network.reads++;
    await route.continue();
  });
  page=await context.newPage();video=page.video();
  page.on('pageerror',error=>report.errors.push(error.name));
  await page.goto('http://127.0.0.1:8081/stage');
  const leftSelector='iframe[title="利用者のスマートフォン画面"]',rightSelector='iframe[title="事業者のパソコン管理画面"]';
  const left=page.frameLocator(leftSelector),right=page.frameLocator(rightSelector);
  for(const [frame,user] of [[left,'aoi'],[right,'forest']]) {
    await frame.getByLabel('アカウント名',{exact:true}).fill(user);
    await frame.getByLabel('パスワード',{exact:true}).fill(user+'-local-2026');
    await expect(frame.getByLabel('パスワード',{exact:true})).toHaveAttribute('type','password');
  }
  await page.evaluate(()=>document.fonts.ready);
  const overlayCSS=await page.evaluate(()=>{
    const style=document.createElement('style');style.id='intro-video-style';
    style.textContent=`#intro-video-overlay{position:fixed;inset:0;pointer-events:none;z-index:2147483000;font-family:"Yu Gothic UI","Meiryo",sans-serif}#intro-focus{position:fixed;border:3px solid #ffe4bb;border-radius:18px;box-shadow:0 0 0 5000px rgba(22,15,10,.57),0 0 0 6px rgba(255,228,187,.2);transition:left .16s ease,top .16s ease,width .16s ease,height .16s ease}#intro-caption{position:fixed;left:260px;top:14px;width:920px;height:76px;box-sizing:border-box;padding:10px 28px;background:#6f3024;color:#fff8ec;border-radius:18px;box-shadow:0 8px 24px rgba(30,15,10,.2);display:flex;gap:20px;align-items:center;font-weight:700;font-size:25px;letter-spacing:.02em}#intro-step{font-size:13px;white-space:nowrap;color:#f4c9aa}#intro-cursor{position:fixed;width:22px;height:28px;display:none;filter:drop-shadow(0 2px 2px #0008)}#intro-ring{position:fixed;width:34px;height:34px;border:3px solid #fff1ca;border-radius:50%;display:none;box-shadow:0 0 0 3px #8e392a80;transform:translate(-50%,-50%)}`;
    const overlay=document.createElement('div');overlay.id='intro-video-overlay';
    overlay.innerHTML='<div id="intro-focus"></div><div id="intro-caption"><span id="intro-step"></span><span id="intro-text"></span></div><div id="intro-cursor"><svg viewBox="0 0 24 30"><path d="M2 1L3 25L9 19L14 29L19 26L14 17L23 16Z" fill="#fff9ee" stroke="#3b2319" stroke-width="2"/></svg></div><div id="intro-ring"></div>';
    overlay.style.visibility='hidden';document.body.append(overlay);
    return style.textContent;
  });
  // Keep the application's CSP intact. The temporary capture context serves a
  // same-origin stylesheet; nothing is installed in the app or its web server.
  await page.route('**/__intro_video_overlay.css',route=>route.fulfill({status:200,contentType:'text/css',body:overlayCSS}));
  await page.evaluate(()=>new Promise((resolve,reject)=>{const link=document.createElement('link');link.rel='stylesheet';link.href='/__intro_video_overlay.css';link.onload=resolve;link.onerror=reject;document.head.append(link);}));
  assert.equal(await page.locator('#intro-caption').evaluate(el=>getComputedStyle(el).position),'fixed');
  async function geometry(locator,frameSelector,padding=8) {
    const rect=await locator.evaluate(el=>{const r=el.getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height};});
    const frame=await page.locator(frameSelector).boundingBox();assert(frame);
    const x=Math.max(frame.x,frame.x+rect.x-padding),y=Math.max(frame.y,frame.y+rect.y-padding);
    const right=Math.min(frame.x+frame.width,frame.x+rect.x+rect.width+padding),bottom=Math.min(frame.y+frame.height,frame.y+rect.y+rect.height+padding);
    assert(right>x&&bottom>y,'Target is outside the visible phone');
    return {x,y,width:right-x,height:bottom-y};
  }
  async function focus(locator,frameSelector,step,caption) {
    const rect=await geometry(locator,frameSelector);
    await page.evaluate(({rect,step,caption})=>{
      const focus=document.getElementById('intro-focus');Object.assign(focus.style,{left:rect.x+'px',top:rect.y+'px',width:rect.width+'px',height:rect.height+'px'});
      document.getElementById('intro-step').textContent=step+' / 04';document.getElementById('intro-text').textContent=caption;
    },{rect,step,caption});
    return rect;
  }
  async function click(locator,frameSelector,label) {
    await locator.scrollIntoViewIfNeeded();
    const rect=await geometry(locator,frameSelector,0),x=rect.x+rect.width/2,y=rect.y+rect.height/2;
    await page.mouse.move(x,y,{steps:10});
    await page.evaluate(({x,y})=>{const cursor=document.getElementById('intro-cursor');Object.assign(cursor.style,{display:'block',left:x+'px',top:y+'px'});const ring=document.getElementById('intro-ring');Object.assign(ring.style,{display:'block',left:x+'px',top:y+'px'});},{x,y});
    await page.waitForTimeout(220);
    await page.mouse.click(x,y);
    report.actions.push({type:'click',label,seconds:Number(((performance.now()-started)/1000).toFixed(2)),position:{x:Math.round(x),y:Math.round(y)}});
    await page.waitForTimeout(200);
    await page.evaluate(()=>{document.getElementById('intro-ring').style.display='none';document.getElementById('intro-cursor').style.display='none';});
  }
  async function until(seconds) {
    const remaining=seconds*1000-(performance.now()-started);
    if(remaining>0) await page.waitForTimeout(remaining);
  }
  async function still(name) {await page.screenshot({path:path.join(output,name+'.png')});}
  await focus(left.locator('.welcome-form'),leftSelector,'01','アカウントを入力して、ログイン');
  started=performance.now();
  await page.evaluate(()=>document.getElementById('intro-video-overlay').style.visibility='visible');
  await until(.7);await still('01-login');
  await until(1.4);await click(left.getByRole('button',{name:'ログイン',exact:true}),leftSelector,'traveler login');
  await focus(right.locator('.welcome-form'),rightSelector,'01','アカウントを入力して、ログイン');
  await click(right.getByRole('button',{name:'ログイン',exact:true}),rightSelector,'provider login');
  await expect(left.locator('.market-plan-card').first()).toBeVisible();
  await expect(right.locator('.market-plan-card').first()).toBeVisible();
  await until(4);
  const search=left.locator('.plan-discovery input[type="search"]');
  await expect(search).toBeVisible();
  await focus(search,leftSelector,'02','気になる場所から、旅のプランを探す');
  await click(search,leftSelector,'search public plans');
  await search.pressSequentially('森',{delay:160});
  report.actions.push({type:'search',label:'public woodland plans',seconds:Number(((performance.now()-started)/1000).toFixed(2))});
  const card=left.locator('.market-plan-card').first();
  await expect(card).toBeVisible();
  await card.locator('img').evaluate(async image=>{if(!image.complete) await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject;});if(!image.naturalWidth) throw new Error('Public plan photo did not load');});
  await focus(card,leftSelector,'02','写真を見ながら、旅のプランを探す');
  await until(7);await still('02-explore');
  await until(9);
  await click(card.locator('.plan-photo-button'),leftSelector,'open actual public plan');
  const dialog=left.getByRole('dialog',{name:'プランの行程と費用'});
  await expect(dialog).toBeVisible();
  const facts=dialog.locator('.plan-detail-facts');
  await facts.scrollIntoViewIfNeeded();
  await focus(facts,leftSelector,'03','人数・泊数・エリアを確かめる');
  await until(11);await still('03-detail');
  await until(13.2);
  const price=dialog.locator('.price-summary');
  await price.scrollIntoViewIfNeeded();
  await focus(price,leftSelector,'03','料金と、費用に含まれる内容を確認');
  await until(14.5);await still('04-price');
  await until(15.2);
  const itinerary=dialog.locator('.day-itinerary');
  await itinerary.scrollIntoViewIfNeeded();
  await focus(itinerary,leftSelector,'04','行程・訪問先まで、詳しく確認');
  report.actions.push({type:'scroll',label:'read actual itinerary',seconds:Number(((performance.now()-started)/1000).toFixed(2))});
  await until(17.4);await still('05-itinerary');
  assert(performance.now()-started<19500,'Actions exceeded the allotted 20-second introduction');
  assert.equal(report.blockedRequests.length,0);assert.equal(report.errors.length,0);
  await until(20.4);
  await page.evaluate(()=>document.getElementById('intro-video-overlay').style.visibility='hidden');
  await page.waitForTimeout(650);
  report.timelineCompleted=true;
} catch(error) {
  report.timelineCompleted=false;report.failure={name:error.name,message:error.message.slice(0,400)};
  throw error;
} finally {
  await context.close();
  if(video) report.rawVideo=path.relative(root,await video.path()).replaceAll('\\','/');
  report.checkedAt=new Date().toISOString();
  await fs.writeFile(path.join(output,'recording.json'),JSON.stringify(report,null,2));
  await browser.close();
}
const encoded=spawnSync(python,[path.join(root,'scripts/encode_intro_video.py'),path.join(root,report.rawVideo)],{encoding:'utf8',windowsHide:true});
if(encoded.status!==0) throw new Error('Video encoding or verification failed: '+encoded.stderr.slice(-1500));
console.log(encoded.stdout.trim());
