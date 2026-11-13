'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');const {prepare}=require('../scripts/prepare.cjs');
test('Unsupported installed Recordly version is rejected before companion copy', {skip:process.platform!=='win32'},()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'recordly-prepare-unit-'));const installed=path.join(root,'installed'),home=path.join(root,'home');fs.mkdirSync(path.join(installed,'resources/app.asar.unpacked'),{recursive:true});const manifest=path.join(installed,'resources/app.asar.unpacked/package.json');const text=JSON.stringify({name:'recordly',version:'9.9.9'});fs.writeFileSync(manifest,text);
 assert.throws(()=>prepare({installDir:installed,home,pluginRoot:path.join(__dirname,'..')}),/Supported installed runtime/);assert.equal(fs.readFileSync(manifest,'utf8'),text);assert.equal(fs.readdirSync(home).length,0);
});
test('Companion writes outside D are rejected before creating paths',{skip:process.platform!=='win32'},()=>{assert.throws(()=>prepare({installDir:'C:/not-read',home:'C:/not-created-by-test',pluginRoot:__dirname}),/must be on D/);});
