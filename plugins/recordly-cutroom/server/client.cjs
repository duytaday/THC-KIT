'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),http=require('node:http'),{spawn,spawnSync}=require('node:child_process');
const {prepare}=require('../scripts/prepare.cjs');
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
class Client{
 constructor({home,installDir,pluginRoot}={}){
  this.home=path.resolve(home||process.env.CUTROOM_RECORDLY_HOME||'D:/.codex/workspaces/talking-head-support/recordly-plugin');
  if(!/^D:[\\/]/i.test(this.home))throw Error('Recordly Cutroom writes only to a D workspace');
  this.installDir=installDir||path.join(process.env.LOCALAPPDATA||'','Programs/Recordly');this.pluginRoot=pluginRoot||path.resolve(__dirname,'..');this.opening=null;
 }
 crypt(mode,value){
  const method=mode==='protect'?'Protect':'Unprotect';
  const script='Add-Type -AssemblyName System.Security; $b=[Convert]::FromBase64String([Console]::In.ReadToEnd()); $o=[System.Security.Cryptography.ProtectedData]::'+method+'($b,$null,[System.Security.Cryptography.DataProtectionScope]::CurrentUser); [Console]::Out.Write([Convert]::ToBase64String($o))';
  const r=spawnSync('powershell.exe',['-NoLogo','-NoProfile','-NonInteractive','-Command',script],{input:Buffer.from(value).toString('base64'),encoding:'utf8',windowsHide:true,env:{...process.env,TEMP:path.join(this.home,'tmp'),TMP:path.join(this.home,'tmp')}});
  if(r.status!==0)throw Error('Windows user-bound secret storage unavailable');return Buffer.from(r.stdout.trim(),'base64');
 }
 auth(){return this.crypt('unprotect',fs.readFileSync(path.join(this.home,'bridge-auth.dpapi'))).toString('utf8');}
 request(route,body,timeout=300000){
  const ready=JSON.parse(fs.readFileSync(path.join(this.home,'bridge-ready.json')));if(!Number.isInteger(ready.port)||ready.port<1||ready.port>65535)throw Error('Invalid bridge endpoint');
  const token=this.auth();if(!/^[a-f0-9]{64}$/.test(token))throw Error('Invalid stored bridge credential');
  const data=body===undefined?null:Buffer.from(JSON.stringify(body));
  return new Promise((resolve,reject)=>{
   const req=http.request({host:'127.0.0.1',port:ready.port,path:route,method:data?'POST':'GET',headers:{Authorization:'Bearer '+token,...(data?{'Content-Type':'application/json','Content-Length':data.length}:{})},timeout},res=>{
    let text='';res.on('data',c=>{text+=c;if(text.length>2*1024*1024)req.destroy(Error('Bridge response too large'));});res.on('end',()=>{try{const obj=JSON.parse(text);if(res.statusCode!==200)reject(Error(obj.error||'Bridge call failed'));else resolve(obj.result??obj);}catch{reject(Error('Invalid bridge response'));}});
   });req.on('error',reject);req.on('timeout',()=>req.destroy(Error('Bridge operation timed out; inspect the same request ID/status before retrying')));if(data)req.write(data);req.end();
  });
 }
 async health(){try{const status=await this.request('/health',undefined,1500);const expected=crypto.createHash('sha256').update(fs.readFileSync(path.join(this.pluginRoot,'bridge/main.cjs'))).digest('hex');return {...status,compatible:status.bridge_sha256===expected};}catch{return null;}}
 async open(){
  if(this.opening)return this.opening;
  this.opening=(async()=>{
   const connected=await this.health();if(connected?.ready){if(!connected.compatible)throw Error('Running bridge code differs from this plugin. Stop/save and close that companion before upgrading; no duplicate launch.');return {connected:true,...connected};}
   const readyFile=path.join(this.home,'bridge-ready.json');if(fs.existsSync(readyFile)){const prior=JSON.parse(fs.readFileSync(readyFile));let alive=false;if(Number.isInteger(prior.pid)&&prior.pid>0){try{process.kill(prior.pid,0);alive=true;}catch{}}if(alive)throw Error('Prior companion PID is still present but cannot be authenticated. Inspect it; no duplicate launch.');}
   fs.mkdirSync(this.home,{recursive:true});fs.mkdirSync(path.join(this.home,'tmp'),{recursive:true});
   const lock=path.join(this.home,'open.lock');let fd;
   try{fd=fs.openSync(lock,'wx');}catch{throw Error('A prior bridge startup is incomplete/unknown. Inspect existing app/session; no duplicate launch.');}
   fs.writeSync(fd,JSON.stringify({pid:process.pid,started_at:new Date().toISOString()}));fs.closeSync(fd);
   const prepared=prepare({installDir:this.installDir,home:this.home,pluginRoot:this.pluginRoot});
   const token=crypto.randomBytes(32).toString('hex');fs.writeFileSync(path.join(this.home,'bridge-auth.dpapi'),this.crypt('protect',Buffer.from(token)));
   const log=fs.openSync(path.join(this.home,'recordly-companion.log'),'a');
   const child=spawn(prepared.executable,[],{cwd:prepared.runtime,windowsHide:true,detached:false,stdio:['ignore',log,log],env:{...process.env,CUTROOM_RECORDLY_HOME:this.home,CUTROOM_RECORDLY_TOKEN:token,TEMP:path.join(this.home,'tmp'),TMP:path.join(this.home,'tmp')}});fs.closeSync(log);
   child.on('error',()=>{});this.child=child;
   const until=Date.now()+45000;
   while(Date.now()<until){const status=await this.health();if(status?.ready&&status.compatible){fs.unlinkSync(lock);return {connected:true,...status};}if(child.exitCode!==null)throw Error('Companion exited; inspect its D log. Original Recordly is unchanged.');await wait(500);}
   throw Error('Companion startup outcome unknown; inspect D log and existing process. Do not launch again blindly.');
  })();try{return await this.opening;}finally{this.opening=null;}
 }
 async call(command,params={},request_id){const h=await this.health();if(!h?.ready)throw Error('Recordly bridge is not connected; call recordly_open first');if(!h.compatible)throw Error('Running bridge code differs from this plugin; inspect before upgrading');return this.request('/rpc',{command,params,request_id});}
}
module.exports={Client};
