"""Optional model planning with visible, versioned fallback and source-resolved decisions."""
import copy,json,os,subprocess,sys,time
from pathlib import Path
from engine import media
import learning,storyboard

MODES=('built_in','base','base_rag','fine_tuned')

def checkpoint(root,mode):
    folder=Path(root).resolve()/'models'/'candidate';file=folder/'preset.json'
    if not file.exists():raise ValueError('Missing checkpoint: models/candidate/preset.json. Built-in rules remain active.')
    config=json.loads(file.read_text(encoding='utf-8'))
    if not config.get('version') or config.get('model_revision')!=learning.BASE['model_revision']:raise ValueError('Unpinned or incompatible model revision.')
    verified={}
    for name,h in config.get('files',{}).items():
        p=(folder/name).resolve();p.relative_to(folder.resolve())
        if p.suffix=='.bin':raise ValueError('Use safetensors, not pickled weights.')
        if not p.exists() or media.sha(p)!=h:raise ValueError('Missing or changed checkpoint file: '+name)
        verified[name]=h
    for k in ('base_path','adapter_path') if mode=='fine_tuned' else ('base_path',):
        p=(folder/config[k]).resolve();p.relative_to(folder.resolve());config[k]=str(p)
        wanted='adapter_model.safetensors' if k=='adapter_path' else 'config.json'
        if not (p/wanted).is_file() or str((p/wanted).relative_to(folder)).replace('\\','/') not in verified:raise ValueError('Missing hash-bound '+wanted)
        for asset in p.rglob('*'):
            if asset.is_file() and str(asset.relative_to(folder)).replace('\\','/') not in verified:raise ValueError('Unpinned model asset: '+asset.name)
    if mode=='fine_tuned' and not config.get('dataset_fingerprint'):raise ValueError('Adapter has no training provenance.')
    config['verified_hashes']=verified;return config

def resolve_sequence(context,master_start,master_end):
    """Resolve timestamps from this footage, never copy reference/model timestamps."""
    decisions=[]
    for a in context['available_media']:
        anchors=a.get('anchors',{});required=('target','contact','result','opened')
        missing=[k for k in required if anchors.get(k) is None or not a['observed_range'][0]<=anchors[k]<a['observed_range'][1]]
        if missing:decisions.append(dict(choice='REVIEW',asset=a['id'],pickup='Record '+', '.join(missing)+' on this screen sequence; retain presenter until proof is available.'));continue
        if [anchors[k] for k in required]!=sorted(anchors[k] for k in required):raise ValueError('Observed control/contact/result/opened sequence is inconsistent.')
        offset=a['master_start']-a['observed_range'][0]
        for kind,key in [('SHOW_CONTROL','target'),('CONTACT','contact'),('HOLD_RESULT','result'),('OPEN_FILE','opened')]:
            decisions.append(dict(choice=kind,asset=a['id'],source_pts=anchors[key],master_frame=round((offset+anchors[key])*30),hold_until_frame=round((offset+(anchors['opened'] if key=='result' else a['observed_range'][1]))*30),anchor_basis='observed current source; never inherited from reference'))
    return decisions

def apply(root,host,settings,plan,assets):
    mode=settings.get('planner_mode','built_in');started=time.monotonic()
    receipt=dict(requested=mode,origin='reference-guided' if settings.get('style_ref') else 'built-in rules',model_version='rules-v2',weights_loaded=False,retrieved_reference_ids=[],fallback=None,decisions=[],runtime_seconds=0,paid_api_spend=0,accepted_finished_minutes=None,cost_per_accepted_minute=None)
    if mode=='built_in':plan['planner_receipt']=receipt;return receipt
    try:
        preset=checkpoint(root,mode)
        parts,_=storyboard.passages(settings['script'],host['duration'],Path(host['path']));rows=[]
        pool=[]
        if mode in ('base_rag','fine_tuned'):
            path=Path(root)/'models/candidate/retrieval-train-only.json'
            if not path.exists():raise ValueError('Missing frozen training-only retrieval index.')
            key='retrieval-train-only.json'
            if preset['verified_hashes'].get(key)!=media.sha(path):raise ValueError('Retrieval index differs from the model preset.')
            pool=json.loads(path.read_text(encoding='utf-8'))
            if any(r.get('split')!='train' for r in pool):raise ValueError('Retrieval contains unverified or held-out groups.')
            if any(r.get('source_sha256')==media.sha(host['path']) for r in pool):raise ValueError('This episode is present in retrieval; unseen export required.')
        from train_planner import retrieve
        for p in parts:
            available=[]
            for q in plan['proof']:
                if q.get('artifact_type')=='introduction' or q['end']<p['start'] or q['start']>p['end']:continue
                available.append(dict(id=q['id'],sha256=media.sha(q['file']),duration=media.duration(media.stream(q['file'],'video')),observed_range=[q['source_start'],q['source_start']+q['end']-q['start']],description=q.get('source_name','Creator-assigned proof'),evidence='Explicit source anchors supplied by operator',anchors=q.get('anchors',{}),master_start=q['start']))
            context=dict(passage=p['quote'],speech_timing=[p['start'],p['end']],available_media=available,reference_observations=[],choices=list(learning.DECISIONS));examples=retrieve(context,pool) if pool else []
            rows.append(dict(id=p['id'],input=context,retrieved=examples));receipt['decisions'].append(dict(passage_id=p['id'],source_quote=p['quote'],resolved=resolve_sequence(context,p['start'],p['end'])))
        executable=os.environ.get('CUTROOM_PLANNER_PYTHON',sys.executable)
        proc=subprocess.run([executable,str(Path(__file__).parent/'planner_worker.py')],input=json.dumps(dict(mode=mode,preset=preset,rows=rows),ensure_ascii=False),text=True,encoding='utf-8',capture_output=True,timeout=180,**media.launch_options())
        if proc.returncode:raise ValueError('Local planner worker failed: '+proc.stderr[-450:])
        result=json.loads(proc.stdout)
        if not result.get('weights_loaded') or result.get('loaded_hashes')!=preset['verified_hashes']:raise ValueError('Worker did not attest the expected weight files.')
        predictions={p['id']:p for p in result['predictions']}
        for row in rows:
            predicted=predictions[row['id']];part=next(p for p in parts if p['id']==row['id']);choice=predicted['choice']
            if choice not in learning.DECISIONS:raise ValueError('Unsupported model decision.')
            # The model chooses editorial treatment; deterministic source geometry remains authoritative.
            # Manual cues are protected even when the planner prefers a quiet presenter hold.
            if choice in ('STAY_PRESENTER','NO_EFFECT'):
                plan['events']=[e for e in plan.get('events',[]) if e.get('manual_override') or e.get('origin')=='manual' or not part['start']<=e['anchor'].get('timeline_source_pts',e['anchor']['source_pts'])<part['end']]
            receipt['decisions'][rows.index(row)]['prediction']=predicted
        receipt.update(origin='fine-tuned' if mode=='fine_tuned' else 'base planner + retrieval' if mode=='base_rag' else 'base planner',model_version=preset['version'],weights_loaded=True,weights=result['loaded_hashes'],device=result['device'],retrieved_reference_ids=sorted({e['id'] for r in rows for e in r['retrieved']}),deployment_eligible=preset.get('deployment_eligible',False))
    except (OSError,ValueError,KeyError,TypeError,subprocess.TimeoutExpired) as e:receipt['fallback']=str(e);receipt['origin']='built-in rules · visible fallback'
    receipt['runtime_seconds']=time.monotonic()-started;plan['planner_receipt']=receipt;return receipt
