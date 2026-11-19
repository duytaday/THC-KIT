"""Local A/B registry. Text decision LoRA is never video-generation training."""
import copy,json,os,sqlite3,subprocess,time,uuid,shutil
from pathlib import Path
from engine import media
from revisions import digest
import asset_learning,asset_planner

STATES=('prepared','training','candidate','development-evaluated','human-approved','active')
BASE='Qwen/Qwen2.5-1.5B-Instruct';BASE_REVISION='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
DEFAULT_BASE=Path('D:/.codex/workspaces/talking-head-support/models/Qwen2.5-1.5B-Instruct/models--Qwen--Qwen2.5-1.5B-Instruct/snapshots')/BASE_REVISION

def registry(root):
    path=Path(root)/'models/registry.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(version=1,revision=0,runs={},active={'A':'B1','B':'B1','C':None},active_scopes={},history=[],video_generation=dict(status='NOT_IMPLEMENTED_NO_VALIDATED_LOCAL_RECIPE',reason='A/B are text decision/spec LoRAs. No claim of video-generation training on this hardware.'))

class Lease:
    def __init__(self,path):self.path=Path(path);self.token=uuid.uuid4().hex
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path.with_suffix('.sqlite3'),timeout=30)
        self.db.execute('CREATE TABLE IF NOT EXISTS writer(id INTEGER PRIMARY KEY)');self.db.commit()
        self.db.execute('BEGIN IMMEDIATE')
        return self
    def __exit__(self,*args):
        try:self.db.rollback() if args and args[0] else self.db.commit()
        finally:self.db.close()

def update(root,run_id,patch):
    root=Path(root)
    with Lease(root/'models/registry.lock'):
        r=registry(root);entry=r['runs'][run_id];entry.update(copy.deepcopy(patch));r['revision']+=1
        asset_learning.write(root/'models/registry.json',r)
        return copy.deepcopy(entry)

def worker_code(folder,config):
    source=folder/'code' if (folder/'code').exists() else Path(__file__).parent
    for name,sha in config['code_files'].items():
        if Path(name).name!=name or media.sha(source/name)!=sha:raise ValueError('Pinned training/inference code changed: '+name)
    return source/'asset_train_worker.py'

def prepare(root,dataset,*,creator='local-experimental',style='locked-native',steps=4,max_tokens=1536,cycle='local-development-v1'):
    root=Path(root);manifest,rows=asset_learning.load_package(dataset)
    if manifest['track'] not in ('A','B'):raise ValueError('Local trainer supports editing decisions A or MotionSpec B only')
    if not 1<=steps<=64 or not 256<=max_tokens<=2048:raise ValueError('Use1–64 steps and256–2048 tokens for this local experiment')
    if sum(r.get('cycle')==cycle for r in registry(root)['runs'].values())>=3:raise ValueError('Three candidate recipes already prepared for this cycle; preserve B1 and review the cycle before starting another')
    key=uuid.uuid4().hex;folder=root/'models/local'/key;folder.mkdir(parents=True,exist_ok=False)
    config=dict(format='thc-local-lora-v1',track=manifest['track'],creator=creator,style=style,dataset=str(Path(dataset).resolve()),dataset_hash=manifest['dataset_hash'],base_model=BASE,base_revision=BASE_REVISION,base_path=str(DEFAULT_BASE),tokenizer_revision=BASE_REVISION,recipe=dict(rank=4,alpha=8,dropout=.03,target_modules=['q_proj','v_proj'],optimizer='AdamW',learning_rate=1e-4,max_tokens=max_tokens,steps=steps,micro_batch_size=1,gradient_checkpointing=True,seed=3407),training_device='cuda:0',prompt_version=10 if manifest['track']=='B' else 'typed-edit-plan-v1',output_kind='text_decision_spec_not_video_generation',full_video_quality='NOT_VERIFIED',human_approval=False)
    names=['asset_train_worker.py','asset_models.py','asset_learning.py','asset_planner.py']
    if config['track']=='B':names+=['motion_learning.py','motion_decisions.py','motion_specs.py']
    config['code_files']={name:media.sha(Path(__file__).with_name(name)) for name in names}
    config['code_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[1],text=True).strip()
    asset_learning.write(folder/'configuration.json',config)
    (folder/'code').mkdir()
    for name in config['code_files']:shutil.copyfile(Path(__file__).with_name(name),folder/'code'/name)
    entry=dict(id=key,track=config['track'],creator=creator,style=style,cycle=cycle,state='prepared',folder=str(folder),configuration_sha256=media.sha(folder/'configuration.json'),dataset_hash=config['dataset_hash'],created=time.time(),production_eligible=False,human_approved=False)
    with Lease(root/'models/registry.lock'):
        r=registry(root)
        if sum(e.get('cycle')==cycle for e in r['runs'].values())>=3:raise ValueError('Candidate cycle reached its bound while preparing; keep existing runs')
        r['runs'][key]=entry;r['revision']+=1;asset_learning.write(root/'models/registry.json',r)
    return entry

def train(root,run_id,python,*,resume=False,stop_after=None):
    entry=registry(root)['runs'][run_id]
    with Lease(Path(entry['folder'])/'execution.lock'):
        return _train(root,run_id,python,resume=resume,stop_after=stop_after)

def _train(root,run_id,python,*,resume=False,stop_after=None):
    r=registry(root);entry=r['runs'][run_id];folder=Path(entry['folder']);config=json.loads((folder/'configuration.json').read_text(encoding='utf-8'))
    if media.sha(folder/'configuration.json')!=entry['configuration_sha256']:raise ValueError('Frozen local training configuration changed')
    worker=worker_code(folder,config)
    if entry['state'] in ('candidate','development-evaluated','human-approved','active'):
        if resume:return dict(**entry,replayed=True)
        raise ValueError('Keep completed checkpoints; prepare a new recipe instead of retraining in place')
    if entry['state']=='training' and not resume:raise ValueError('Use explicit resume for the same interrupted candidate')
    update(root,run_id,dict(state='training',started=time.time()))
    request=dict(action='train',folder=str(folder),resume=resume,stop_after=stop_after)
    proc=subprocess.run([str(python),str(worker)],input=json.dumps(request).encode(),capture_output=True,timeout=1800,env={**os.environ,'PYTHONPATH':str(Path(__file__).parent)},**media.launch_options())
    (folder/('resume.stderr.log' if resume else 'train.stderr.log')).write_bytes(proc.stderr)
    try:result=json.loads(proc.stdout)
    except ValueError:result=dict(status='FAILED',error='Worker did not return bounded JSON; inspect local stderr')
    asset_learning.write(folder/('resume-result.json' if resume else 'train-result.json'),result)
    if proc.returncode:
        update(root,run_id,dict(state='training',last_error=result.get('error','Local resource/runtime failure'),resource_limited=True));return result
    complete=result.get('training_completed') is True
    update(root,run_id,dict(state='candidate' if complete else 'training',actual_steps=result.get('actual_steps',0),checkpoint_sha256=result.get('adapter_sha256'),metrics=result,production_eligible=False))
    return result

def infer(root,run_id,contexts,python,mode='B2'):
    if mode!='B2':raise ValueError('B0/B1 run without this candidate adapter; use evaluate for matched comparison')
    entry=registry(root)['runs'][run_id]
    folder=Path(entry['folder']);config=json.loads((folder/'configuration.json').read_text(encoding='utf-8'))
    if media.sha(folder/'configuration.json')!=entry['configuration_sha256']:raise ValueError('Frozen inference configuration changed')
    worker=worker_code(folder,config)
    if entry['state'] not in STATES[2:]:raise ValueError('Load a completed candidate')
    request=dict(action='infer',folder=entry['folder'],contexts=contexts,mode=mode)
    trace=folder/'inference'/uuid.uuid4().hex;trace.mkdir(parents=True,exist_ok=False);asset_learning.write(trace/'worker-request.json',request)
    proc=subprocess.run([str(python),str(worker)],input=json.dumps(request,ensure_ascii=False).encode(),capture_output=True,timeout=600,env={**os.environ,'PYTHONPATH':str(Path(__file__).parent)},**media.launch_options())
    (trace/'stdout.json').write_bytes(proc.stdout);(trace/'stderr.log').write_bytes(proc.stderr)
    result=json.loads(proc.stdout)
    if proc.returncode or not result.get('adapter_loaded') or result.get('adapter_sha256')!=entry['checkpoint_sha256']:raise ValueError('Candidate inference failed or loaded the wrong adapter: '+str(result.get('error','')))
    result['inference_trace']=str(trace);return result

def promote(root,run_id,evidence,base_revision):
    """Explicit human evidence gate; metrics/loss/autopick alone cannot activate."""
    root=Path(root)
    with Lease(root/'models/registry.lock'):
        r=registry(root)
        if type(base_revision) is not int or r['revision']!=base_revision:raise ValueError('Registry revision conflict; do not overwrite another activation')
        entry=r['runs'][run_id]
        if str(entry.get('release_status','')).startswith('BLOCKED_BY_'):raise ValueError('Candidate has an unresolved development regression; keep B1 active')
        if entry.get('track')!='A':raise ValueError('Scoped native MotionSpec activation has not been validated; keep B1 and use the existing motion candidate review workflow')
        report=Path(entry.get('evaluation_path',''))
        if not report.is_file() or media.sha(report)!=entry.get('evaluation_sha256'):raise ValueError('Exact development evidence is missing or changed')
        measured=json.loads(report.read_text(encoding='utf-8'));arm=measured.get('arms',{}).get('B2',{})
        if arm.get('cases',0)<=0 or arm.get('valid')!=arm.get('cases'):raise ValueError('Candidate did not pass every required development case')
        required=('blind_full_episode','matched_sources_renderer_loudness','qc_all_pass','B2_better_than_B1','can_hear','can_see')
        if entry['state']!='development-evaluated' or not all(evidence.get(k) is True for k in required) or evidence.get('reviewer_kind')!='human' or not str(evidence.get('reviewer','')).strip():raise ValueError('Full independent human comparison evidence is missing; keep B1 active')
        import math
        acceptance=evidence.get('first_pass_acceptance');repair=evidence.get('repair_minutes_per_finished_minute')
        if evidence.get('checkpoint_sha256')!=entry['checkpoint_sha256'] or type(acceptance) not in (int,float) or type(repair) not in (int,float) or not math.isfinite(acceptance) or not math.isfinite(repair) or not 0<=acceptance<=1 or repair<0:raise ValueError('Bind finite human metrics to this exact checkpoint')
        scope=digest([entry['track'],entry['creator'],entry['style']]);old=r.setdefault('active_scopes',{}).get(scope,'B1');entry.update(state='human-approved',human_approved=True,production_eligible=True,approval=copy.deepcopy(evidence));r['history'].append(dict(track=entry['track'],creator=entry['creator'],style=entry['style'],previous=old,next=run_id,reviewer=evidence['reviewer'],time=time.time()));r['active_scopes'][scope]=run_id;entry['state']='active';r['revision']+=1
        asset_learning.write(root/'models/registry.json',r);return copy.deepcopy(entry)

def rollback(root,track,base_revision,creator='local-experimental',style='locked-native'):
    root=Path(root)
    with Lease(root/'models/registry.lock'):
        r=registry(root)
        if type(base_revision) is not int or r['revision']!=base_revision:raise ValueError('Registry revision conflict')
        scope=digest([track,creator,style]);old=r.setdefault('active_scopes',{}).get(scope,'B1');r['active_scopes'][scope]='B1';r['history'].append(dict(track=track,creator=creator,style=style,previous=old,next='B1',reason='explicit rollback',time=time.time()));r['revision']+=1;asset_learning.write(root/'models/registry.json',r);return dict(active='B1',previous=old,revision=r['revision'])
