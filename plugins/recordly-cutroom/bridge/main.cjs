'use strict';
const fs=require('node:fs'),fsp=fs.promises,path=require('node:path'),crypto=require('node:crypto'),http=require('node:http');
const sha=p=>crypto.createHash('sha256').update(p).digest('hex');
const stable=v=>JSON.stringify(v,(_k,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,x[k]])):x);
function inside(file,root){const rel=path.relative(root,file);return rel!==''&&!rel.startsWith('..'+path.sep)&&rel!=='..'&&!path.isAbsolute(rel);}
function label(value){if(typeof value!=='string'||!/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$/.test(value)||/^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$/i.test(value))throw Error('Use a safe beat/name of1–80letters, digits, underscore or hyphen');return value;}
function exact(p,keys){if(!p||typeof p!=='object'||Array.isArray(p)||Object.keys(p).some(k=>!keys.includes(k)))throw Error('Unknown parameters');}
async function atomic(file,obj){const tmp=file+'.'+crypto.randomUUID()+'.tmp';await fsp.writeFile(tmp,JSON.stringify(obj,null,2));await fsp.rename(tmp,file);}
function editorDefaults(width,height){return {padding:{top:0,bottom:0,left:0,right:0,linked:true},borderRadius:0,shadowIntensity:0,backgroundBlur:0,showCursor:true,webcam:{enabled:false,sourcePath:null},cropRegion:{x:0,y:0,width:1,height:1},zoomRegions:[],trimRegions:[],clipRegions:[],speedRegions:[],annotationRegions:[],audioRegions:[],autoCaptions:[],sourceAudioTrackSettingsByClip:{},defaultSourceAudioTrackSettings:{},aspectRatio:width>=height?'16:9':'9:16',mp4FrameRate:30,exportFormat:'mp4',exportEncodingMode:'auto',exportQuality:'high'};}

async function controller({root,invoke,version='1.4.0',sourceCheckMs=300,sourceClock=Date.now}){
 root=path.resolve(root);if(process.platform==='win32'&&!/^D:\\/i.test(root))throw Error('Recordly Cutroom data must stay on D');
 await fsp.mkdir(root,{recursive:true});root=await fsp.realpath(root);
 if(process.platform==='win32'&&!/^D:\\/i.test(root))throw Error('Resolved workspace must stay on D');
 const file=path.join(root,'capture-ledger.json');let state={requests:{},capture:null};
 if(fs.existsSync(file))state=JSON.parse(await fsp.readFile(file,'utf8'));
 let chain=Promise.resolve(),timer=null,guardTimer=null,guardQueued=false;const pending=new Map(),sourceObservations=new Map();
 const ok=async(channel,...args)=>{const result=await invoke(channel,...args);if(result?.success===false)throw Error(result.message||result.error||channel+' failed');return result;};
 async function sources(){const data=await ok('get-sources',{types:['window'],thumbnailSize:{width:1,height:1},fetchWindowIcons:false});if(!Array.isArray(data))throw Error('Unexpected source list');return data.filter(s=>s.id?.startsWith('window:')).map(s=>({id:s.id,name:s.name,sourceType:'window'}));}

 function observeSources(list){
  const now=sourceClock();for(const [key,v] of sourceObservations)if(v.at<now-300000)sourceObservations.delete(key);
  for(const source of list)sourceObservations.set(JSON.stringify([source.id,source.name]),{at:now});
  while(sourceObservations.size>500)sourceObservations.delete(sourceObservations.keys().next().value);
 }
 function allowedTitles(p){
  const titles=p.allowed_titles??[p.expected_title];
  if(!Array.isArray(titles)||titles.length<1||titles.length>5||new Set(titles).size!==titles.length||titles.some(t=>typeof t!=='string'||!t||t.length>500)||!titles.includes(p.expected_title))throw Error('allowed_titles must include the exact starting title and contain 1–5 unique exact titles.');
  for(const title of titles)if(title!==p.expected_title){const seen=sourceObservations.get(JSON.stringify([p.window_id,title]));if(!seen||seen.at<sourceClock()-300000)throw Error('List every additional allowed title for this same window in fresh recordly_sources within five minutes before starting.');}
  return [...titles];
 }
 function current(id){const c=state.capture;if(!c||c.id!==id)throw Error('Capture ID does not match current retained capture');return c;}
 async function save(c,name){
  if(c.stage!=='STOPPED')throw Error('Stop capture before saving a project');
  name=label(name);const folder=path.dirname(c.source),target=path.join(folder,name+'.recordly');if(fs.existsSync(target))throw Error('Project exists; use a new name/request ID');
  const projects=await ok('get-projects-directory');if(!inside(await fsp.realpath(projects.path),root))throw Error('Recordly projects directory is outside D workspace');
  const data={version:1,projectId:crypto.randomUUID(),videoPath:c.source,editor:editorDefaults(c.metadata.width,c.metadata.height)};
  const native=await ok('save-project-file-named',data,name,null,'copy');
  const nativePath=await fsp.realpath(native.path);if(!inside(nativePath,root))throw Error('Recordly project escaped D workspace');
  if(nativePath!==target)await fsp.copyFile(nativePath,target,fs.constants.COPYFILE_EXCL);
  const loaded=await ok('open-project-file-at-path',target);c.project=target;return {project:target,project_id:JSON.parse(await fsp.readFile(target,'utf8')).projectId,reopened:loaded.success!==false};
 }
 async function checkSource(c){
  if(!c.source_guard||c.source_guard.status==='FAILED')return false;
  let reason=null;
  try{const observed=(await sources()).find(s=>s.id===c.window.id);if(!observed)reason='SELECTED_WINDOW_MISSING';else if(!(c.allowed_titles||[c.window.name]).includes(observed.name))reason='SELECTED_WINDOW_TITLE_CHANGED';}
  catch{reason='SOURCE_CHECK_UNAVAILABLE';}
  c.source_guard.checks++;c.source_guard.last_checked_at=new Date().toISOString();
  if(reason){c.source_guard.status='FAILED';c.source_guard.reason=reason;await atomic(file,state);return false;}
  return true;
 }
 function monitor(c){
  guardTimer=setInterval(()=>{
   if(guardQueued||c.stage!=='CAPTURING')return;guardQueued=true;
   chain=chain.then(async()=>{if(c.stage==='CAPTURING'&&!await checkSource(c))await stop(c);}).catch(async error=>{c.stage='STOP_FAILED';c.source_guard.error=String(error.message||error);await atomic(file,state);}).finally(()=>{guardQueued=false;});
  },sourceCheckMs);guardTimer.unref?.();
 }
 async function stop(c){
  if(c.stage==='STOPPED')return {capture_id:c.id,stage:c.stage,source:c.source,project:c.project,metadata:c.metadata,source_guard:c.source_guard||null};
  if(c.stage!=='CAPTURING')throw Error('Capture outcome is unknown; inspect native diagnostics, do not start again');
  clearInterval(guardTimer);guardTimer=null;await checkSource(c);
  c.stage='STOPPING';await atomic(file,state);clearTimeout(timer);timer=null;
  const result=await ok('stop-native-screen-recording');const source=await fsp.realpath(result.path);
  if(!inside(source,root)||path.extname(source).toLowerCase()!=='.mp4')throw Error('Native recording is outside this D workspace');
  const folder=path.join(root,'captures',c.id);await fsp.mkdir(folder,{recursive:true});
  const stem=path.parse(source).name;const entries=await fsp.readdir(path.dirname(source),{withFileTypes:true});
  for(const e of entries){if(e.isFile()&&e.name.startsWith(stem)&&/\.(mp4|json|wav|m4a)$/.test(e.name))await fsp.copyFile(path.join(path.dirname(source),e.name),path.join(folder,e.name),fs.constants.COPYFILE_EXCL);}
  c.source=path.join(folder,path.basename(source));c.native_source=source;
  await ok('set-current-recording-session',{videoPath:c.source,webcamPath:null,timeOffsetMs:0});
  const info=await ok('probe-native-video-metadata',c.source);c.metadata=info.metadata;
  if(!(c.metadata.width>0&&c.metadata.height>0&&c.metadata.duration>0))throw Error('Native capture metadata is incomplete');
  if(c.source_guard?.status==='MONITORING')c.source_guard.status='MONITORED_NO_CHANGE_OBSERVED';
  c.stage='STOPPED';c.stopped_at=new Date().toISOString();
  const project=await save(c,c.beat+'-'+c.id.slice(0,8));await atomic(file,state);
  await atomic(path.join(folder,'capture.json'),{...c,source_sha256:sha(await fsp.readFile(c.source)),recorded_by:'Recordly native Windows capture IPC',audio:'mic/system/webcam disabled',review:'NEEDS_REVIEW'});
  return {capture_id:c.id,stage:c.stage,source:c.source,...project,metadata:c.metadata,source_guard:c.source_guard||null};
 }
 async function action(command,p){
  if(command==='sources'){exact(p,[]);const list=await sources();observeSources(list);return {sources:list};}
  if(command==='status'){exact(p,[]);return {recordly_version:version,capture:state.capture,capabilities:{window_capture:true,native_export:true,animated_zoom:false,arbitrary_ipc:false},review:'NEEDS_REVIEW'};}
  if(command==='start'){
   exact(p,['window_id','expected_title','allowed_titles','beat','max_seconds']);label(p.beat);
   if(typeof p.expected_title!=='string'||!p.expected_title||p.expected_title.length>500)throw Error('Supply the exact observed window title');
   const seconds=p.max_seconds??30;if(!Number.isInteger(seconds)||seconds<5||seconds>180)throw Error('Capture limit must be5–180seconds');
   if(state.capture&&!['STOPPED'].includes(state.capture.stage))throw Error('An active/uncertain capture is retained; stop or inspect it first');
   const allowed=allowedTitles(p);
   const selected=(await sources()).find(s=>s.id===p.window_id&&s.name===p.expected_title);
   if(!selected)throw Error('Selected window disappeared or title changed; list sources again. No fallback.');
   const dir=await ok('get-recordings-directory');if(!inside(path.resolve(dir.path),root))throw Error('Recordly recording directory is outside D workspace');
   await ok('set-recording-preferences',{microphoneEnabled:false,systemAudioEnabled:false,webcamEnabled:false});
   await ok('select-source',selected);
   if(!(await sources()).some(s=>s.id===selected.id&&s.name===selected.name))throw Error('Selected window changed after selection; no capture started.');
   const c={id:crypto.randomUUID(),beat:p.beat,window:selected,allowed_titles:allowed,stage:'STARTING',started_at:new Date().toISOString(),max_seconds:seconds,source_guard:{status:'MONITORING',policy:'exact_frozen_title_list',checks:0,interval_ms:sourceCheckMs,limitation:'ID/title polling cannot prove pixel isolation; inspect decoded export.'}};state.capture=c;await atomic(file,state);
   await ok('start-native-screen-recording',selected,{capturesSystemAudio:false,capturesMicrophone:false});
   c.stage='CAPTURING';await atomic(file,state);monitor(c);
   timer=setTimeout(()=>{chain=chain.then(()=>stop(c)).catch(async()=>{c.stage='STOP_FAILED';await atomic(file,state);});},seconds*1000);timer.unref?.();
   return {capture_id:c.id,stage:c.stage,window:selected,allowed_titles:allowed,maximum_seconds:seconds,audio:'OFF',webcam:'OFF'};
  }
  if(command==='stop'){exact(p,['capture_id']);return stop(current(p.capture_id));}
  if(command==='save_project'){exact(p,['capture_id','name']);const c=current(p.capture_id);const saved=await save(c,p.name);await atomic(file,state);return saved;}
  if(command==='export'){
   exact(p,['capture_id','name','width','height','seconds']);const c=current(p.capture_id);if(c.stage!=='STOPPED')throw Error('Stop capture before export');
   if(c.source_guard?.status==='FAILED')throw Error('Capture quarantined: source changed or could not be checked. Retain project/source; record a new take.');
   const name=label(p.name);const width=p.width??1280,height=p.height??720,seconds=p.seconds??c.metadata.duration;
   if(!Number.isInteger(width)||!Number.isInteger(height)||width<360||height<360||width>3840||height>3840||width%2||height%2)throw Error('Even output dimensions360–3840required');
   if(typeof seconds!=='number'||!Number.isFinite(seconds)||seconds<=0||seconds>c.metadata.duration+.01)throw Error('Export duration outside recorded source');
   const folder=path.join(root,'exports',c.id);await fsp.mkdir(folder,{recursive:true});const output=path.join(folder,name+'.mp4');if(fs.existsSync(output))throw Error('Export exists; keep it and choose a new name');
   const fit=Math.min(width/c.metadata.width,height/c.metadata.height);const cw=Math.max(2,Math.floor(c.metadata.width*fit/2)*2),ch=Math.max(2,Math.floor(c.metadata.height*fit/2)*2);
   if(!c.project)throw Error('Save a native project before exporting');
   await ok('open-project-file-at-path',c.project);
   const native=await ok('native-static-layout-export',{inputPath:c.source,width,height,frameRate:30,bitrate:12000000,encodingMode:'auto',durationSec:seconds,contentWidth:cw,contentHeight:ch,offsetX:(width-cw)/2,offsetY:(height-ch)/2,backgroundColor:'#10151b',borderRadius:0,shadowIntensity:0,backgroundBlurPx:0,audioOptions:{audioMode:'none'}});
   if(native.encoderName!=='static-layout-h264-nvenc'||!native.metrics?.chunks?.length||!native.metrics.chunks.every(chunk=>chunk.backend==='cuda-scale-cpu-pad'))throw Error('Native compositor fell back to an unverified static backend; keep source/project and inspect the D log');
   await ok('finalize-exported-video',{tempPath:native.tempPath,fileName:name+'.mp4',outputPath:output});
   const probe=await ok('probe-native-video-metadata',output);const receipt={capture_id:c.id,source:c.source,project:c.project,output,sha256:sha(await fsp.readFile(output)),metadata:probe.metadata,encoder:native.encoderName,metrics:native.metrics,renderer:'Recordly native-static-layout-export',animated_zoom:false,source_guard:c.source_guard||{status:'LEGACY_UNVERIFIED'},review:'NEEDS_REVIEW'};
   await atomic(path.join(folder,name+'.json'),receipt);return receipt;
  }
  throw Error('Unknown command');
 }
 async function dispatch({command,params={},request_id}){
  if(['status','sources'].includes(command))return action(command,params);
  if(typeof request_id!=='string'||!/^[A-Za-z0-9_-]{8,96}$/.test(request_id))throw Error('Use a stable request ID for this logical operation');
  const fingerprint=sha(stable({command,params}));const prior=state.requests[request_id];
  if(prior){if(prior.fingerprint!==fingerprint)throw Error('Request ID conflict');if(pending.has(request_id))return pending.get(request_id);if(prior.stage==='DONE')return {...prior.result,replayed:true};throw Error('Prior operation is incomplete; inspect status instead of retrying the action');}
  state.requests[request_id]={fingerprint,stage:'PENDING'};
  const promise=chain.then(async()=>{await atomic(file,state);try{const result=await action(command,params);state.requests[request_id]={fingerprint,stage:'DONE',result};await atomic(file,state);return result;}catch(error){state.requests[request_id].stage='FAILED';state.requests[request_id].error=String(error.message||error);await atomic(file,state);throw error;}});
  pending.set(request_id,promise);chain=promise.catch(()=>{});try{return await promise;}finally{pending.delete(request_id);}
 }
 return {dispatch,close:()=>{clearTimeout(timer);clearInterval(guardTimer);}};
}

function createHttpServer({token,control,version,isReady,fingerprint}){
 const server=http.createServer(async(req,res)=>{
   const send=(code,obj)=>{res.writeHead(code,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(obj));};
   const expected=Buffer.from('Bearer '+token),actual=Buffer.from(req.headers.authorization||'');
   if(req.headers.origin||req.headers.host!=='127.0.0.1:'+server.address().port||actual.length!==expected.length||!crypto.timingSafeEqual(actual,expected)){send(403,{error:'Unauthorized local request'});return;}
   if(req.method==='GET'&&req.url==='/health'){send(200,{pid:process.pid,version:version,ready:isReady(),bridge_sha256:fingerprint});return;}
   if(req.method!=='POST'||req.url!=='/rpc'||req.headers['content-type']!=='application/json'){send(404,{error:'Not found'});return;}
   let body='',over=false;req.on('data',chunk=>{body+=chunk;if(Buffer.byteLength(body)>16384){over=true;req.destroy();}});
   req.on('end',async()=>{if(over)return;try{send(200,{result:await control.dispatch(JSON.parse(body))});}catch(e){send(400,{error:String(e.message||e)});}});
  });
 return server;
}

function install(){
 const electron=require('electron');const {app,ipcMain,BrowserWindow}=electron;
 const root=process.env.CUTROOM_RECORDLY_HOME;if(!root||!/^D:[\\/]/i.test(root))throw Error('CUTROOM_RECORDLY_HOME on D is required');
 for(const [key,sub] of [['appData','appdata'],['userData','profile'],['sessionData','session'],['temp','tmp'],['crashDumps','crashes']]){const dir=path.join(root,sub);fs.mkdirSync(dir,{recursive:true});app.setPath(key,dir);}
 app.setAppLogsPath(path.join(root,'logs'));
 const handlers=new Map(),handle=ipcMain.handle.bind(ipcMain),remove=ipcMain.removeHandler.bind(ipcMain);
 ipcMain.handle=(name,callback)=>{handlers.set(name,callback);return handle(name,callback);};
 ipcMain.removeHandler=name=>{handlers.delete(name);return remove(name);};
 app.whenReady().then(async()=>{
  const token=process.env.CUTROOM_RECORDLY_TOKEN;if(!/^[a-f0-9]{64}$/.test(token||''))return;
  const invoke=async(name,...args)=>{const fn=handlers.get(name);if(!fn)throw Error('Recordly IPC is not ready: '+name);const win=BrowserWindow.getAllWindows().find(w=>!w.isDestroyed());if(!win)throw Error('Recordly window is not ready');return fn({sender:win.webContents},...args);};
  const control=await controller({root,invoke,version:app.getVersion()});
  const server=createHttpServer({token,control,version:app.getVersion(),fingerprint:sha(fs.readFileSync(__filename)),isReady:()=>['get-sources','start-native-screen-recording','stop-native-screen-recording'].every(n=>handlers.has(n))});
  server.listen(0,'127.0.0.1',async()=>atomic(path.join(root,'bridge-ready.json'),{pid:process.pid,port:server.address().port,version:app.getVersion()}));
  app.on('will-quit',()=>{control.close();server.close();});
 }).catch(error=>console.error('Recordly Cutroom bridge startup failed:',error.message));
}
module.exports={install,controller,inside,label,createHttpServer};
