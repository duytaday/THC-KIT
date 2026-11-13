'use strict';
const readline=require('node:readline');const {Client}=require('./client.cjs');
const client=new Client();
const str={type:'string',minLength:1},request={type:'string',pattern:'^[A-Za-z0-9_-]{8,96}$'},id={type:'string',minLength:1};
const definitions=[
 ['recordly_status','Inspect connected Recordly bridge and retained capture. Does not launch or record.',{},[],true],
 ['recordly_open','Prepare/open a separate local Recordly1.4.0 companion on D. Original installed app is preserved. No recording starts.',{},[],false],
 ['recordly_sources','List current capturable app windows. Returns ID/title only; does not start recording. Select exact ID and title for a later start.',{},[],true],
 ['recordly_start','Record exactly the selected window in Recordly. Webcam, microphone and system audio are OFF. No fallback to another source. Source ID/title must come from fresh recordly_sources.',{window_id:id,expected_title:str,beat:{type:'string',pattern:'^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$'},max_seconds:{type:'integer',minimum:5,maximum:180,default:30},request_id:request},['window_id','expected_title','beat','request_id'],false],
 ['recordly_stop','Stop the identified capture, retain source media and save/reopen a native .recordly project on D. Retry same logical request ID, not a new recording.',{capture_id:id,request_id:request},['capture_id','request_id'],false],
 ['recordly_save_project','Save another editable native project version for the retained capture; never overwrite an existing project.',{capture_id:id,name:str,request_id:request},['capture_id','name','request_id'],false],
 ['recordly_export','Export the retained recording through Recordly native static-layout export. Audio off,30fps. Keep previous exports. Does not claim animated zoom or editorial approval.',{capture_id:id,name:str,width:{type:'integer',minimum:360,maximum:3840,default:1280},height:{type:'integer',minimum:360,maximum:3840,default:720},seconds:{type:'number',exclusiveMinimum:0},request_id:request},['capture_id','name','request_id'],false]
];
const tools=definitions.map(([name,description,properties,required,readOnlyHint])=>({name,description,inputSchema:{type:'object',properties,required,additionalProperties:false},annotations:{readOnlyHint,destructiveHint:false,idempotentHint:true,openWorldHint:false}}));
async function call(name,args){
 const definition=tools.find(t=>t.name===name);if(!definition)throw Error('Unknown tool');
 if(!args||typeof args!=='object'||Array.isArray(args)||Object.keys(args).some(k=>!(k in definition.inputSchema.properties))||definition.inputSchema.required.some(k=>args[k]===undefined))throw Error('Arguments do not match this tool schema');
 if(name==='recordly_open')return client.open();
 if(name==='recordly_status'){const health=await client.health();if(!health?.ready)return {connected:false,recording_started:false,next_action:'Call recordly_open; no capture source selected automatically'};}
 const {request_id,...params}=args;return client.call(name.replace('recordly_',''),params,request_id);
}
async function handle(message){
 if(message?.jsonrpc!=='2.0'||typeof message.method!=='string')return {jsonrpc:'2.0',id:message?.id??null,error:{code:-32600,message:'Invalid JSON-RPC request'}};
 if(message.id===undefined)return null;
 if(message.method==='initialize')return {jsonrpc:'2.0',id:message.id,result:{protocolVersion:'2025-06-18',capabilities:{tools:{listChanged:false}},serverInfo:{name:'recordly-cutroom',version:'0.1.1'},instructions:'Local Recordly companion. Explicitly select exact window ID/title. All captures/projects/exports stay on D; no editorial READY from this plugin.'}};
 if(message.method==='ping')return {jsonrpc:'2.0',id:message.id,result:{}};
 if(message.method==='tools/list')return {jsonrpc:'2.0',id:message.id,result:{tools}};
 if(message.method==='tools/call'){
  try{return {jsonrpc:'2.0',id:message.id,result:{content:[{type:'text',text:JSON.stringify(await call(message.params?.name,message.params?.arguments||{}))}],isError:false}};}
  catch(e){return {jsonrpc:'2.0',id:message.id,result:{content:[{type:'text',text:JSON.stringify({error:String(e.message||e),review:'NEEDS_REVIEW'})}],isError:true}};}
 }
 return {jsonrpc:'2.0',id:message.id,error:{code:-32601,message:'Method not found'}};
}
if(require.main===module){
 readline.createInterface({input:process.stdin,crlfDelay:Infinity}).on('line',async line=>{
  let response;try{if(Buffer.byteLength(line)>131072)throw Error('Request too large');response=await handle(JSON.parse(line));}catch{response={jsonrpc:'2.0',id:null,error:{code:-32700,message:'Invalid bounded JSON message'}};}
  if(response)process.stdout.write(JSON.stringify(response)+'\n');
 });
}
module.exports={tools,handle,call};
