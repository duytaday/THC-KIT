"""Adapt actual Cutroom recipes and human observations to the kit release hooks."""
import copy,json,os,shutil,sys
from pathlib import Path
TOOLS=Path(__file__).resolve().parents[1]/'talking-head-qc/tools'
sys.path.insert(0,str(TOOLS))
from qc_profile import prepare
from qc_hook import inspect_and_save,release_receipt
from qc_gates import sha

SKILL=Path(os.environ.get('CUTROOM_QC_SKILL',Path.home()/'.agents/skills/ffmpeg-skill'))
def write(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def prepare_export(folder,host,settings,plan):
    duration=round(host['duration']*30)/30
    (folder/'brief.md').write_text('Cutroom recorded-presenter edit. Preserve narration and meaning. Apply the selected caption treatment and framing, show each assigned cutaway with readable results, and preserve any spoken CTA.\n\nSpoken script supplied by creator:\n'+settings['script'],encoding='utf-8')
    write(folder/'delivery.json',dict(platform='youtube',width=1080,height=1920,min_seconds=max(.01,duration-.05),max_seconds=duration+.05,caption_mode='burned_in_and_sidecar',language='vi',required_beats=['presenter']+[f'cutaway-{i}' for i,_ in enumerate(plan['proof'])]))
    beats=[dict(id='presenter',source=host['path'],source_start=0,source_end=host['duration'],output_start=0,output_end=duration)]
    for i,q in enumerate(plan['proof']):beats.append(dict(id=f'cutaway-{i}',source=q['file'],source_start=q['source_start'],source_end=q['source_start']+q['end']-q['start'],output_start=q['start'],output_end=q['end']))
    write(folder/'timeline.json',dict(expected_frames=round(duration*30),beats=beats,settings=copy.deepcopy(settings)))
    from engine.enhance import events_for,sound_asset
    dependencies={Path(__file__).parent/'engine'/name for name in ('edit.py','media.py','enhance.py','cues.py','layouts.py','planner.py')}
    dependencies.add(Path(__file__).parent/'fonts/DejaVuSans-Bold.ttf')
    if plan.get('motion_specs'):
        dependencies.update(Path(__file__).parent/name for name in ('motion_specs.py','motion_render.py','motion_hooks.py'))
    dependencies.update(Path(q['file']) for q in plan['proof'])
    for e in events_for(plan,[[0,host['duration'],0]]):
        if not e['sound'].get('muted') and e['sound'].get('id'):dependencies.add(sound_asset(e['sound'])[0])
    if plan.get('music',{}).get('mode','off')!='off':dependencies.add(Path(plan['music'].get('path') or Path(__file__).parent/'music'/(plan['music'].get('track','calm')+'.wav')))
    write(folder/'render-project.json',dict(source=host['path'],source_sha256=sha(host['path']),plan=copy.deepcopy(plan),renderer=str(Path(__file__).parent/'engine/edit.py'),renderer_sha256=sha(Path(__file__).parent/'engine/edit.py'),dependencies=[dict(path=str(p),sha256=sha(p)) for p in sorted(dependencies)]))
    profile=prepare(folder,expected_frames=round(duration*30))
    profile['project_hashes']={'render-project.json':sha(folder/'render-project.json')}
    profile['demonstrations']=[dict(id=f'cutaway-{i}',claim='Original/generated/reference explanatory illustration; not real product-action proof. Verify its correspondence to the spoken idea.' if q.get('artifact_kind') in ('process','list','generated_video','reference_excerpt') else 'Creator-assigned demonstration must show target, action and readable result.',source_asset=q['file'],source_sha256=sha(q['file']),source_range=[q['source_start'],q['source_start']+q['end']-q['start']],master_range=[q['start'],q['end']]) for i,q in enumerate(plan['proof']) if q.get('artifact_type')!='introduction']
    import re
    if re.search(r'\b(5|năm)\s+repo',settings['script'],re.I):
        from storyboard import REPOS
        profile['required_repository_count']=5
        mentions=[(re.search(r'(?<!\w)'+re.escape(repo)+r'(?!\w)',settings['script'],re.I),repo) for repo in REPOS]
        promised=[repo for match,repo in sorted([(m,r) for m,r in mentions if m is not None],key=lambda item:item[0].start())]
        promised += ['UNASSIGNED REPO '+str(i+1) for i in range(len(promised),5)]
        for repo in promised:
            candidates=[q for q in plan['proof'] if q.get('artifact_type')!='introduction' and q.get('artifact_kind') not in ('process','list','generated_video','reference_excerpt') and re.search(r'(?<!\w)'+re.escape(repo.split()[0])+r'(?!\w)',q.get('source_name',''),re.I)]
            for i,q in enumerate(candidates or [None]):
                profile['demonstrations'].append(dict(id='promised-'+repo.replace(' ','-')+'-'+str(i),repo_name=repo,claim='Verify this named repository’s own promised demo; a generic animation is not product proof.',source_asset=q['file'] if q else '',source_sha256=sha(q['file']) if q else '0'*64,source_range=[q['source_start'],q['source_start']+q['end']-q['start']] if q else None,master_range=[q['start'],q['end']] if q else [0,duration]))
    profile['gates']['B']['evidence_ids']=[d['id'] for d in profile['demonstrations']] or ['presenter_visuals']
    profile['evidence_ranges']={d['id']:d['master_range'] for d in profile['demonstrations']}
    fx=settings.get('insert_sound','none')
    if fx!='none':
        sounds=Path(__file__).parent/'sounds';peak=json.loads((sounds/'peaks.json').read_text())[fx]['peak_sample']/48000;stem=sounds/(fx+'.wav')
        profile['motion_cues']=[dict(id=f'insert-{i}',frame_locked=True,visual_frame=round(q['start']*30),stem_path=str(stem),stem_sha256=sha(stem),stem_master_offset_seconds=round(q['start']*30)/30-peak,window_seconds=.1) for i,q in enumerate(plan['proof'])]
    events=events_for(plan,[[0,host['duration'],0]])
    profile['motion_cues']=[]
    for e in events:
        sound=e['sound']
        if sound.get('muted') or not sound.get('id'):continue
        stem,marker,left,right=sound_asset(sound);offset=sound.get('offset_frames',0)
        profile['motion_cues'].append(dict(id=e['id'],frame_locked=True,visual_frame=e['master_frame'],stem_path=str(stem),stem_sha256=sha(stem),stem_master_offset_seconds=e['sample']/48000+offset/30-marker/48000,window_seconds=max(.12,abs(offset)/30+.12),expected_offset_frames=offset if sound.get('offset_reason') else 0,editorial_exception=sound.get('offset_reason',''),landmark='peak_abs'))
    write(folder/'acceptance-profile.json',profile)

def verify_reproduction(folder,host,plan,render):
    """Actually run the unchanged recipe twice; never infer reproducibility."""
    project=json.loads((folder/'render-project.json').read_text(encoding='utf-8'))
    for item in project.get('dependencies',[]):
        if sha(item['path'])!=item['sha256']:raise ValueError('A render dependency changed during the job: '+item['path'])
    rerun=folder/'reopened';rerun.mkdir();shutil.copytree(folder/'fonts',rerun/'fonts')
    render(Path(host['path']),copy.deepcopy(plan),rerun)
    output=rerun/'edit.mp4'
    write(folder/'repeatability.json',dict(master_sha256=sha(folder/'edit.mp4'),project_sha256=sha(folder/'render-project.json'),rerender_path=str(output),rerender_sha256=sha(output)))

def check(folder):return inspect_and_save(folder,SKILL)

def approve(folder,body):
    report=json.loads((folder/'qc.json').read_text(encoding='utf-8'));profile=json.loads((folder/'acceptance-profile.json').read_text(encoding='utf-8'));duration=report['duration_seconds']
    reviewer=str(body.get('reviewer','')).strip()
    if not reviewer:raise ValueError('Enter the name of the person who actually watched and listened.')
    notes=body.get('gate_notes',{})
    import re
    for k in 'ABCDEF':
        if not isinstance(notes.get(k),str) or len(notes[k].strip())<12 or not re.search(r'\b\d{1,2}:[0-5]\d\b',notes[k]):raise ValueError('Add a timestamp and what you verified for each of the six review gates.')
    review=json.loads((folder/'review-form.json').read_text(encoding='utf-8'))
    review.update(reviewer=dict(id=reviewer,runtime='Cutroom local human review',can_watch=True,can_listen=True),viewing=dict(speed=1,width_px=360),listening_speed=1,watched_ranges=[[0,duration]],listened_ranges=[[0,duration]],approved_by=reviewer)
    for k in 'ABCDEF':
        ids=profile['gates'][k].get('evidence_ids',[]) or ['export']
        review['gates'][k]=dict(status='PASS',evidence=[dict(id=id_,master_range=[0,duration],expected='Gate '+k+' acceptance goal',actual=notes[k],evidence='Explicit human observation entered in Cutroom') for id_ in ids])
    review['sync_observations']=body.get('sync_observations',[])
    review['cue_observations']=body.get('cue_observations',[])
    review['warning_dispositions']={w:notes['F'] for w in review.get('warning_dispositions',{})}
    # Review is an operator attestation, not inferred from player progress.
    history=folder/'review-history';history.mkdir(exist_ok=True)
    if (folder/'review.json').exists():shutil.copy2(folder/'review.json',history/(__import__('uuid').uuid4().hex+'.json'))
    write(folder/'review.json',review)
    result=check(folder)
    if not release_receipt(folder,result):raise ValueError('Review saved, but release remains '+result['status']+'. Inspect the QC details and complete missing evidence.')
    return result
