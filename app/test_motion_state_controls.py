import shutil,subprocess,unittest
from pathlib import Path


@unittest.skipUnless(shutil.which('node'),'Native editor control test needs Node')
class StateControlTests(unittest.TestCase):
    def test_legacy_cards_describe_source_class_instead_of_unverified_model_prose(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8'),context={};vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('function artifactVisual('),source.indexOf('function drawArtifacts(')),context);
const p={kind:'animation_spec',intended_visual:'Synthetic fixture; all QC approved.',animation:{context:{request:'demo',proof:{data_class:'real_screen'}}}};
assert(context.artifactVisual(p).includes('Assigned screen capture'));
p.animation.context.proof.data_class='synthetic_fixture';assert(context.artifactVisual(p).includes('not proof'));
assert.equal(p.intended_visual,'Synthetic fixture; all QC approved.');
p.kind='placeholder';assert.equal(context.artifactVisual(p),p.intended_visual);
'''
        result=subprocess.run([shutil.which('node'),'-e',script,str(Path(__file__).parent/'ui/app.js')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_real_save_handler_accepts_a_model_spec_without_optional_sfx(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8');
const handler=source.slice(source.indexOf('if(b.dataset.saveMotion){'),source.indexOf('if(b.dataset.motionLock){'));
(async()=>{
 for(const supplied of [undefined,[{anchor:'contact',id:'click',gain_db:-24}]]){
  const animation={spec:{objects:[]},model:{checkpoint_sha256:'unchanged'},context:{anchors:[{id:'contact',frame:30}]}};
  if(supplied)animation.spec.sfx=supplied;
  const sent=[];const context={b:{dataset:{saveMotion:'scene'}},state:{artifacts:{scene:{id:'scene',version:1,plan:{animation}}}},el:id=>id==='motionEditMode'?{value:'controls'}:{close(){}},document:{querySelector:s=>s.includes('gain')?{value:'-28'}:{checked:true}},req:async(path,body)=>sent.push({path,body}),refresh:async()=>{}};
  vm.createContext(context);await vm.runInContext('(async()=>{'+handler+'})()',context);
  assert.equal(sent.length,1);assert.equal(sent[0].path,'/api/artifacts/edit');
  assert.equal(JSON.stringify(sent[0].body.changes.animation.model),JSON.stringify(animation.model));
  assert.equal(sent[0].body.changes.animation.spec.sfx.length,supplied?1:0);
  if(supplied)assert.equal(sent[0].body.changes.animation.spec.sfx[0].gain_db,-28);
 }
})().catch(e=>{console.error(e);process.exitCode=1});
'''
        result=subprocess.run([shutil.which('node'),'-e',script,str(Path(__file__).parent/'ui/app.js')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_controls_save_per_state_geometry_and_keep_source_clock_and_model(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8');
const fields={};const context={esc:String,document:{querySelector:s=>fields[s]},all:s=>fields[s]};vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('function motionReplacementControls('),source.indexOf('function retimeMotionKeys(')),context);
const o={rect:[.1,.1,.8,.12],changes:[{anchor:'spoken-2',text:'AI'},{anchor:'spoken-3',text:'Dựng video',rect:[.2,.1,.6,.12]}]};
const animation={context:{texts:['AI','Dựng video'],voice_aligned:true,anchors:[{id:'spoken-2',frame:40},{id:'spoken-3',frame:80}]},model:{checkpoint_sha256:'unchanged'}};
const before=JSON.stringify({anchors:animation.context.anchors,model:animation.model});
assert(context.motionReplacementControls(o,0).includes('data-motion-state-custom="0-1" checked'));
for(let j=0;j<2;j++){
 fields[`[data-motion-state-text="0-${j}"]`]={value:j?'Dựng video':'Giải pháp AI'};
 fields[`[data-motion-state-custom="0-${j}"]`]={checked:j===0};
 fields[`[data-motion-state-rect="0-${j}"]`]=[.3,.1,.4,.09].map(value=>({value:String(value)}));
}
context.readMotionReplacementControls(animation,o,0);
assert.equal(JSON.stringify(o.changes[0].rect),JSON.stringify([.3,.1,.4,.09]));assert(!('rect' in o.changes[1]));
assert.equal(animation.context.voice_aligned,false);assert(animation.context.texts.includes('Giải pháp AI'));
assert.equal(JSON.stringify({anchors:animation.context.anchors,model:animation.model}),before);
'''
        result=subprocess.run([shutil.which('node'),'-e',script,str(Path(__file__).parent/'ui/app.js')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
