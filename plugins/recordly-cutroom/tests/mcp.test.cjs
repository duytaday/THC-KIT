'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),{spawnSync}=require('node:child_process'),path=require('node:path');
test('Real stdio process initializes, lists seven tools and rejects unsupported arguments',()=>{
 const messages=[{jsonrpc:'2.0',id:1,method:'initialize',params:{protocolVersion:'2025-06-18'}},{jsonrpc:'2.0',method:'notifications/initialized'},{jsonrpc:'2.0',id:2,method:'tools/list'},{jsonrpc:'2.0',id:3,method:'tools/call',params:{name:'recordly_status',arguments:{unexpected:true}}}];
 const r=spawnSync(process.execPath,[path.join(__dirname,'../server/index.cjs')],{input:messages.map(x=>JSON.stringify(x)).join('\n')+'\n',encoding:'utf8',env:{...process.env,CUTROOM_RECORDLY_HOME:path.join(process.env.TEMP,'nonexistent-mcp-fixture-home')}});
 assert.equal(r.status,0,r.stderr);const output=r.stdout.trim().split('\n').map(JSON.parse);
 assert.equal(output.length,3);assert.equal(output.find(x=>x.id===1).result.serverInfo.name,'recordly-cutroom');
 const tools=output.find(x=>x.id===2).result.tools;assert.equal(tools.length,7);assert(tools.every(t=>t.inputSchema.additionalProperties===false));assert.equal(output.find(x=>x.id===3).result.isError,true);
});
