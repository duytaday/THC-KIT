'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {controller,label,inside}=require('../bridge/main.cjs');
async function fixture(backend='cuda-scale-cpu-pad'){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'recordly-unit-'));const native=path.join(root,'recordings');const projects=path.join(root,'projects');fs.mkdirSync(native);fs.mkdirSync(projects);
 const calls=[];const source={id:'window:123:0',name:'Synthetic unit window'};let present=true,sourceError=false,changeOnSelect=false,sourceTime=Date.now();
 const invoke=async(channel,...args)=>{calls.push({channel,args});
  if(channel==='get-sources'){if(sourceError)throw Error('Synthetic source listing error');return present?[source]:[];}
  if(channel==='select-source'&&changeOnSelect)source.name='Unexpected window';
  if(channel==='get-recordings-directory')return {success:true,path:native};
  if(channel==='get-projects-directory')return {success:true,path:projects};
  if(channel==='stop-native-screen-recording'){const p=path.join(native,'recording-unit.mp4');fs.writeFileSync(p,'UNIT FIXTURE NOT VIDEO');return {success:true,path:p};}
  if(channel==='probe-native-video-metadata')return {success:true,metadata:{width:1280,height:720,duration:6}};
  if(channel==='save-project-file-named'){const p=path.join(projects,args[1]+'.recordly');fs.writeFileSync(p,JSON.stringify(args[0]));return {success:true,path:p};}
  if(channel==='native-static-layout-export'){const p=path.join(root,'native-export.mp4');fs.writeFileSync(p,'UNIT EXPORT NOT VIDEO');return {success:true,tempPath:p,encoderName:'static-layout-h264-nvenc',metrics:{chunks:[{backend}]}};}
  if(channel==='finalize-exported-video'){fs.copyFileSync(args[0].tempPath,args[0].outputPath,fs.constants.COPYFILE_EXCL);return {success:true,path:args[0].outputPath};}
  return {success:true};
 };
 const c=await controller({root,invoke,sourceCheckMs:5,sourceClock:()=>sourceTime});return {root,c,calls,source,disappear:()=>present=false,failSource:()=>sourceError=true,changeAfterSelection:()=>changeOnSelect=true,advanceSourceTime:ms=>sourceTime+=ms};
}
const start=f=>({command:'start',request_id:'start-request-001',params:{window_id:f.source.id,expected_title:f.source.name,beat:'unit-beat',max_seconds:5}});
test('Concurrent/reordered retries start native capture once; changed payload conflicts',async()=>{
 const f=await fixture();try{const request=start(f);const [a,b]=await Promise.all([f.c.dispatch(request),f.c.dispatch(request)]);assert.equal(a.capture_id,b.capture_id);
  assert.equal(f.calls.filter(c=>c.channel==='start-native-screen-recording').length,1);
  const retry={...request,params:{beat:'unit-beat',max_seconds:5,expected_title:f.source.name,window_id:f.source.id}};assert.equal((await f.c.dispatch(retry)).replayed,true);
  await assert.rejects(f.c.dispatch({...request,params:{...request.params,beat:'other'}}),/conflict/);
  const options=f.calls.find(c=>c.channel==='start-native-screen-recording').args[1];assert.deepEqual(options,{capturesSystemAudio:false,capturesMicrophone:false});
 }finally{f.c.close();}
});

test('Unverified CUDA overlay backend cannot finalize a delivery',async()=>{
 const f=await fixture('cuda-overlay');try{
  const a=await f.c.dispatch(start(f));await f.c.dispatch({command:'stop',request_id:'stop-request-001',params:{capture_id:a.capture_id}});
  await assert.rejects(f.c.dispatch({command:'export',request_id:'export-request-001',params:{capture_id:a.capture_id,name:'rejected-export'}}),/unverified static backend/);
  assert(!f.calls.some(c=>c.channel==='finalize-exported-video'));
 }finally{f.c.close();}
});
test('Disappeared/changed source never falls back to another window',async()=>{
 const f=await fixture();try{f.disappear();await assert.rejects(f.c.dispatch(start(f)),/disappeared/);assert(!f.calls.some(c=>c.channel==='start-native-screen-recording'));}finally{f.c.close();}
});
test('Stop retains source/native project; duplicate stop and export do not overwrite',async()=>{
 const f=await fixture();try{
  const a=await f.c.dispatch(start(f));const request={command:'stop',request_id:'stop-request-001',params:{capture_id:a.capture_id}};
  const stopped=await f.c.dispatch(request);assert(fs.existsSync(stopped.source));assert(fs.existsSync(stopped.project));
  assert.equal((await f.c.dispatch(request)).replayed,true);assert.equal(f.calls.filter(c=>c.channel==='stop-native-screen-recording').length,1);
  const exp={command:'export',request_id:'export-request-001',params:{capture_id:a.capture_id,name:'unit-export',seconds:5}};
  const output=await f.c.dispatch(exp);assert.equal(output.encoder,'static-layout-h264-nvenc');assert.equal(output.review,'NEEDS_REVIEW');
  const exportIndex=f.calls.findIndex(c=>c.channel==='native-static-layout-export');assert.equal(f.calls[exportIndex-1].channel,'open-project-file-at-path');
  assert(!('sourceCropWidth' in f.calls[exportIndex].args[0]));assert.equal(f.calls[exportIndex].args[0].contentWidth%2,0);
  assert.equal((await f.c.dispatch(exp)).replayed,true);assert.equal(f.calls.filter(c=>c.channel==='native-static-layout-export').length,1);
  await assert.rejects(f.c.dispatch({...exp,request_id:'export-request-002'}),/exists/);
 }finally{f.c.close();}
});
test('Unknown parameters, unsafe names and mismatched capture IDs are denied',async()=>{
 const f=await fixture();try{
  await assert.rejects(f.c.dispatch({...start(f),params:{...start(f).params,capturesSystemAudio:true}}),/Unknown parameters/);
  await assert.rejects(f.c.dispatch({command:'delete-recording-file',request_id:'dangerous-request',params:{}}),/Unknown command/);
  await assert.rejects(f.c.dispatch({command:'stop',request_id:'stop-wrong-001',params:{capture_id:'foreign'}}),/does not match/);
  for(const s of ['../escape','C:\\escape','CON','file.mp4'])assert.throws(()=>label(s));
  assert(!inside(path.join(f.root,'..','foreign'),f.root));
 }finally{f.c.close();}
});
test('Restored completed ledger responds without repeating native calls',async()=>{
 const f=await fixture();try{
  const a=await f.c.dispatch(start(f));await f.c.dispatch({command:'stop',request_id:'stop-request-001',params:{capture_id:a.capture_id}});f.c.close();
  const restored=await controller({root:f.root,invoke:async()=>{throw Error('No call expected');}});
  try{const response=await restored.dispatch(start(f));assert(response.replayed);assert.equal(response.capture_id,a.capture_id);}finally{restored.close();}
 }finally{f.c.close();}
});

async function stopped(f){
 const deadline=Date.now()+2000;
 while(Date.now()<deadline){const s=await f.c.dispatch({command:'status'});if(s.capture.stage==='STOPPED')return s.capture;await new Promise(r=>setTimeout(r,5));}
 throw Error('Guard did not stop capture');
}
for(const [name,change,reason] of [
 ['title change',f=>f.source.name='Different application title','SELECTED_WINDOW_TITLE_CHANGED'],
 ['missing window',f=>f.disappear(),'SELECTED_WINDOW_MISSING'],
 ['source list failure',f=>f.failSource(),'SOURCE_CHECK_UNAVAILABLE']
])test('During capture: '+name+' stops once, preserves project and blocks export',async()=>{
 const f=await fixture();try{
  const a=await f.c.dispatch(start(f));change(f);const c=await stopped(f);
  assert.equal(c.source_guard.status,'FAILED');assert.equal(c.source_guard.reason,reason);assert(fs.existsSync(c.source));assert(fs.existsSync(c.project));
  assert.equal(f.calls.filter(c=>c.channel==='stop-native-screen-recording').length,1);
  const again=await f.c.dispatch({command:'stop',request_id:'stop-after-guard',params:{capture_id:a.capture_id}});assert.equal(again.source_guard.status,'FAILED');
  await assert.rejects(f.c.dispatch({command:'export',request_id:'guard-export-001',params:{capture_id:a.capture_id,name:'must-not-export'}}),/quarantined/);
  assert(!f.calls.some(c=>c.channel==='native-static-layout-export'));
 }finally{f.c.close();}
});
test('Selection race is rejected before native recording starts',async()=>{
 const f=await fixture();try{f.changeAfterSelection();await assert.rejects(f.c.dispatch(start(f)),/changed after selection/);assert(!f.calls.some(c=>c.channel==='start-native-screen-recording'));}finally{f.c.close();}
});
test('Manual stop checks the source even before the first polling tick',async()=>{
 const f=await fixture();try{const a=await f.c.dispatch(start(f));f.source.name='Unexpected';const c=await f.c.dispatch({command:'stop',request_id:'stop-before-tick',params:{capture_id:a.capture_id}});assert.equal(c.source_guard.status,'FAILED');assert.equal(c.source_guard.reason,'SELECTED_WINDOW_TITLE_CHANGED');}finally{f.c.close();}
});
test('Unchanged source records limited evidence without claiming isolation',async()=>{
 const f=await fixture();try{const a=await f.c.dispatch(start(f));const c=await f.c.dispatch({command:'stop',request_id:'stop-clean-guard',params:{capture_id:a.capture_id}});assert.equal(c.source_guard.status,'MONITORED_NO_CHANGE_OBSERVED');assert(c.source_guard.checks>=1);assert.match(c.source_guard.limitation,/cannot prove pixel isolation/);}finally{f.c.close();}
});

async function planNavigation(f){
 const initial=f.source.name;await f.c.dispatch({command:'sources'});f.source.name='Approved Releases page';await f.c.dispatch({command:'sources'});f.source.name=initial;
 const request=start(f);request.params.allowed_titles=[initial,'Approved Releases page'];return request;
}
test('Observed planned navigation keeps the same capture running and exports without expanding titles',async()=>{
 const f=await fixture();try{const req=await planNavigation(f);const a=await f.c.dispatch(req);f.source.name='Approved Releases page';await new Promise(r=>setTimeout(r,25));const status=await f.c.dispatch({command:'status'});assert.equal(status.capture.stage,'CAPTURING');assert.deepEqual(status.capture.allowed_titles,req.params.allowed_titles);
 const c=await f.c.dispatch({command:'stop',request_id:'planned-stop-001',params:{capture_id:a.capture_id}});assert.equal(c.source_guard.status,'MONITORED_NO_CHANGE_OBSERVED');const e=await f.c.dispatch({command:'export',request_id:'planned-export-001',params:{capture_id:a.capture_id,name:'planned-navigation'}});assert.equal(e.review,'NEEDS_REVIEW');assert.equal(e.source_guard.policy,'exact_frozen_title_list');
 }finally{f.c.close();}
});
test('Unobserved and stale additional titles are rejected before native start',async()=>{
 const f=await fixture();try{const req=start(f);req.params.allowed_titles=[f.source.name,'Unobserved title'];await assert.rejects(f.c.dispatch(req),/fresh recordly_sources/);const observed=await planNavigation(f);observed.request_id='stale-navigation-001';f.advanceSourceTime(300001);await assert.rejects(f.c.dispatch(observed),/fresh recordly_sources/);assert(!f.calls.some(c=>c.channel==='start-native-screen-recording'));}finally{f.c.close();}
});
test('A title observed on a different window ID cannot authorize navigation',async()=>{
 const f=await fixture();try{const id=f.source.id,name=f.source.name;f.source.id='window:999:0';f.source.name='Other window title';await f.c.dispatch({command:'sources'});f.source.id=id;f.source.name=name;const req=start(f);req.params.allowed_titles=[name,'Other window title'];await assert.rejects(f.c.dispatch(req),/same window/);assert(!f.calls.some(c=>c.channel==='start-native-screen-recording'));}finally{f.c.close();}
});
test('Sources called during capture never expand the frozen navigation title list',async()=>{
 const f=await fixture();try{const req=await planNavigation(f);const a=await f.c.dispatch(req);f.source.name='Unplanned private tab';await f.c.dispatch({command:'sources'});const c=await stopped(f);assert.equal(c.source_guard.status,'FAILED');assert(!c.allowed_titles.includes(f.source.name));assert.equal(f.calls.filter(c=>c.channel==='stop-native-screen-recording').length,1);assert.equal(c.id,a.capture_id);}finally{f.c.close();}
});
