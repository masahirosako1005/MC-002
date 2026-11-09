import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';

// Run only after root schedules this browser task; do not run beside another QA browser.
// Credentials below are public synthetic fixture accounts. Tokens stay only in memory.
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(path.join(root,'qa/package.json'));
const {chromium,expect}=require('@playwright/test');
const base='http://127.0.0.1:8081';
const output=path.join(root,'community/artifacts/stage-security-browser.json');
const results=[],browserErrors=[],blockedExternal=[],sessions={};
const browser=await chromium.launch({channel:'msedge',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:900},locale:'ja-JP',timezoneId:'Asia/Tokyo'});
await context.route('**/*',async route=>{
  const url=new URL(route.request().url());
  if(!['127.0.0.1','localhost'].includes(url.hostname)){
    blockedExternal.push({blocked:true});await route.abort();
  }else await route.continue();
});
await context.addInitScript(()=>{
  // Observe only to test the existing listener; this does not alter its decisions.
  window.__stageSecurityMessages=[];
  window.addEventListener('message',event=>{
    if(window.top===window&&event.data?.source==='ko-stage'){
      window.__stageSecurityMessages.push(event.data);
    }
  });
});
const normal=await context.newPage(),stage=await context.newPage();
for(const page of [normal,stage])page.on('pageerror',error=>browserErrors.push(error.name||'BrowserError'));
const visitor=stage.frameLocator('iframe[title="旅行者の操作画面"]');
const provider=stage.frameLocator('iframe[title="事業者の操作画面"]');
let normalCookies,privateMediaUrl;

async function step(name,fn){
  try{await fn();results.push({name,status:'passed'});console.log('PASS '+name);}
  catch(error){
    // Deliberately do not serialize assertion operands, HTTP bodies or auth headers.
    results.push({name,status:'failed',error_type:error.name||'Error'});
    console.error('FAIL '+name);throw new Error('Stage security check failed: '+name);
  }
}
async function login(page,scope,username,isStage){
  await scope.getByRole('radio',{name:new RegExp(username)}).check();
  await scope.getByLabel('パスワード',{exact:true}).fill(`${username}-local-2026`);
  const pending=page.waitForResponse(r=>new URL(r.url()).pathname===(isStage?'/api/stage/login':'/api/login')&&r.request().method()==='POST');
  await scope.getByRole('button',{name:'ログイン',exact:true}).click();
  const response=await pending;assert(response.ok(),'login status');
  const record=await response.json();
  assert(record.user.username===username,'authenticated expected account');
  if(isStage){assert(!response.headers()['set-cookie'],'stage login must not mutate cookie');sessions[username]=record;}
  return record;
}
async function frameFor(kind){
  const frame=stage.frames().find(f=>new URL(f.url()||'about:blank').pathname===`/stage/${kind}`);
  assert(frame,'stage frame exists');return frame;
}
async function apiIn(frame,username,url,{method='GET',body,authorization,credentials='omit'}={}){
  const auth=sessions[username];
  return frame.evaluate(async args=>{
    const headers={Authorization:args.authorization??`Bearer ${args.token}`};
    if(args.method!=='GET'){headers['Content-Type']='application/json';headers['X-CSRF-Token']=args.csrf;}
    const response=await fetch('/api'+args.url,{method:args.method,headers,credentials:args.credentials,body:args.body===undefined?undefined:JSON.stringify(args.body),cache:'no-store'});
    const type=response.headers.get('content-type')||'';
    return {status:response.status,body:type.includes('application/json')?await response.json():null};
  },{token:auth.access_token,csrf:auth.csrf_token,url,method,body,authorization,credentials});
}
async function cookiesUnchanged(){
  const current=await context.cookies(base);
  assert(JSON.stringify(current)===normalCookies,'normal cookie must remain unchanged');
}
async function captionSnapshot(){return stage.locator('.stage-caption').evaluate(el=>JSON.stringify({text:el.textContent,event:el.dataset.event}));}

try{
  await step('normal cookie and two independent stage sessions coexist',async()=>{
    await normal.goto(base+'/');await login(normal,normal,'aoi',false);
    normalCookies=JSON.stringify(await context.cookies(base));assert((await context.cookies(base)).some(c=>c.name==='ko_session'),'normal session cookie exists');
    await stage.goto(base+'/stage');await login(stage,visitor,'aoi',true);await login(stage,provider,'forest',true);
    await visitor.getByRole('button',{name:'みんなの記録',exact:true}).click();
    await expect(visitor.locator('.post-card').first()).toBeVisible();
    await expect(provider.locator('.provider-workspace')).toBeVisible();
    const left=await apiIn(await frameFor('visitor'),'aoi','/me');
    const right=await apiIn(await frameFor('provider'),'forest','/me');
    assert(left.body.user.username==='aoi'&&right.body.user.username==='forest','separate authenticated identities');
    await cookiesUnchanged();
    const ordinary=await normal.evaluate(async()=>{const r=await fetch('/api/me',{credentials:'same-origin'});return (await r.json()).user.username;});
    assert(ordinary==='aoi','normal account unaffected');
  });

  await step('private image loads by authorized blob and is denied to provider and anonymous',async()=>{
    const left=await frameFor('visitor');
    const feed=await apiIn(left,'aoi','/communities/campus/feed');
    assert(feed.status===200,'private community feed available to author');
    privateMediaUrl=feed.body.items.flatMap(p=>p.media).map(m=>m.url)[0];
    assert(/^\/api\/media\/[A-Za-z0-9_-]+$/.test(privateMediaUrl),'private seeded photo exists');
    const photo=visitor.locator('.post-card img').first();
    await expect.poll(()=>photo.evaluate(i=>i.complete&&i.naturalWidth>0)).toBe(true);
    assert((await photo.getAttribute('src')).startsWith('blob:'),'stage image uses authenticated blob');
    const denied=await apiIn(await frameFor('provider'),'forest',privateMediaUrl.slice(4));
    assert(denied.status===404,'provider cannot read aoi private image');
    const anonymous=await left.evaluate(async url=>(await fetch(url,{credentials:'omit'})).status,privateMediaUrl);
    assert(anonymous===401,'no public private-image URL');
  });

  await step('bad bearer never falls back to the valid normal cookie',async()=>{
    const right=await frameFor('provider');
    for(const value of ['Bearer definitely-invalid-stage-token','Basic invalid','Bearer ']){
      const response=await apiIn(right,'forest','/me',{authorization:value,credentials:'include'});
      assert(response.status===401,'explicit invalid credential rejected without cookie fallback');
    }
    await cookiesUnchanged();
    const valid=await apiIn(right,'forest','/me');assert(valid.body.user.username==='forest','valid stage token still works');
  });

  await step('tokens are absent from browser storage, URLs and legitimate parent notifications',async()=>{
    const secrets=Object.values(sessions).flatMap(s=>[s.access_token,s.csrf_token]);
    for(const frame of stage.frames()){
      const audit=await frame.evaluate(values=>{
        const stored=JSON.stringify({local:{...localStorage},session:{...sessionStorage}});
        return {urlClean:values.every(v=>!location.href.includes(v)),storageClean:values.every(v=>!stored.includes(v)),authKeysAbsent:!/(access_token|csrf_token|bearer|authorization)/i.test(stored)};
      },secrets);
      assert(audit.urlClean&&audit.storageClean&&audit.authKeysAbsent,'no auth material in persistent browser surfaces');
    }
    const notifications=await stage.evaluate(values=>{
      const events=window.__stageSecurityMessages||[];
      return {count:events.length,clean:values.every(v=>!JSON.stringify(events).includes(v)),shape:events.every(e=>Object.keys(e).sort().join(',')==='source,status,type')};
    },secrets);
    assert(notifications.count>=2&&notifications.clean&&notifications.shape,'parent receives only event type and success state');
  });

  await step('scene caption ignores login, reads, failures, wrong sources and unknown events',async()=>{
    await expect(stage.locator('.stage-caption')).toHaveAttribute('data-event','initial');
    const before=await captionSnapshot();
    await stage.evaluate(()=>window.postMessage({source:'ko-stage',type:'selection',status:'success'},location.origin));
    await stage.evaluate(()=>{
      const child=document.querySelector('iframe[title="旅行者の操作画面"]').contentWindow;
      window.dispatchEvent(new MessageEvent('message',{origin:'https://untrusted.invalid',source:child,data:{source:'ko-stage',type:'selection',status:'success'}}));
      window.dispatchEvent(new MessageEvent('message',{origin:location.origin,source:child,data:{source:'ko-stage',type:'__unrecognized_event__',status:'success'}}));
      window.dispatchEvent(new MessageEvent('message',{origin:location.origin,source:child,data:{source:'ko-stage',type:'selection',status:'pending'}}));
      for(const [type,status] of [['selection','failure'],['session','success'],['consultation-read','success'],['photo','success']]){
        window.dispatchEvent(new MessageEvent('message',{origin:location.origin,source:child,data:{source:'ko-stage',type,status}}));
      }
    });
    // Flush posted-message and React scheduling, without fixed long sleeps.
    await stage.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    assert(await captionSnapshot()===before,'ignored events do not change the scene caption');
  });

  await step('only the two stage HTML pages permit same-origin embedding; API remains denied',async()=>{
    for(const target of ['/stage/visitor','/stage/provider']){
      const response=await context.request.get(base+target);
      assert(response.ok()&&response.headers()['content-type'].startsWith('text/html'),'stage document delivered');
      assert(response.headers()['x-frame-options']==='SAMEORIGIN','stage frame restriction');
      assert(response.headers()['content-security-policy'].includes("frame-ancestors 'self'"),'same origin ancestor only');
    }
    for(const target of ['/','/stage','/api/health','/api/marketplace/capabilities']){
      const response=await context.request.get(base+target);
      assert(response.headers()['x-frame-options']==='DENY','other endpoint remains deny');
      assert(response.headers()['content-security-policy'].includes("frame-ancestors 'none'"),'other endpoint ancestor restriction');
    }
    await stage.evaluate(()=>new Promise((resolve,reject)=>{
      const frame=document.createElement('iframe');frame.id='forbidden-api-frame';
      const timer=setTimeout(()=>reject(new Error('API frame load did not finish')),10000);
      frame.onload=()=>{clearTimeout(timer);resolve();};
      frame.src='/api/health';document.body.append(frame);
    }));
    await expect.poll(()=>stage.locator('#forbidden-api-frame').evaluate(f=>{
      try{return !f.contentDocument||!f.contentDocument.body?.textContent?.includes('"status":"ok"');}catch{return true;}
    })).toBe(true);
    await stage.locator('#forbidden-api-frame').evaluate(f=>f.remove());
  });

  await step('logging out one phone revokes only that token and leaves the other phone and cookie working',async()=>{
    await provider.getByRole('button',{name:/森の旅案内 アカウントを切り替える/}).click();
    const dialog=provider.getByRole('dialog');
    const pending=stage.waitForResponse(r=>new URL(r.url()).pathname==='/api/logout'&&r.request().method()==='POST');
    await dialog.getByRole('button',{name:'ログアウトして切り替える',exact:true}).click();
    const response=await pending;assert(response.ok()&&!response.headers()['set-cookie'],'stage logout does not delete normal cookie');
    await expect(provider.getByRole('button',{name:'ログイン',exact:true})).toBeVisible();
    const revoked=await apiIn(await frameFor('provider'),'forest','/me');assert(revoked.status===401,'old right token revoked');
    const left=await apiIn(await frameFor('visitor'),'aoi','/me');assert(left.body.user.username==='aoi','left token remains valid');
    await expect(visitor.locator('.post-card').first()).toBeVisible();await cookiesUnchanged();
    const ordinary=await normal.evaluate(async()=>(await(await fetch('/api/me',{credentials:'same-origin'})).json()).user.username);
    assert(ordinary==='aoi','normal cookie remains usable after stage logout');
  });

  await step('no external requests or uncaught browser errors',async()=>{
    assert(blockedExternal.length===0,'all resources local');assert(browserErrors.length===0,'no uncaught browser errors');
  });
}finally{
  await fs.mkdir(path.dirname(output),{recursive:true});
  await fs.writeFile(output,JSON.stringify({checked_at:new Date().toISOString(),url:base,scope:'Browser security regression for local synthetic accounts and trusted same-origin stage frames',results,passed:results.length===8&&results.every(r=>r.status==='passed'),blocked_external_count:blockedExternal.length,browser_error_types:browserErrors,limits:['Does not claim isolation from malicious same-origin JavaScript or extensions.','Natural 30-minute expiry is verified by backend tests; this browser run tests explicit token revocation.','Synthetic account data only; no accuracy or real-user effectiveness claim.'],backend_evidence:'community/artifacts/marketplace-backend-verification.json'},null,2));
  await browser.close();
}
