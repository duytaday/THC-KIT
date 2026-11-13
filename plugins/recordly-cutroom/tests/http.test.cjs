'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),http=require('node:http');
const {createHttpServer}=require('../bridge/main.cjs');
test('Loopback bridge requires token, exact Host and no browser Origin; commands remain bounded',async()=>{
 let calls=0;const token='a'.repeat(64);const server=createHttpServer({token,version:'unit',isReady:()=>true,control:{dispatch:async()=>{calls++;return {unit:true};}}});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const port=server.address().port;
 const send=(options={})=>new Promise((resolve,reject)=>{const data=options.body;const q=http.request({host:'127.0.0.1',port,path:options.path||'/health',method:data?'POST':'GET',headers:{Host:'127.0.0.1:'+port,Authorization:'Bearer '+token,...(data?{'Content-Type':'application/json'}:{}),...options.headers}},r=>{let b='';r.on('data',x=>b+=x);r.on('end',()=>resolve({status:r.statusCode,body:JSON.parse(b)}));});q.on('error',reject);if(data)q.write(data);q.end();});
 try{
  assert.equal((await send()).body.ready,true);
  assert.equal((await send({headers:{Authorization:'Bearer wrong'}})).status,403);
  assert.equal((await send({headers:{Origin:'http://evil.example'}})).status,403);
  assert.equal((await send({headers:{Host:'evil.example'}})).status,403);
  assert.equal((await send({path:'/rpc',body:'not json'})).status,400);
  assert.equal((await send({path:'/eval',body:'{}'})).status,404);
  assert.equal(calls,0);
  assert.deepEqual((await send({path:'/rpc',body:'{"command":"status"}'})).body.result,{unit:true});assert.equal(calls,1);
 }finally{await new Promise(r=>server.close(r));}
});
