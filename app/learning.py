"""Deliberate, source-bound editorial dataset preparation. Never trains from unlabeled cuts."""
import argparse,copy,hashlib,json,math,re
from pathlib import Path
from engine import media

DECISIONS=('STAY_PRESENTER','SHOW_CONTROL','CONTACT','HOLD_RESULT','OPEN_FILE','ILLUSTRATE','CTA','NO_EFFECT','REVIEW')
INPUT_KEYS={'passage','speech_timing','available_media','reference_observations','choices'}
BASE={'base_model':'Qwen/Qwen2.5-1.5B-Instruct','model_revision':'989aa7980e4cf806f80c7fef2b1adb7bc71aa306'}

def fingerprint(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()
def write(path,value):media.write_json(Path(path),value)

def moments(asset):
    """Candidate editorial windows across the whole episode; all start UNLABELED."""
    length=asset['duration'];points={0.,float(length)}
    for o in asset.get('analysis',{}).get('observations',[]):points.update(o.get('scene_times',[]))
    # Sparse samples must not masquerade as complete human annotation.
    points.update([min(3.,length),length/3,2*length/3,max(0,length-5)])
    points=sorted(t for t in points if 0<=t<=length)
    return [dict(id='moment-'+fingerprint([asset['sha256'],a,b])[:16],master_range=[a,b],raw_source_range=None,coordinate_system='finished_reference_only',episode_region='opening' if a<3 else 'ending_candidate' if b>length-5 else 'middle',decision='UNLABELED',passage='',visible_evidence='',audible_evidence=None,review_status='UNLABELED',input=None,target=None) for a,b in zip(points,points[1:]) if b-a>=.15]

def intake(asset,metadata):
    allowed={'creator','series','family','parent_group','group_reviewed','permission','reviewer','include','presenter_verified','content_evidence'}
    if set(metadata)-allowed:raise ValueError('Unknown training metadata.')
    result=copy.deepcopy(asset.get('training',{}));result.update(copy.deepcopy(metadata))
    if result.get('include') and not result.get('permission'):raise ValueError('Record permission for this training use first.')
    result.setdefault('moments',moments({**asset,'sha256':media.sha(asset['path'])}))
    result['source_sha256']=media.sha(asset['path']);result['training_started']=False
    return result

def annotate(asset,body):
    training=copy.deepcopy(asset.get('training',{}));items=training.get('moments',[])
    moment=next(m for m in items if m['id']==body['id'])
    if not body.get('reviewer') or not body.get('visible_evidence'):raise ValueError('Record the reviewer and observed visual evidence.')
    if body.get('decision') not in DECISIONS:raise ValueError('Choose an explicit decision; an unlabeled interval is not a deliberate presenter hold.')
    for key in ('master_range','raw_source_range'):
        value=body.get(key,moment.get(key))
        if value is not None and (len(value)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in value) or not 0<=value[0]<value[1] or key=='master_range' and value[1]>asset['duration']):raise ValueError('Invalid '+key)
    context=body.get('input')
    if not isinstance(context,dict) or set(context)!=INPUT_KEYS:raise ValueError('Separate inference inputs: passage, speech_timing, available_media, reference_observations and choices.')
    if not body.get('input_independently_reviewed') or not body.get('input_evidence'):raise ValueError('Inputs need independent evidence; do not copy final-editor target annotations into features.')
    target=body.get('target',{})
    if target.get('choice')!=body['decision'] or not target.get('reason'):raise ValueError('Record target choice and reason separately from inference features.')
    if body.get('audible_evidence') and not body.get('can_listen'):raise ValueError('Audible evidence needs a reviewer who actually listened.')
    if body.get('raw_take_rejection_reason') and not body.get('raw_source_range') and not body.get('editor_annotation'):raise ValueError('A finished MP4 alone cannot explain why a raw take was discarded.')
    if not body.get('passage') or body.get('label_kind') not in ('human_reviewed','agent_experiment'):raise ValueError('Record the spoken passage and truthful approval kind.')
    prior=copy.deepcopy(moment);moment.update(copy.deepcopy(body));moment['review_status']='REVIEWED';moment.setdefault('history',[]).append(prior)
    return training

def validate_input(context):
    if set(context)!=INPUT_KEYS:raise ValueError('Unexpected inference feature or target leakage.')
    if not isinstance(context['choices'],list) or not {'NO_EFFECT','REVIEW'}<=set(context['choices']) or set(context['choices'])-set(DECISIONS):raise ValueError('Invalid decision choices.')
    if not isinstance(context['available_media'],list):raise ValueError('Available media must describe actual inputs.')
    for a in context['available_media']:
        if not {'id','sha256','duration','observed_range','description','evidence'}<=set(a):raise ValueError('Media features need independently observed input evidence.')
        if len(a['sha256'])!=64 or not a['evidence']:raise ValueError('Invalid inference asset identity/evidence.')
        if a.get('result_time') is not None and not 0<=a['result_time']<a['duration']:raise ValueError('Result lies outside available footage; request a pickup.')

def dataset(assets):
    refs=[a for a in assets.values() if a['kind']=='reference'];rows=[];excluded=[];sources={}
    for a in refs:
        t=a.get('training',{});issues=[]
        if not t.get('include'):issues.append('not_selected_for_training')
        if not t.get('permission'):issues.append('training_permission_unrecorded')
        if not all(t.get(k) for k in ('creator','series','family','group_reviewed')):issues.append('creator_series_family_group_review_missing')
        if not t.get('presenter_verified') or not t.get('content_evidence'):issues.append('presenter_led_scope_not_verified')
        h=media.sha(a['path'])
        if t.get('source_sha256')!=h:issues.append('source_not_bound_or_changed')
        labels=[m for m in t.get('moments',[]) if m.get('review_status')=='REVIEWED']
        if not labels:issues.append('no_usable_reviewed_moments')
        if issues:excluded.append(dict(asset=a['id'],name=a['name'],reasons=issues));continue
        sources[a['id']]=dict(id=a['id'],sha256=h,creator=t['creator'],series=t['series'],family=t['family'],parent_group=t.get('parent_group'),permission=t['permission'])
        for m in labels:
            validate_input(m['input'])
            if not m.get('input_independently_reviewed') or not m.get('input_evidence'):raise ValueError('Unproven input independence.')
            if m['target']['choice'] not in m['input']['choices']:raise ValueError('Target outside supported choices.')
            rows.append(dict(id=m['id'],asset=a['id'],source_sha256=h,master_range=m['master_range'],raw_source_range=m.get('raw_source_range'),input=m['input'],target=m['target'],reviewer=m['reviewer'],label_kind=m['label_kind'],input_evidence=m['input_evidence']))
    # Connected components: duplicate hashes, creator, series, source families and excerpts.
    parent={k:k for k in sources}
    def find(k):
        while parent[k]!=k:k=parent[k]
        return k
    seen={}
    for k,s in sources.items():
        for field in ('sha256','creator','series','family','parent_group'):
            if not s.get(field):continue
            token=(field,s[field])
            if token in seen:parent[find(k)]=find(seen[token])
            seen[token]=k
    groups={}
    for k in sources:groups.setdefault(find(k),[]).append(k)
    ordered=sorted(groups.values(),key=fingerprint);assignment={}
    for i,group in enumerate(ordered):
        for k in group:assignment[k]='validation' if i==0 else 'test' if i==1 else 'train'
    unique={}
    for row in rows:
        key=fingerprint([row['source_sha256'],row['master_range']])
        if key in unique and unique[key]['target']!=row['target']:raise ValueError('Conflicting duplicate/excerpt labels need editorial resolution.')
        unique.setdefault(key,row)
    rows=list(unique.values());counts={p:sum(assignment[r['asset']]==p for r in rows) for p in ('train','validation','test')}
    blockers=[]
    if len(groups)<3:blockers.append('Need at least three independently reviewed connected source groups; aliases/excerpts/reposts stay together.')
    for p,n in {'train':20,'validation':5,'test':10}.items():
        if counts[p]<n:blockers.append(f'{p}: {counts[p]} reviewed moments; require {n} before the small pilot.')
    return dict(schema_version=2,status='BLOCKED' if blockers else 'READY_FOR_EXPERIMENT',base=BASE,accessible=len(refs),distinct_recordings=len({media.sha(a['path']) for a in refs}),eligible_references=len(sources),usable_labels=len(rows),sources=sources,rows=rows,excluded=excluded,split=assignment,split_counts=counts,group_count=len(groups),dataset_fingerprint=fingerprint(rows),split_fingerprint=fingerprint(assignment),blockers=blockers,training_completed=False,weights_loaded=False,unseen_improvement=None,cost_worthwhile=None)

def export(assets,out):
    report=dataset(assets);out=Path(out);out.mkdir(parents=True,exist_ok=False);write(out/'dataset-report.json',report)
    if report['blockers']:return report
    for part in ('train','validation','test'):
        rows=[r for r in report['rows'] if report['split'][r['asset']]==part]
        (out/(part+'.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    # Retrieval receives only training moments. No held-out transcripts, pixels or corrections.
    write(out/'retrieval-train-only.json',[dict(id=r['id'],source=r['asset'],input=r['input'],target=r['target']) for r in report['rows'] if report['split'][r['asset']]=='train'])
    write(out/'split-manifest.json',{k:report[k] for k in ('sources','split','dataset_fingerprint','split_fingerprint')})
    config=dict(**BASE,seed=3407,max_steps=40,max_length=1024,lora_rank=8,learning_rate=.0001,adapter_default='off',deployment_eligible=False)
    write(out/'config.json',config);write(out/'package-hashes.json',{p.name:media.sha(p) for p in out.iterdir() if p.is_file()})
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('workspace',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();s=json.loads(a.workspace.read_text(encoding='utf-8'));r=export(s['assets'],a.out);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','sources')},ensure_ascii=False,indent=2));raise SystemExit(3 if r['blockers'] else 0)
