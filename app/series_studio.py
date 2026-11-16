"""Series studio orchestration: permitted moments → controlled native trials → new-episode binding."""
import copy,json,math,re,shutil,time,uuid
from pathlib import Path
from engine import media,planner,edit
from revisions import Conflict,digest
import series_library as lib
import reference_moments,motion_specs,motion_storyboard,motion_render,creator_editor

RULE_VERSION='series-native-1'
ROLES=('hook','explain','demo','showcase','cta')

def runtime_identity():
    root=Path(__file__).parent
    paths=[root/n for n in ('motion_specs.py','motion_render.py','motion_storyboard.py','motion_bridge.py','source_context.py','demo_framing.py','series_studio.py','series_library.py','headless.py','reference_moments.py')]
    for sub,pattern in [('engine','*.py'),('fonts','*.ttf'),('sounds','*.wav'),('music','*.wav'),('animation_runtime/vendor','*.cjs')]:paths+=list((root/sub).glob(pattern))
    import subprocess
    p=subprocess.run(['ffmpeg','-version'],capture_output=True,text=True,timeout=15,**media.launch_options())
    return dict(files={p.relative_to(root).as_posix():media.sha(p) for p in paths},ffmpeg=p.stdout.splitlines()[0] if p.returncode==0 else 'unavailable')

def episode(ws,b):
    job=ws.data['jobs'][b['job']];host=ws.data['assets'][job['id']]
    ws.evaluation_access.asset(host)
    if not job['settings']['script'].strip():raise ValueError('Attach the new recording’s own TXT/SRT first')
    import scene_plan
    passages=scene_plan.read(ws,job['id'])['passages'];beats=[]
    hook_added=False
    for i,p in enumerate(passages):
        start=round(p['start']*30)/30;end=min(round(p['end']*30)/30,round(host['duration']*30)/30)
        if end-start<1:continue
        quote=p['quote'];lower=quote.casefold()
        role='hook' if start<3 else 'cta' if re.search(r'đăng ký|theo dõi|subscribe|follow|link.*mô tả',lower) else 'showcase' if re.search(r'ưu đãi|offer|giá bán',lower) else 'demo' if re.search(r'bấm|nhấn|click|xuất|kết quả',lower) else 'explain'
        if role=='hook':
            if hook_added:continue
            start=0;end=min(3,host['duration']);hook_added=True
            quote=' '.join(c['quote'] for c in passages if c['start']<3)
        end=min(end,start+12)
        if end-start<1:continue
        beats.append(dict(id=p['id'],role=role,start=start,end=end,quote=quote,title=quote if len(quote)<=70 else '',requires_proof=role=='demo',
                          viewer_goal='Thấy đúng thao tác và kết quả' if role=='demo' else 'Hiểu ý đang được nói',proof=None,
                          pickup='Quay đúng đối tượng: mục tiêu xuất hiện → thao tác trong câu này → kết quả đủ lâu để đọc: '+quote if role=='demo' else None,
                          return_to_presenter=end,timing=p['timing']))
    return dict(job=job['id'],revision=job['revision'],source_sha256=media.sha(host['path']),beats=beats,edl=job.get('creator',{}).get('keep',[[0,host['duration']]]),
                transcript_status='ASR_TIMED' if job.get('transcript',{}).get('words') else 'SUPPLIED_SCRIPT_UNVERIFIED',manual_mapping_allowed=True)

def request_payload(style,params,context,feedback=None):
    # This is the actual native-builder boundary. There is no provider call here.
    prefix=json.dumps(dict(provider='local',model='native-rules',rules=RULE_VERSION,schema=1,style_identity=style['id'],locked_style=params),sort_keys=True,ensure_ascii=False,separators=(',',':'))
    tail=json.dumps(dict(context=context,feedback=feedback),sort_keys=True,ensure_ascii=False,separators=(',',':'))
    return dict(prefix=prefix,suffix=tail,prefix_sha256=digest(prefix),request_sha256=digest(prefix+'\n'+tail),
                provider_cache_read_tokens=None,cache_status='PREFIX_HASH_ONLY_NO_INFERENCE_CALL')

def _proof(ws,beat,duration):
    proof=beat.get('proof')
    if not proof:return None
    a=ws.data['assets'][proof['asset']];lib.permission(ws,a,'output')
    if a.get('kind')!='reference' or a.get('source_role')=='style_reference' or a.get('media_is_reusable_proof') is False or a.get('data_class') not in (None,'real_screen'):raise ValueError('Use actual current-episode screen footage, not a reference reconstruction')
    p=copy.deepcopy(proof);offset=motion_specs.finite(p.get('offset',0),0,a['duration'],'proof offset')
    if offset+duration>a['duration']+.001:raise ValueError('Proof recording is too short for the retained scene')
    for name in ('target','contact','result'):
        motion_specs.finite(p.get(name),offset,offset+duration-1/30,name+' anchor')
    if not p['target']<=p['contact']<p['result'] or offset+duration-p['result']<.7:raise ValueError('Retain target → actual contact → readable result hold of at least 0.7s')
    for name in ('target_roi','result_roi'):
        box=p.get(name)
        if not isinstance(box,list) or len(box)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in box) or min(box[:2])<0 or min(box[2:])<2 or box[0]+box[2]>a['width'] or box[1]+box[3]>a['height']:raise ValueError('Proof ROI outside current source')
    if not isinstance(p.get('contact_point'),list) or len(p['contact_point'])!=2:raise ValueError('Bind the actual contact point')
    x,y=p['contact_point']
    if not all(type(v) in (int,float) and math.isfinite(v) for v in (x,y)) or not 0<=x<a['width']-12 or not 0<=y<a['height']-12:raise ValueError('Contact point outside source')
    p.update(source_sha256=media.sha(a['path']),duration=a['duration']);return p

def build(ws,job,host,beat,params):
    start=round(float(beat['start'])*30)/30;end=round(float(beat['end'])*30)/30
    if beat['role'] not in ROLES or not 0<=start<end<=host['duration']+.001 or not 1<=end-start<=30:raise ValueError('Choose a 1–30s current-episode beat')
    if beat['role']=='hook' and (start!=0 or end>3):raise ValueError('Hook audition uses the actual first 0–3 seconds')
    title=motion_specs.clean_text(beat['title']);quote=lib.text(beat['quote'],2000)
    if beat['role']=='cta' and not re.search(r'đăng ký|theo dõi|subscribe|follow|link|liên hệ|mua',quote,re.I):raise ValueError('CTA must be present in the supplied current take/script')
    proof=_proof(ws,beat,end-start) if beat.get('proof') else None
    if beat.get('requires_proof') and not proof:title=motion_specs.clean_text('MINH HỌA · '+title)
    plan=dict(type='demo' if beat['role']=='demo' else 'introduction',kind='animation_spec',title=title,source_quote=quote,items=[],
              at=start,duration=end-start,passage_ids=[beat['id']],intro_layout='host',motion_style='balanced',
              narration_status='recorded_words_unverified',evidence=proof,position='top',intensity=.5,sound='none')
    ctx,at=motion_storyboard.context(plan,host,ws.data['assets'],job.get('transcript'))
    if abs(at-start)>1/60:raise ValueError('Observed speech/proof suggests a different binding. Adjust the beat explicitly before comparing')
    if not proof:
        # A clearly explanatory headline remains above the protected face/captions.
        ctx.update(request='intro',layout_requirement='host',required_texts=[title])
    framing=None
    if proof and proof.get('framing')=='control_result_cuts':
        import demo_framing
        a=ws.data['assets'][proof['asset']];framing=demo_framing.bind(proof,a,end-start)
        for anchor in ctx['anchors']:
            roi=proof['target_roi'] if anchor['kind']=='control' else proof['result_roi'] if anchor['kind']=='result' else [*proof['contact_point'],12,12]
            anchor['roi']=demo_framing.map_roi(framing,roi,anchor['frame'])
    if params['control_at_contact'] and proof:
        target=next(a for a in ctx['anchors'] if a['kind']=='control');contact=next(a for a in ctx['anchors'] if a['kind']=='contact')
        target.update(frame=contact['frame'],source_pts=contact['source_pts'])
    spec=motion_specs.rules(ctx)
    for obj in spec['objects']:
        marker=obj['component'] in ('11','12','13');t=params['treatment'];n=params['entrance_frames']
        if not marker:obj.update(theme=params['theme'],box_style=params['box_style'],font_size=params['font_size'],**params['palette'])
        first=dict(frame=0,x=0,y=0,scale=1,opacity=1,ease='linear');last={**first,'frame':1}
        if t=='fade':first['opacity']=0;last.update(frame=n,ease='smoothstep')
        elif t=='slide':
            first.update(opacity=0,x=0 if marker else -.018);last.update(frame=n,ease='ease_out')
            if marker:last['frame']=min(30,n*2)
        obj['keyframes']=[first,last]
        if obj['component']=='12':obj['keyframes']=[{**first,'opacity':1,'x':0},{**last,'frame':1}]
        if marker:
            anchors={a['id']:a for a in ctx['anchors']}
            budget=motion_specs.lifetime_end(obj,ctx)-motion_specs.object_start(obj,anchors)-obj.get('exit_frames',6)-12
            if budget>=1:obj['keyframes'][-1]['frame']=min(obj['keyframes'][-1]['frame'],budget)
    for sound in spec.get('sfx',[]):sound['gain_db']=params['sfx_gain_db']
    if not params['sfx_enabled']:spec['sfx']=[]
    if not params['effects_enabled']:
        ctx.pop('required_texts',None);spec.update(scene_type='hold',objects=[],sfx=[],evidence='real_screen' if proof else 'presenter')
    spec,compiled=motion_specs.compile_spec(spec,ctx)
    entry=dict(id='series-'+beat['id'],context_version=motion_storyboard.CONTEXT_VERSION,context=ctx,spec=spec,compiler=compiled,model=dict(mode='rules',version=RULE_VERSION,weights_loaded=False),source_start=start,source_end=start+ctx['frames']/30,source_asset=host['id'])
    base,_=planner.build(host,job['settings'],ws.data['assets']);base.update(keep=[[start,end]],proof=[],events=[],punches=[],motion_specs=[entry])
    base['captions']=[[[max(start,a),min(end,b),w] for a,b,w in page if a<end and b>start] for page in base['captions']]
    base['captions']=[p for p in base['captions'] if p]
    if proof:
        a=ws.data['assets'][proof['asset']];base['proof']=[dict(id='series-proof',file=a['path'],source_start=proof['offset'],start=start,end=end,
                           anchors={k:proof[k] for k in ('target','contact','result','target_roi','result_roi')},demonstrates=beat.get('subject',title),visual_claim=beat.get('claim',quote))]
        if framing:base['proof'][0]['framing']=framing
    base['events']=motion_render.sound_events(entry)
    for event in base['events']:
        if event['kind']=='contact':event['sound'].update(offset_frames=params['contact_offset_frames'],offset_reason='Explicit series/scene cue policy' if params['contact_offset_frames'] else '')
    existing_music=base.get('music',{})
    base['music']={**existing_music,'gain_db':params['music_gain_db']} if existing_music.get('mode')=='my_track' else {**existing_music,'mode':params['music_mode'],'track':params['music_track'],'gain_db':params['music_gain_db']}
    base['style']=params['caption_style'];base['series_transition']=dict(kind='hard_cut',overlap_frames=0,enter_frame=round(start*30),settle_frame=round(start*30)+params['entrance_frames'])
    return base,entry

def render_round(ws,b):
    started=time.monotonic()
    with ws.lock:
        s,p=lib.preset(ws,b['style'],b.get('preset_version'));s=copy.deepcopy(s);locked_params=copy.deepcopy(p)
        job=copy.deepcopy(ws.data['jobs'][b['job']]);host=copy.deepcopy(ws.data['assets'][b['job']]);ws.evaluation_access.asset(host)
        ws.artifacts._check_job(job)
        if b['revision']!=job['revision']:raise Conflict('Episode revision changed')
        if b.get('style_revision',s['revision'])!=s['revision']:raise lib.StudioConflict(dict(current_revision=s['revision'],proposed=b,current=s['draft']))
        if not job['settings']['script'].strip():raise ValueError('Attach the current recording script')
        reference=[m for m in s['moments'] if not m['ignored']]
        if not reference and b.get('require_reference',True):raise ValueError('Select and save at least one permitted reference moment')
        if b.get('reference_recipe') is True and not b.get('preset_version'):
            p=lib.params({**p,**reference[-1].get('recipe_proposal',{})})
        for m in reference:
            a=ws.data['assets'][m['asset']];lib.permission(ws,a,'analysis')
            if media.sha(a['path'])!=m['source_sha256']:raise Conflict('Reference moment changed')
        beat=copy.deepcopy(b['beat']);axis=b.get('axis','visual')
        if axis not in ('visual','audio'):raise ValueError('Compare one supported axis')
        prior=[r for r in lib.migrate(ws)['rounds'].values() if r['style']==s['id'] and r['job']==job['id'] and r['beat']['id']==beat['id'] and r.get('choices') and r['choices'][-1]['choice'] in r['variants']]
        prior.sort(key=lambda r:r['choices'][-1].get('created',0))
        if prior:
            last=prior[-1];chosen=last['variants'][last['choices'][-1]['choice']];p=lib.params(chosen['params'])
        else:
            p=lib.params({**p,**p['role_params'].get(beat['role'],{})})
            p['treatment']=p['role_treatments'].get(beat['role'],p['treatment'])
        locks=[]
        if b.get('preset_version'):
            version=next(v for v in s['versions'] if v['version']==b['preset_version']);locks=version.get('locked_fields',[])
            p=lib.params({**p,**{k:locked_params[k] for k in locks}})
        if b.get('scene_patch'):
            if any(k in locks and v!=locked_params[k] for k,v in b['scene_patch'].items()):raise ValueError('Scene request changes a locked preset property; fork or version the preset explicitly')
            p=lib.params({**p,**b['scene_patch']})
        source_sha=media.sha(host['path']);revision=job['revision'];key=uuid.uuid4().hex
    variants={};plans={};excluded=[];seen=set();metrics=[];runtime=runtime_identity()
    treatments=[p['treatment']]+[t for t in p['allowed_treatments'] if t!=p['treatment']]
    options=[{**p,'treatment':t} for t in treatments[:3]] if axis=='visual' else [{**p,'sfx_gain_db':max(-48,p['sfx_gain_db']+delta)} for delta in (0,-3,-6)]
    options=[o for o in options if all(o[k]==locked_params[k] for k in locks)]
    for i,option in enumerate(options):
        label='ABC'[i]
        try:
            plan,entry=build(ws,job,host,beat,option)
            identity=digest(plan)
            if identity in seen:excluded.append(dict(slot=label,reason='No distinct eligible treatment under current locks'));continue
            seen.add(identity)
            boundary=request_payload(s,locked_params,dict(beat=beat,source_sha256=source_sha,moments=reference,trial_params=option),b.get('feedback'))
            dependencies=[dict(sha256=media.sha(ws.data['assets'][m['asset']]['path'])) for m in reference]
            cachekey=digest([RULE_VERSION,media.sha(__file__),runtime,source_sha,plan,dependencies])
            folder=ws.root/'series-cache'/'renders'/cachekey;hit=(folder/'receipt.json').exists()
            wall=time.monotonic()
            if hit:
                rec=json.loads((folder/'receipt.json').read_text(encoding='utf8'))
                if media.sha(folder/'edit.mp4')!=rec['sha256']:raise Conflict('Cached render identity changed')
            else:
                if folder.exists():folder=folder.with_name(cachekey+'-'+uuid.uuid4().hex[:8])
                folder.mkdir(parents=True);shutil.copytree(Path(__file__).parent/'fonts',folder/'fonts')
                media.write_json(folder/'request.json',boundary);media.write_json(folder/'plan.json',plan)
                edit.render(Path(host['path']),plan,folder,scene_preview=True)
                rec=dict(sha256=media.sha(folder/'edit.mp4'),source_sha256=source_sha,engine='existing native spec + FFmpeg',engine_version=RULE_VERSION,
                         renderer_sha256=media.sha(Path(edit.__file__)),frames=round((beat['end']-beat['start'])*30),review='NEEDS_REVIEW',listening='UNVERIFIED')
                media.write_json(folder/'receipt.json',rec)
            measured=dict(slot=label,cache_hit=hit,render_calls=0 if hit else 1,elapsed_seconds=time.monotonic()-wall,cache_bytes=sum(f.stat().st_size for f in folder.iterdir() if f.is_file()),peak_memory_bytes=None)
            variants[label]=dict(label=label,params=option,relative_folder=str(folder.relative_to(ws.root)),sha256=rec['sha256'],
                why=('Lựa chọn hiện tại / gần preset nhất' if label=='A' else 'Chỉ đổi '+axis+'; '+option['treatment'] if axis=='visual' else 'Chỉ giảm cue '+str(option['sfx_gain_db'])+' dB'),
                spec=entry['spec'],context=entry['context'],request_receipt={k:v for k,v in boundary.items() if k not in ('prefix','suffix')},metrics=measured,
                url='/series-media/'+key+'/'+label+'/mp4',voice_url='/series-media/'+key+'/'+label+'/voice',sfx_url='/series-media/'+key+'/'+label+'/sfx')
            plans[label]=plan;metrics.append(measured)
        except (ValueError,PermissionError) as e:excluded.append(dict(slot=label,reason=str(e)))
    if not variants:raise ValueError('No eligible rendered variant: '+json.dumps(excluded,ensure_ascii=False))
    with ws.lock:
        if ws.data['jobs'][job['id']]['revision']!=revision or media.sha(host['path'])!=source_sha or lib.migrate(ws)['styles'][s['id']]['revision']!=s['revision']:raise Conflict('Source/style changed while rendering; outputs retained but not applied')
        r=dict(id=key,style=s['id'],style_revision=s['revision'],preset_version=b.get('preset_version'),job=job['id'],revision=revision,source_sha256=source_sha,script_sha256=digest(job['settings']['script']),
               beat=beat,axis=axis,variants=variants,plans=plans,excluded=excluded,choices=[],reference=reference,created=time.time(),status='NEEDS_REVIEW',
               pickup=(beat.get('pickup') or 'Quay mục tiêu → thao tác → kết quả cho: '+beat['quote']) if beat.get('requires_proof') and not beat.get('proof') else None,
               comparison='Same recording/cut/narration/captions; '+axis+' axis only',elapsed_seconds=time.monotonic()-started)
        lib.migrate(ws)['rounds'][key]=r;lib.migrate(ws)['metrics'].extend(metrics);ws.save()
    return {k:v for k,v in r.items() if k!='plans'}

def current_round(ws,r,job):
    selection=job.get('series_selection',{});script=digest(job['settings'].get('script','')) if job.get('settings') else None
    linked=selection.get('revision')==job['revision'] and any(s['round']==r['id'] for s in selection.get('scenes',[])) and selection.get('source_script_sha256')==script
    if job['revision']!=r['revision'] and not linked:raise Conflict('Episode changed; rebind this trial')
    if r.get('script_sha256') and r['script_sha256']!=script:raise Conflict('Script changed; rebind this trial')
    if media.sha(ws.data['assets'][r['job']]['path'])!=r['source_sha256']:raise Conflict('Recording changed; rebind this trial')

def select(ws,b):
    with ws.lock:
        root=lib.migrate(ws);r=root['rounds'][b['round']];job=ws.data['jobs'][r['job']]
        current_round(ws,r,job)
        choice=b['choice'];scope=b.get('scope','scene')
        if choice not in (*r['variants'],'reject_all','abstain') or scope not in ('scene','style'):raise ValueError('Choose a rendered candidate, reject all or abstain and an explicit scope')
        kind=b.get('reviewer_kind','agent')
        if kind not in ('human','agent','test','auto'):raise ValueError('Declare actual reviewer kind')
        feedback=dict(id=uuid.uuid4().hex,round=r['id'],style=r['style'],creator=root['styles'][r['style']]['creator'],job=r['job'],beat=r['beat']['id'],role=r['beat']['role'],choice=choice,scope=scope,
                      note=b.get('note',''),reviewer=lib.text(b['reviewer'],120),reviewer_kind=kind,consent_train=b.get('consent_train') is True,created=time.time(),axis=r['axis'],
                      positive_target=choice in r['variants'] and kind=='human',attribution='Whole declared treatment only; not causal attribution to individual parameters')
        if scope=='style' and choice in r['variants']:
            s=root['styles'][r['style']]
            if b.get('style_revision')!=s['revision']:raise lib.StudioConflict(dict(current_revision=s['revision'],proposed=b,current=s['draft']))
        root['feedback'].append(feedback)
        if choice in r['variants']:
            r['choices'].append(feedback)
            if scope=='style':
                s=root['styles'][r['style']]
                p=copy.deepcopy(s['draft']);p['role_treatments'][r['beat']['role']]=r['variants'][choice]['params']['treatment']
                roles=copy.deepcopy(s['draft'].get('role_params',{}));roles[r['beat']['role']]={k:v for k,v in r['variants'][choice]['params'].items() if k not in ('role_params','role_treatments')}
                lib.update(ws,dict(style=s['id'],revision=s['revision'],patch={'role_treatments':p['role_treatments'],'role_params':roles}))
        ws.save();return dict(feedback=feedback,preset_changed=scope=='style' and choice in r['variants'],training_started=False)

def parse_feedback(ws,b):
    r=lib.migrate(ws)['rounds'][b['round']];label=b.get('choice') or (r['choices'][-1]['choice'] if r['choices'] else 'A')
    before=lib.params(r['variants'][label]['params']);note=lib.text(b['note'],2000);low=note.casefold();patch={};unsupported=[]
    m=re.search(r'(giảm|tăng)\s+(?:tiếng\s+)?click\s+(\d+(?:[.,]\d+)?)\s*d\s*b',low)
    if m:patch['sfx_gain_db']=before['sfx_gain_db']+(-1 if m[1]=='giảm' else 1)*float(m[2].replace(',','.'))
    if 'viền' in low and ('chạm' in low or 'click' in low):patch['control_at_contact']=True
    if 'tắt hiệu ứng' in low or 'bỏ hiệu ứng' in low:patch.update(effects_enabled=False,sfx_enabled=False)
    if 'màu tối' in low:patch['theme']='charcoal'
    if 'màu sáng' in low:patch['theme']='paper'
    if 'giữ zoom' in low:unsupported.append('Camera zoom không thuộc native marker này; giữ variant đã chọn, hoặc dùng demo-focus với crop/anchor của tập hiện tại.')
    if 'preset' in low or 'toàn bộ' in low:unsupported.append('Yêu cầu vượt scene: chọn scope style rõ ràng; patch này chưa ghi preset.')
    if not patch:unsupported.append('Chưa nhận được patch thuộc grammar hỗ trợ; hãy dùng các trường tham số hoặc mô tả cụ thể hơn.')
    after=lib.params({**before,**patch})
    return dict(round=r['id'],choice=label,scope='scene',patch=patch,before=before,after=after,diff={k:dict(before=before[k],after=v) for k,v in patch.items()},
                unresolved=unsupported,note=note,applied=False,next_action='Review diff, then explicitly render the scene patch; preset is unchanged')

def apply_choices(ws,b):
    with ws.lock:
        ids=b['rounds'];root=lib.migrate(ws);rounds=[root['rounds'][i] for i in ids]
        if not rounds or len({r['job'] for r in rounds})!=1:raise ValueError('Choose rounds from one episode')
        job=ws.data['jobs'][rounds[0]['job']];ws.artifacts._check_job(job)
        if b['revision']!=job['revision']:raise Conflict('Current episode revision changed')
        selected=[]
        for r in rounds:
            current_round(ws,r,job)
            if not r['choices']:raise ValueError('Choose a candidate first')
            chosen=r['variants'][r['choices'][-1]['choice']];plan=r['plans'][chosen['label']];entry=copy.deepcopy(plan['motion_specs'][0]);
            if any(entry['source_start']<old['source_end'] and entry['source_end']>old['source_start'] for old in selected):raise ValueError('Chosen scene ranges overlap; resolve before assembly')
            selected.append(entry)
        before=copy.deepcopy(job.get('series_selection'))
        job['series_selection']=dict(rounds=ids,source_sha256=rounds[0]['source_sha256'],source_script_sha256=digest(job['settings']['script']),revision=job['revision']+1,
                                     scenes=[dict(round=r['id'],choice=r['choices'][-1]['choice']) for r in rounds],previous=before)
        job.update(revision=job['revision']+1,status='Draft',stage='Series choices applied. Render a new master; review remains pending.');ws.save()
        return dict(job=job['id'],revision=job['revision'],master_render_required=True,pickups=[r['pickup'] for r in rounds if r['pickup']])

def assemble(ws,key,plan):
    for i,requirement in enumerate(ws.data['jobs'][key].get('auto_requirements',[])):
        plan.setdefault('capture_requirements',[]).append(dict(id='auto-pickup-'+str(i),subject=requirement.get('quote','Demo'),claim=requirement.get('quote',''),intended_visual=requirement['pickup']))
    selection=ws.data['jobs'][key].get('series_selection')
    if not selection:return
    job=ws.data['jobs'][key]
    if selection['source_sha256']!=media.sha(ws.data['assets'][key]['path']) or selection['source_script_sha256']!=digest(job['settings']['script']):raise Conflict('Recording/script changed: rebind series scenes to the current episode')
    for choice in selection['scenes']:
        r=lib.migrate(ws)['rounds'][choice['round']];p=r['plans'][choice['choice']];entry=copy.deepcopy(p['motion_specs'][0])
        if any(entry['source_start']<old['source_end'] and entry['source_end']>old['source_start'] for old in plan.get('motion_specs',[])):raise ValueError('Series/native scenes overlap; keep one controller per property')
        for moment in r['reference']:lib.permission(ws,ws.data['assets'][moment['asset']],'analysis')
        if r['beat'].get('proof'):_proof(ws,r['beat'],r['beat']['end']-r['beat']['start'])
        if any(entry['source_start']<q['end'] and entry['source_end']>q['start'] for q in plan['proof']):raise ValueError('Existing cutaway overlaps series scene; explicitly choose one before assembly')
        plan.setdefault('motion_specs',[]).append(entry);plan['proof'].extend(copy.deepcopy(p['proof']));plan['events'].extend(copy.deepcopy(p['events']))
        if r['pickup']:plan.setdefault('capture_requirements',[]).append(dict(id='series-pickup-'+r['id'],subject=r['beat'].get('subject',r['beat']['title']),claim=r['beat']['quote'],intended_visual=r['pickup']))
    plan['series_selection']=copy.deepcopy(selection)

def validate_release(ws,key):
    if ws.data['jobs'][key].get('auto_requirements'):raise ValueError('Chưa được bàn giao: còn demo cần quay bổ sung')
    if ws.data['assets'].get(key,{}).get('technical_fixture'):raise ValueError('Technical fixtures cannot receive customer-master approval')
    selection=ws.data['jobs'][key].get('series_selection')
    if not selection:return
    for choice in selection['scenes']:
        r=lib.migrate(ws)['rounds'][choice['round']]
        if r['pickup']:raise ValueError('Chưa được bàn giao: '+r['pickup'])
        if r['beat'].get('proof'):_proof(ws,r['beat'],r['beat']['end']-r['beat']['start'])

def reference_path(ws,asset_id,mode):
    a=ws.data['assets'][asset_id];lib.permission(ws,a,'output' if mode=='proof' else 'analysis')
    if mode=='proof' and a.get('series_rights',{}).get('listen') is True:lib.permission(ws,a,'listen');return Path(a['path'])
    if mode=='mix':lib.permission(ws,a,'listen');return Path(a['path'])
    if mode not in ('silent','proof'):raise ValueError('Unknown reference playback mode')
    folder=ws.root/'series-cache'/'reference-proxies';folder.mkdir(parents=True,exist_ok=True)
    file=folder/(digest([media.sha(a['path']),'silent-proxy-v1'])+'.mp4')
    with ws.archive_lock:
        if not file.exists():media.ff('-i',a['path'],'-an','-vf','scale=360:-2','-c:v','libx264','-preset','veryfast','-crf','25','-movflags','+faststart',file)
    return file

def training_export(ws,b):
    root=lib.migrate(ws);style=root['styles'][b['style']];rows=[];excluded=[]
    for f in root['feedback']:
        if f['style']!=style['id']:continue
        if not f['positive_target'] or not f['consent_train']:excluded.append(dict(id=f['id'],reason='No human positive target + explicit training consent'));continue
        r=root['rounds'][f['round']];assets=[ws.data['assets'][r['job']]]+[ws.data['assets'][m['asset']] for m in r['reference']]
        try:
            for a in assets:lib.permission(ws,a,'train')
        except PermissionError:excluded.append(dict(id=f['id'],reason='Source training permission missing'));continue
        v=r['variants'][f['choice']];folder=ws.root/v['relative_folder']
        if media.sha(folder/'edit.mp4')!=v['sha256']:raise Conflict('Training render changed')
        rows.append(dict(id=f['id'],source_group=ws.data['jobs'][r['job']].get('source_family',r['source_sha256']),reference_groups=[m['source_sha256'] for m in r['reference']],
                         creator=style['creator'],input=copy.deepcopy(v['context']),target=copy.deepcopy(v['spec']),source_sha256=r['source_sha256'],render_sha256=v['sha256'],
                         annotation_scope='editor_confirmed',editor_confirmed=True,created=f['created']))
    # Connected recording/reference families stay together; no sealed material is read.
    groups=[]
    for row in rows:
        keys={row['source_group'],row['source_sha256'],*row['reference_groups']};matches=[g for g in groups if g['keys']&keys]
        if matches:
            group=matches[0];group['keys']|=keys;group['rows'].append(row)
            for other in matches[1:]:group['keys']|=other['keys'];group['rows']+=other['rows'];groups.remove(other)
        else:groups.append(dict(keys=keys,rows=[row]))
    groups.sort(key=lambda g:digest(sorted(g['keys'])))
    status='READY_FOR_EXPERIMENT' if len(groups)>=6 else 'INSUFFICIENT_INDEPENDENT_REVIEWED_GROUPS'
    for i,g in enumerate(groups):
        split='train' if i<max(1,int(len(groups)*.65)) else 'validation' if i<len(groups)-1 else 'sealed_final'
        for row in g['rows']:row['split']=split
    out=ws.root/'series-learning'/uuid.uuid4().hex;out.mkdir(parents=True)
    for split in ('train','validation','sealed_final'):media.write_json(out/(split+'.json'),[r for r in rows if r['split']==split])
    receipt=dict(status=status,rows=len(rows),independent_groups=len(groups),excluded=excluded,dataset_fingerprint=digest(rows),training_started=False,
                 adapter_promoted=False,baseline='native rules + scoped past preference retrieval',runtime='optional existing Qwen/PEFT worker; no new model dependency',
                 unknown_measurements=['peak RAM/VRAM','blind episode preference','editor repair time'],split_policy='connected source/reference families; sealed final never read by studio retrieval',relative_folder=str(out.relative_to(ws.root)))
    media.write_json(out/'receipt.json',receipt);root['training_jobs'].append(receipt);ws.save();return receipt

def media_path(ws,round_id,label,kind):
    r=lib.migrate(ws)['rounds'][round_id];v=r['variants'][label];host=ws.data['assets'][r['job']];ws.evaluation_access.asset(host)
    folder=(ws.root/v['relative_folder']).resolve();folder.relative_to((ws.root/'series-cache'/'renders').resolve())
    if media.sha(folder/'edit.mp4')!=v['sha256']:raise Conflict('Preview file changed')
    file=folder/{'mp4':'edit.mp4','voice':'voice.wav','sfx':'sfx.wav','music':'music.wav'}[kind]
    if not file.is_file():raise ValueError('Requested bus is unavailable; use the full mix')
    return file

def dispatch(ws,action,b):
    calls={'rights':lib.set_rights,'create':lib.create,'update':lib.update,'freeze':lib.freeze,'moment':reference_moments.save,'excerpt':reference_moments.excerpt,
           'compare':render_round,'select':select,'feedback':parse_feedback,'apply':apply_choices,'training-export':training_export}
    if action=='scan':return reference_moments.scan(ws,b)
    if action=='episode':return episode(ws,b)
    if action not in calls:raise ValueError('Unknown series action')
    return lib.request(ws,b,lambda:calls[action](ws,b))
