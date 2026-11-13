'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const VERSION='1.4.0';
function prepare({installDir,home,pluginRoot}){
 if(process.platform!=='win32')throw Error('This adapter currently supports Windows only');
 installDir=path.resolve(installDir);home=path.resolve(home);pluginRoot=path.resolve(pluginRoot);
 if(!/^D:\\/i.test(home))throw Error('Companion/data root must be on D');
 fs.mkdirSync(home,{recursive:true});home=fs.realpathSync(home);if(!/^D:\\/i.test(home))throw Error('Resolved data root must be on D');
 const pkg=path.join(installDir,'resources/app.asar.unpacked/package.json'),main=path.join(installDir,'resources/app.asar.unpacked/dist-electron/main.cjs');
 const manifest=JSON.parse(fs.readFileSync(pkg));if(manifest.name!=='recordly'||manifest.version!==VERSION)throw Error('Supported installed runtime is Recordly1.4.0; no update or original-app patch applied');
 const archive=fs.readFileSync(path.join(installDir,'resources/app.asar'));const length=archive.readUInt32LE(12);if(length>archive.length-16)throw Error('Invalid app archive');
 const header=JSON.parse(archive.toString('utf8',16,16+length));if(header.files?.['dist-electron']?.files?.['main.cjs']?.unpacked!==true)throw Error('This runtime requires an unpacked main entry; prepare a supported build explicitly');
 const code=fs.readFileSync(main,'utf8');if(!code.startsWith('"use strict";'))throw Error('Unknown main entry; original runtime preserved');
 for(const command of ['get-sources','start-native-screen-recording','stop-native-screen-recording','native-static-layout-export','save-project-file-named'])if(!code.includes('handle("'+command+'"'))throw Error('Required IPC missing: '+command);
 if(!code.includes('await je.autoUpdater.checkForUpdates()'))throw Error('Unknown updater entry; do not enable a self-updating companion');
 if(hash(main)!=='2ef26cf37acc1b047eebbabecd5e138c78a4bd55f8c795138ec7390683ed0891')throw Error('Installed build differs from the tested adapter; original preserved');
 if(!code.includes('function Xf(e){')||!code.includes('let ie=Q,pe="cuda-overlay",ve;'))throw Error('Unknown native layout entry; preserve runtime');
 const pinnedCode=code.replaceAll('await je.autoUpdater.checkForUpdates()','await Promise.resolve(null)').replace('function Xf(e){','function Xf(e){return Kf(e)}function cutroomOriginalCudaOverlay(e){').replace('let ie=Q,pe="cuda-overlay",ve;','let ie=Q,pe="cuda-scale-cpu-pad",ve;').replace('pad=w=${e.width}:h=${e.height}:x=${e.offsetX}:y=${e.offsetY}:color=${t}`','pad=w=${e.width}:h=${e.height}:x=${e.offsetX}:y=${e.offsetY}:color=${t},setsar=1`');
 const patched='"use strict";\nrequire(require("node:path").join(process.resourcesPath,"cutroom-bridge/main.cjs")).install();\n'+pinnedCode.slice('"use strict";'.length);
 const bridge=path.join(pluginRoot,'bridge/main.cjs'),identity=crypto.createHash('sha256').update(hash(main)+hash(bridge)+hash(__filename)).digest('hex').slice(0,16);
 const runtime=path.join(home,'runtime-'+identity),receipt=path.join(runtime,'cutroom-companion.json');
 if(fs.existsSync(receipt)){
  const r=JSON.parse(fs.readFileSync(receipt));if(hash(path.join(runtime,'resources/cutroom-bridge/main.cjs'))!==r.bridge_sha256||hash(path.join(runtime,'resources/app.asar.unpacked/dist-electron/main.cjs'))!==r.patched_main_sha256)throw Error('Existing companion changed; preserve it for inspection');return r;
 }
 if(fs.existsSync(runtime))throw Error('Incomplete companion copy exists; inspect it instead of overwriting');
 fs.mkdirSync(runtime);
 fs.cpSync(installDir,runtime,{recursive:true,filter:source=>{
  const item=fs.lstatSync(source);if(item.isSymbolicLink())throw Error('Runtime symlinks require explicit review');
  const name=path.basename(source);return !name.startsWith('Uninstall ')&&!name.endsWith('.log')&&!name.includes('before-bounded-hud');
 }});
 const destination=path.join(runtime,'resources/cutroom-bridge');fs.mkdirSync(destination,{recursive:true});fs.copyFileSync(bridge,path.join(destination,'main.cjs'));
 const output=path.join(runtime,'resources/app.asar.unpacked/dist-electron/main.cjs');fs.writeFileSync(output,patched);
 const result={recordly_version:VERSION,executable:path.join(runtime,'Recordly.exe'),original_install:installDir,original_main_sha256:hash(main),patched_main_sha256:hash(output),bridge_sha256:hash(bridge),runtime,source_preserved:true,export_workaround:'cuda-scale-cpu-pad (bypass overlay_cuda color defect)',updater_disabled:true};
 fs.writeFileSync(receipt,JSON.stringify(result,null,2));return result;
}
module.exports={prepare};
if(require.main===module){const [installDir,home]=process.argv.slice(2);console.log(JSON.stringify(prepare({installDir,home,pluginRoot:path.resolve(__dirname,'..')})));}
