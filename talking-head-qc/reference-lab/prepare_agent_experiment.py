"""Private, explicitly agent-reviewed pilot. Production approval is never inferred."""
import collections,copy,importlib.util,json,re,shutil
from pathlib import Path
from video_kit import read,write,sha,digest,validate,permission,search

ROOT=Path(__file__).resolve().parent;KIT=ROOT.parents[1];LAB=KIT/'output/5-repo-ai/reference-lab'
OUT=LAB/'kaggle-agent-pilot-v001';DATA=OUT/'dataset';KERNEL=OUT/'kernel'
USER='duytruyenthong'

def main():
    reviewed=LAB/'agent-label-review-v001/reviewed-decisions.jsonl'
    rows=[json.loads(s) for s in reviewed.read_text(encoding='utf-8').splitlines() if s.strip()]
    manifest=validate(read(LAB/'inventory/references.json'));assets={a['id']:a for a in manifest['assets']};rights={r['id']:r for r in manifest['rights']}
    ids=set()
    for r in rows:
        if r['decision_id'] in ids:raise ValueError('Duplicate decision')
        ids.add(r['decision_id']);a=assets[r['asset_id']]
        if not permission(rights[a['rights_id']],'train_commercial') or a['sha256']!=r['asset_sha256'] or sha(a['path'])!=a['sha256']:raise ValueError('Source rights/bytes invalid')
        if not a['family_reviewed'] or not a['presenter_verified'] or a['family_id']!=r['family_id']:raise ValueError('Source review invalid')
        packet=Path(r['evidence_id']);evidence=read(packet)
        if not packet.exists() or not r.get('visual_sequence_reviewed') or r.get('human_approved') is not False or r.get('transcript_verified_by_hearing') is not False:raise ValueError('Review provenance invalid')
    families=sorted({r['family_id'] for r in rows},key=lambda f:digest('3407:'+f))
    if len(families)!=19:raise ValueError('Expected reviewed19source families; recalculate split explicitly if corpus changed')
    assignments={f:('train' if i<13 else 'validation' if i<15 else 'test') for i,f in enumerate(families)}
    OUT.mkdir(exist_ok=False);DATA.mkdir();KERNEL.mkdir()
    split={'seed':3407,'grouping':'source_family','scope':'within_creator_episode_holdout','creator_identity_known':False,'locked_before_model_evaluation':True,'reviewed_input_sha256':sha(reviewed),'assignments':assignments,'split_hash':digest(assignments)}
    write(OUT/'split.json',split)
    heldout=[f for f,p in assignments.items() if p!='train']
    # Same fixed shortlist/prompt for rules, base and adapter. No held-out cards.
    for r in rows:
        # Gold-derived flags were found in pilotv001. Preserve that frozen run,
        # but omit them from future experimental inputs until independently labelled.
        for key in ('keep_presenter','requires_result','result_visible'):r.pop(key,None)
        options={}
        for motion in ('screen','label','proof','hold'):
            found=search(LAB/'inventory/references.json',motion,r['cue']+' '+r['visible_before'],format_='9:16',exclude_families=heldout)
            for rank,card in enumerate(found['results']):
                key=card['segment_id'];score=1/(60+rank+1)
                if key not in options:options[key]={'score':0,'card':card}
                options[key]['score']+=score
        chosen=sorted(options.values(),key=lambda x:(-x['score'],x['card']['segment_id']))[:3]
        r['shortlist']=[{'segment_id':x['card']['segment_id'],'recipe_id':x['card']['recipe_id'],'citation':x['card']['citation'],'editorial_reason':x['card']['editorial_reason']} for x in chosen]
        r['evidence_id']=str(Path(r['evidence_id']).relative_to(LAB)).replace('\\','/')
    files={}
    for part in ('train','validation','test'):
        selected=[r for r in rows if assignments[r['family_id']]==part]
        # Do not transmit local paths or raw reference footage.
        allowed=('decision_id','asset_id','family_id','episode_id','creator_id','asset_sha256','source_range_ms','cue','visible_before','visible_during','visible_after','choices','chosen','rejected','reason','reviewer','evidence_id','rights_id','data_class','human_approved','agent_reviewed','visual_sequence_reviewed','transcript_verified_by_hearing','temporal_context_approved','shortlist','requires_result','result_visible','keep_presenter','sampling_uncertainty','review_scope')
        selected=[{k:r[k] for k in allowed if k in r} for r in selected]
        f=DATA/(part+'.jsonl');f.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in selected)+'\n',encoding='utf-8');files[f.name]=sha(f)
    source_ids={r['asset_id'] for r in rows}|{c['citation']['asset_id'] for r in rows for c in r['shortlist']}
    sources={id_:{k:assets[id_][k] for k in ('sha256','family_id','rights_id','family_reviewed','presenter_verified','duration_ms')} for id_ in source_ids}
    authorized=[id_ for id_,r in rights.items() if permission(r,'train_commercial')]
    write(DATA/'training-manifest.json',{'schema_version':1,'data_class':'agent_reviewed_experiment','approval_kind':'agent_visual_asr_review','approved':False,'deployment_eligible':False,'authorization':{'user_authorized_agent_labels':True,'answer':'Agent duyệt nhãn thử nghiệm','date':'2026-11-11','scope':'First private Kaggle experiment; adapter stays OFF in delivery workflow'},'files':files,'dataset_hash':digest(rows),'reviewed_input_sha256':sha(reviewed),'split_hash':split['split_hash'],'split_scope':split['scope'],'sources':sources,'train_authorized_rights_ids':authorized,'media_uploaded':False,'audio_uploaded':False,'human_reviewed_labels':0,'agent_reviewed_labels':len(rows),'limitations':['ASR not heard or verified by human','Unknown creator identity: source-family/episode holdout only','English references, Vietnamese editorial transfer not established','No engagement analytics or causal quality claim']})
    config=read(LAB/'kaggle-v001/config.json');config.update(max_steps=40,gradient_accumulation_steps=4,max_length=1536,adapter_default='off',deployment_eligible=False,training_data_class='agent_reviewed_experiment')
    write(DATA/'config.json',config)
    shutil.copy2(ROOT/'kaggle/train_kaggle.py',DATA/'train_kaggle.py')
    requirements='transformers==4.57.6\npeft==0.18.1\naccelerate==1.12.0\ndatasets==4.5.0\nbitsandbytes==0.50.2\njinja2==3.1.6\n'
    (DATA/'requirements.txt').write_text(requirements,encoding='utf-8')
    write(DATA/'dataset-metadata.json',{'title':'Talking Head Agent Reviewed Pilot 20261111','id':USER+'/talking-head-agent-labels-20261111','licenses':[{'name':'other'}]})
    wrapper='''import importlib.util,json,os,subprocess,sys,traceback
from pathlib import Path
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
stage='dataset_gate'
try:
    roots=list(Path('/kaggle/input').rglob('training-manifest.json'))
    assert len(roots)==1,'Exactly one private experimental dataset required'
    root=roots[0].parent
    spec=importlib.util.spec_from_file_location('pilot_trainer',root/'train_kaggle.py')
    trainer=importlib.util.module_from_spec(spec);spec.loader.exec_module(trainer)
    trainer.check_dataset(root,allow_agent_experiment=True)
    stage='install_pinned_libraries'
    subprocess.run([sys.executable,'-m','pip','install','-r',str(root/'requirements.txt')],check=True)
    stage='actual_model_training_and_evaluation'
    trainer.main(allow_agent_experiment=True)
except Exception as error:
    Path('/kaggle/working/pilot-error.json').write_text(json.dumps({'stage':stage,'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()},indent=2))
    raise
'''
    (KERNEL/'run_pilot.py').write_text(wrapper,encoding='utf-8')
    write(KERNEL/'kernel-metadata.json',{'id':USER+'/talking-head-agent-selector-pilot-private','title':'Talking Head Agent Selector Pilot Private','code_file':'run_pilot.py','language':'python','kernel_type':'script','is_private':True,'enable_gpu':True,'machine_shape':'NvidiaTeslaT4','enable_internet':True,'dataset_sources':[USER+'/talking-head-agent-labels-20261111'],'competition_sources':[],'kernel_sources':[]})
    spec=importlib.util.spec_from_file_location('check_export',DATA/'train_kaggle.py');trainer=importlib.util.module_from_spec(spec);spec.loader.exec_module(trainer)
    trainer.check_dataset(DATA,allow_agent_experiment=True)
    package=read(DATA/'training-manifest.json')
    package['files'].update({n:sha(DATA/n) for n in ('config.json','train_kaggle.py','requirements.txt')})
    write(DATA/'training-manifest.json',package)
    # Upload only this whitelist. Importing the validator can create __pycache__.
    upload=OUT/'upload';upload.mkdir()
    for name in ('config.json','train_kaggle.py','requirements.txt','training-manifest.json','train.jsonl','validation.jsonl','test.jsonl','dataset-metadata.json'):
        shutil.copy2(DATA/name,upload/name)
    write(OUT/'preparation.json',{'status':'VALIDATED_NOT_UPLOADED','rows':len(rows),'split_rows':{p:sum(assignments[r['family_id']]==p for r in rows) for p in ('train','validation','test')},'choices':dict(collections.Counter(r['chosen'] for r in rows)),'source_families':19,'human_approved':0,'adapter_default':'off','actual_training_steps':0,'dataset_manifest_sha256':sha(DATA/'training-manifest.json'),'trainer_sha256':sha(DATA/'train_kaggle.py')})
    print(json.dumps(read(OUT/'preparation.json'),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
