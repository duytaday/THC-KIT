"""Create a private Kaggle spec-training package; no raw media or auto-upload."""
import argparse,json,re,shutil
from pathlib import Path
from engine import media
import motion_learning


def prepare(dataset,out,owner,steps=128,prompt_version=None):
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',owner):raise ValueError('Use a Kaggle owner name')
    if not 1<=steps<=512:raise ValueError('Use 1–512 optimizer steps')
    prompt_version=motion_learning.PROMPT_VERSION if prompt_version is None else prompt_version
    contract=motion_learning.output_contract(prompt_version)
    manifest,_,_=motion_learning.check_dataset(dataset)
    out=Path(out);out.mkdir(parents=True,exist_ok=False);root=Path(__file__).parent
    upload=out/'dataset';upload.mkdir();kernel=out/'kernel';kernel.mkdir()
    for name in ('manifest.json','train.jsonl','validation.jsonl','test.jsonl','retrieval-train-only.json'):
        shutil.copy2(Path(dataset)/name,upload/name)
    for name in ('motion_specs.py','motion_learning.py','motion_decisions.py','train_motion.py'):shutil.copy2(root/name,upload/name)
    # The CLI skips directories; Kaggle also auto-extracts ZIPs on ingestion.
    # Training uses only `from engine import media`, so use two flat modules.
    (upload/'engine.py').write_text('import cutroom_media as media\n',encoding='utf-8')
    shutil.copy2(root/'engine/media.py',upload/'cutroom_media.py')
    tag=manifest['dataset_fingerprint'][:12]+('-p'+str(prompt_version) if prompt_version>=10 else '')
    slug='talking-head-animation-spec-'+tag
    media.write_json(upload/'dataset-metadata.json',dict(title='Talking Head Animation Spec '+tag,id=owner+'/'+slug,licenses=[dict(name='other')]))
    media.write_json(kernel/'kernel-metadata.json',dict(id=owner+'/talking-head-spec-training-'+tag,title='Talking Head Spec Training '+tag,code_file='train.py',language='python',kernel_type='script',is_private=True,enable_gpu=True,machine_shape='NvidiaTeslaT4',enable_internet=True,dataset_sources=[owner+'/'+slug],competition_sources=[],kernel_sources=[]))
    (kernel/'train.py').write_text("""from pathlib import Path
import json,subprocess,sys
roots=[p.parent for p in Path('/kaggle/input').rglob('manifest.json') if json.loads(p.read_text()).get('task')=='script_animation_spec_v1']
assert len(roots)==1,'Attach exactly one animation spec dataset'
root=roots[0];sys.path.insert(0,str(root))
assert (root/'engine.py').is_file() and (root/'cutroom_media.py').is_file(),'Missing flat training support'
from motion_learning import check_dataset
check_dataset(root)
subprocess.run([sys.executable,'-m','pip','install','transformers==4.51.3','peft==0.15.2','accelerate==1.6.0','safetensors>=0.4.3,<0.9'],check=True)
subprocess.run([sys.executable,str(root/'train_motion.py'),'--dataset',str(root),'--steps',STEPS,'--prompt-version',PROMPT,'--out','/kaggle/working/talking-head-motion-spec'],check=True)
""".replace('STEPS',repr(str(steps))).replace('PROMPT',repr(str(prompt_version))),encoding='utf-8')
    media.write_json(out/'preparation.json',dict(dataset_fingerprint=manifest['dataset_fingerprint'],prompt_version=prompt_version,output_contract=contract,private=True,uploaded=False,optimizer_steps_requested=steps,raw_media_included=False,human_confirmed_labels=manifest['human_confirmed_labels'],production_eligible=False,files={str(p.relative_to(out)):media.sha(p) for p in out.rglob('*') if p.is_file()}))
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('dataset',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--owner',required=True);p.add_argument('--steps',type=int,default=128);p.add_argument('--prompt-version',type=int,default=None);a=p.parse_args()
    print(prepare(a.dataset,a.out,a.owner,a.steps,a.prompt_version))
