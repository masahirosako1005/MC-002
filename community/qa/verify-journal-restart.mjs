import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const base='http://127.0.0.1:8081/api';let session,journey;
async function request(url,method='GET',body){const options={method,headers:{'Content-Type':'application/json',Connection:'close',Origin:'http://127.0.0.1:8081',...(session?{Authorization:`Bearer ${session.access_token}`,'X-CSRF-Token':session.csrf_token}:{})},body:body?JSON.stringify(body):undefined};let r;try{r=await fetch(base+url,options);}catch(e){if(method!=='GET')throw e;r=await fetch(base+url,options);}assert(r.ok,`${url} ${r.status}`);return r.json();}
const report={checkedAt:new Date().toISOString(),passed:false,scope:'Temporary confirmed visit and linked badge across Docker restart; test records cleaned up'};
try{
 session=await request('/stage/login','POST',{username:'aoi',password:'aoi-local-2026'});
 journey=await request('/journal/journeys','POST',{title:'保存確認用の旅',request_key:crypto.randomUUID()});
 for(const id of ['21','22','23','24'])await request('/journal/visits','POST',{journey_id:journey.id,prefecture_id:id,visited_on:'2026-11-01',place_label:'保存確認の訪問',latitude:null,longitude:null,media_id:null,source:'manual',visibility:'private',community_id:null,confirmed:true,request_key:crypto.randomUUID()});
 const before=await request(`/journal/journeys/${journey.id}`);const beforeBadge=(await request('/journal/profile/u-aoi')).badges;
 const result=spawnSync(path.join(root,'.venv/Scripts/python.exe'),['-X','utf8','community/scripts/verify_journal_storage.py','restart-check'],{cwd:root,encoding:'utf8',timeout:120000});
 assert.equal(result.status,0,result.stdout.slice(-1200));
 const after=await request(`/journal/journeys/${journey.id}`);const afterBadge=(await request('/journal/profile/u-aoi')).badges;
 assert.deepEqual(after,before);assert.deepEqual(afterBadge,beforeBadge);assert.equal(afterBadge[0].earned,true);report.passed=true;report.confirmedVisits=after.visits.length;
}finally{
 try{if(journey){const j=await request(`/journal/journeys/${journey.id}`);await request(`/journal/journeys/${journey.id}`,'DELETE',{version:j.journey.version});}report.cleanup=true;}catch{report.cleanup=false;report.passed=false;}
 await fs.writeFile(path.join(root,'community/artifacts/journal/restart-api.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));if(!report.passed)process.exitCode=1;
}
