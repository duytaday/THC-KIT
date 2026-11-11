"""Optional private Kaggle generation and provenance-tagged illustrative artifacts."""
import copy,hashlib,json,os,re,shutil,struct,subprocess,sys,uuid,zipfile
from pathlib import Path
from engine import media
import storyboard

def cli():
    path=os.environ.get('CUTROOM_KAGGLE_CLI') or shutil.which('kaggle')
    if not path:raise ValueError('Kaggle CLI unavailable. Built-in local animations still work; configure the optional Kaggle account first.')
    return path
def command(args,cwd=None):
    result=subprocess.run([cli(),*map(str,args)],cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180,**media.launch_options())
    if result.returncode:raise ValueError('Kaggle action failed: '+(result.stderr or result.stdout)[-1200:])
    return result.stdout

def receipt(folder):
    folder=Path(folder);p=folder/'provenance.json'
    if not p.exists():p=folder/'generation-provenance.json'
    data=json.loads(p.read_text(encoding='utf-8'))
    if data['status']!='COMPLETE':raise ValueError('This generation/training run did not complete.')
    if data['task']=='video_diffusion_lora':
        if not data.get('training_completed') or data.get('actual_optimizer_steps',0)<=0 or data.get('weight_update_l2',0)<=0:raise ValueError('No actual generative weight update is recorded.')
        for name,h in data['adapter_files'].items():
            path=(folder/'adapter'/name).resolve();path.relative_to(folder.resolve())
            if media.sha(path)!=h:raise ValueError('Adapter hash mismatch.')
            if name.endswith('.safetensors'):
                with path.open('rb') as f:
                    prefix=f.read(8)
                    if len(prefix)!=8:raise ValueError('Truncated adapter header.')
                    size=struct.unpack('<Q',prefix)[0]
                    if not 0<size<20*1024**2:raise ValueError('Invalid adapter header size.')
                    header=json.loads(f.read(size))
                names=[n for n in header if n!='__metadata__']
                if not any('lora' in n and any(k in n for k in ('to_q','to_k','to_v','to_out')) for n in names):raise ValueError('Not a CogVideoX video-diffusion LoRA; planner weights are not interchangeable.')
    elif data['task']=='video_diffusion_inference':
        if not data.get('weights_loaded') or 'talking-head-style' not in data.get('active_adapters',[]):raise ValueError('No verified adapter activation receipt.')
    else:raise ValueError('This is not a generative-video run; an edit-selector adapter cannot generate footage.')
    for video in data.get('outputs',[]):
        path=(folder/video['file']).resolve();path.relative_to(folder.resolve())
        if path.suffix.lower()!='.mp4' or media.sha(path)!=video['sha256']:raise ValueError('Generated preview bytes changed.')
    return data

class GenerativeStore:
    def __init__(self,ws):self.ws=ws
    def import_package(self,path,source_kernel=''):
        package_hash=media.sha(path)
        existing=next((r['id'] for r in self.ws.data.get('generative_runs',{}).values() if r.get('package_sha256')==package_hash and r.get('source_kernel')==source_kernel),None)
        if existing:return existing
        id_=uuid.uuid4().hex;folder=self.ws.root/'generative-runs'/id_;folder.mkdir(parents=True,exist_ok=False)
        with zipfile.ZipFile(path) as z:
            if sum(i.file_size for i in z.infolist())>500*1024**2:raise ValueError('Use the compact adapter/preview bundle, not the model download cache.')
            for info in z.infolist():
                dest=(folder/info.filename).resolve();dest.relative_to(folder.resolve())
                if info.is_dir():continue
                if (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Symlinks are not accepted in generation bundles.')
                if dest.suffix.lower() not in ('.json','.mp4','.safetensors','.txt','.log'):continue
                dest.parent.mkdir(parents=True,exist_ok=True)
                with z.open(info) as source,dest.open('wb') as target:shutil.copyfileobj(source,target)
        candidates=list(folder.rglob('provenance.json'))+list(folder.rglob('generation-provenance.json'))
        if len(candidates)!=1:raise ValueError('Use one completed run per bundle.')
        location=candidates[0].parent;data=receipt(location)
        if source_kernel and not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+(?:/\d+)?',source_kernel):raise ValueError('Use a Kaggle owner/kernel[/version] identifier.')
        record=dict(id=id_,folder=str(location),package_sha256=package_hash,receipt_sha256=media.sha(candidates[0]),receipt=data,source_kernel=source_kernel,origin='imported private Kaggle result; human editorial review still required',status='EXPERIMENTAL · NEEDS_REVIEW')
        with self.ws.lock:self.ws.data.setdefault('generative_runs',{})[id_]=record;self.ws.save()
        return id_
    def create_scene(self,run_id,video_name,job_id,passage_id,at,title):
        with self.ws.lock:
            record=copy.deepcopy(self.ws.data['generative_runs'][run_id]);host=copy.deepcopy(self.ws.data['assets'][job_id]);job=self.ws.data['jobs'][job_id];self.ws.artifacts._check_job(job)
            script=job['settings']['script']
        data=receipt(record['folder']);output=next(x for x in data['outputs'] if x['file']==video_name)
        if output.get('label')!='candidate':raise ValueError('Choose a candidate output; baseline stays available for comparison.')
        parts,timing=storyboard.passages(script,host['duration'],Path(host['path']));part=next(p for p in parts if p['id']==passage_id)
        # Workspace.import_asset consumes a temporary copy and never changes the run output.
        temp=self.ws.root/'work'/(uuid.uuid4().hex+'.mp4');shutil.copy2(Path(record['folder'])/video_name,temp);asset_id=self.ws.import_asset(temp,'AI illustration · '+video_name,'generated')
        asset=self.ws.data['assets'][asset_id];duration=round(asset['duration']*30)/30
        if float(at)<0 or float(at)+duration>host['duration']+.001:raise ValueError('Place the illustration inside the recording.')
        plan=dict(schema_version=1,type='demo',kind='generated_video',title=title,source_quote=part['quote'],passage_ids=[part['id']],occurrence=part['occurrence'],intended_visual='Generated illustration; never real software-action proof.',duration=duration,at=float(at),position='top',intensity=.5,sound='none',evidence={'asset':asset_id},narration_status='recorded_words_unverified',timing=timing,enabled=True,status='NEEDS_REVIEW',review_status='UNVERIFIED',origin='generative_lora_candidate',generation_provenance=dict(run_id=run_id,receipt_sha256=record['receipt_sha256'],base_model=data.get('base_model'),base_revision=data.get('base_revision'),adapter=data.get('adapter_files') or data.get('adapter_sha256'),prompt=output['prompt'],seed=output['seed']))
        artifact=dict(id=uuid.uuid4().hex,job=job_id,story_key='generated|'+run_id+'|'+video_name+'|'+passage_id,inserted=False,versions=[])
        with self.ws.lock:
            self.ws.data.setdefault('storyboards',{})[job_id]={'passages':parts,'timing':timing,'limitations':['Generated scenes are illustrations, not product proof.']}
            self.ws.artifacts._render_version(artifact,plan);self.ws.artifacts.records()[artifact['id']]=artifact;self.ws.artifacts._dirty(self.ws.data['jobs'][job_id]);self.ws.save()
        return artifact['id']
    def submit(self,run_id,prompt,seed=3407):
        if not 10<=len(prompt.strip())<=1800:raise ValueError('Describe a short illustration in10–1800characters.')
        run=self.ws.data['generative_runs'][run_id];data=receipt(run['folder'])
        if data['task']!='video_diffusion_lora' or not run.get('source_kernel'):raise ValueError('Import the trained adapter run with its private Kaggle kernel identifier first.')
        kernel='/'.join(run['source_kernel'].split('/')[:2]);owner=kernel.split('/')[0];id_=uuid.uuid4().hex;slug='talking-head-cutroom-generate-'+id_[:12];folder=self.ws.root/'generative-jobs'/id_;folder.mkdir(parents=True,exist_ok=False)
        if not 0<=int(seed)<=2**32-1:raise ValueError('Use a seed between0 and4294967295.')
        adapter=next(h for name,h in data['adapter_files'].items() if name.endswith('.safetensors'));request=dict(prompt=prompt.strip(),seed=int(seed),inference_steps=40,width=720,height=480,include_baseline=True,base_model=data['base_model'],base_revision=data['base_revision'],adapter_sha256=adapter,product_proof=False)
        cache_key=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()
        existing=next((j['id'] for j in self.ws.data.get('generative_jobs',{}).values() if j.get('cache_key')==cache_key and j['status']!='FAILED'),None)
        if existing:return existing
        (folder/'generate.py').write_text('REQUEST='+repr(request)+'\n'+(Path(__file__).parent/'generative_infer.py').read_text(encoding='utf-8'),encoding='utf-8')
        meta=dict(id=owner+'/'+slug,title='Talking Head Cutroom Generate '+id_[:12],code_file='generate.py',language='python',kernel_type='script',is_private=True,enable_gpu=True,machine_shape='NvidiaTeslaT4',enable_internet=True,dataset_sources=[],competition_sources=[],kernel_sources=[kernel]);media.write_json(folder/'kernel-metadata.json',meta)
        result=command(['kernels','push','-p','.'],cwd=folder)
        if 'not valid kernel sources' in result:raise ValueError('Kaggle rejected the private adapter source; no generation is claimed.')
        actual=re.search(r'https://www\.kaggle\.com/code/([A-Za-z0-9_-]+/[A-Za-z0-9_-]+)',result)
        if not actual or not actual[1].startswith(owner+'/'):raise ValueError('Kaggle did not return the expected account’s actual kernel URL.')
        record=dict(id=id_,kernel=actual[1],prompt=prompt,seed=seed,model_run=run_id,cache_key=cache_key,status='SUBMITTED',folder=str(folder),uploaded='Prompt and fixed inference code only; no customer footage',outputs=[],log=result)
        with self.ws.lock:self.ws.data.setdefault('generative_jobs',{})[id_]=record;self.ws.save()
        return id_
    def check(self,id_):
        job=self.ws.data['generative_jobs'][id_]
        reported=re.search(r'https://www\.kaggle\.com/code/([A-Za-z0-9_-]+/[A-Za-z0-9_-]+)',job.get('log',''))
        if reported:job['kernel']=reported[1]
        if job.get('status')=='COMPLETE' and job.get('output_run') in self.ws.data.get('generative_runs',{}):return copy.deepcopy(job)
        status=command(['kernels','status',job['kernel']]);job['remote_status']=status.strip()
        if 'COMPLETE' in status:
            target=Path(job['folder'])/'result';target.mkdir(exist_ok=True);command(['kernels','output',job['kernel'],'--file-pattern',r'(generation-provenance\.json|baseline-.*\.mp4|candidate-.*\.mp4|failure\.log)$','-p',str(target)])
            manifest=next(target.rglob('generation-provenance.json'));data=receipt(manifest.parent);run_id=uuid.uuid4().hex;self.ws.data.setdefault('generative_runs',{})[run_id]=dict(id=run_id,folder=str(manifest.parent),receipt_sha256=media.sha(manifest),receipt=data,source_kernel=job['kernel'],status='EXPERIMENTAL · NEEDS_REVIEW');job.update(status='COMPLETE',output_run=run_id,outputs=data['outputs'])
        elif 'ERROR' in status or 'CANCEL' in status:job['status']='FAILED'
        else:job['status']='RUNNING'
        with self.ws.lock:self.ws.save()
        return job
