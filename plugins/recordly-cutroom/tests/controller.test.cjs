'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {controller,label,inside}=require('../bridge/main.cjs');
async function fixture(backend='cuda-scale-cpu-pad'){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'recordly-unit-'));const native=path.join(root,'recordings');const projects=path.join(root,'projects');fs.mkdirSync(native);fs.mkdirSync(projects);
 const calls=[];const source={id:'window:123:0',name:'Synthetic unit window'};let present=true;
 const invoke=async(channel,...args)=>{calls.push({channel,args});
  if(channel==='get-sources')return present?[source]:[];
  if(channel==='get-recordings-directory')return {success:true,path:native};
  if(channel==='get-projects-directory')return {success:true,path:projects};
  if(channel==='stop-native-screen-recording'){const p=path.join(native,'recording-unit.mp4');fs.writeFileSync(p,'UNIT FIXTURE NOT VIDEO');return {success:true,path:p};}
  if(channel==='probe-native-video-metadata')return {success:true,metadata:{width:1280,height:720,duration:6}};
  if(channel==='save-project-file-named'){const p=path.join(projects,args[1]+'.recordly');fs.writeFileSync(p,JSON.stringify(args[0]));return {success:true,path:p};}
  if(channel==='native-static-layout-export'){const p=path.join(root,'native-export.mp4');fs.writeFileSync(p,'UNIT EXPORT NOT VIDEO');return {success:true,tempPath:p,encoderName:'static-layout-h264-nvenc',metrics:{chunks:[{backend}]}};}
  if(channel==='finalize-exported-video'){fs.copyFileSync(args[0].tempPath,args[0].outputPath,fs.constants.COPYFILE_EXCL);return {success:true,path:args[0].outputPath};}
  return {success:true};
 };
 const c=await controller({root,invoke});return {root,c,calls,source,disappear:()=>present=false};
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
