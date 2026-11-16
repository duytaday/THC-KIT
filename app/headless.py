"""Deterministic headless batch service over the existing Workspace/renderer/QC."""
import copy,contextlib,json,os,re,shutil,sys,time,uuid
from pathlib import Path
from engine import media
from assignments import match_scripts,stem
from revisions import Conflict,digest
import series_library as lib,series_studio as studio

VERSION='headless-1'
VIDEO={'.mp4','.mov','.mkv','.m4v','.webm'}
ACTIONS={'export_video':('xuất video','xuất file','export video','export file','render video'),
         'add_subtitles':('phụ đề','subtitle','caption'), 'save':('lưu thay đổi','save changes','bấm save'),
         'open_file':('mở file','open file')}

def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def absolute(value,base):
    p=Path(value).expanduser();return p.resolve() if p.is_absolute() else (Path(base)/p).resolve()
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8');os.replace(temp,path)
def is_under(path,parent):
    try:Path(path).resolve().relative_to(Path(parent).resolve());return True
    except ValueError:return False

def scan(directory,excluded=()):
    root=Path(directory).resolve(strict=True);files=[];skipped=[]
    for here,dirs,names in os.walk(root,followlinks=False):
        kept=[]
        for name in dirs:
            p=Path(here)/name
            if name in ('.git','.codex','node_modules','exports','outputs','cache','series-cache') or p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) or any(is_under(p,e) for e in excluded):skipped.append(str(p))
            elif is_under(p,root):kept.append(name)
        dirs[:]=kept
        for name in names:
            p=Path(here)/name
            if p.suffix.casefold() in VIDEO and not p.is_symlink() and not any(is_under(p,e) for e in excluded):files.append(p.resolve())
    return sorted(files,key=lambda p:str(p).casefold()),skipped

def component_catalog(value):
    if not value:return []
    p=Path(value).resolve();file=p/'catalog.json' if p.is_dir() else p
    if not file.exists():return []
    doc=load(file);rows=doc if isinstance(doc,list) else doc.get('components',[]);result=[]
    for row in rows:
        r=copy.deepcopy(row)
        if not isinstance(r,dict) or not isinstance(r.get('id'),str):raise ValueError('Each component needs an ID')
        if r.get('file'):r['file']=str(absolute(r['file'],file.parent))
        r['catalog_file']=str(file);result.append(r)
    if len({r['id'] for r in result})!=len(result):raise ValueError('Component IDs must be unique')
    return result

def style_config(request,ws=None):
    selected=request.get('preset') or request.get('template')
    if not selected:raise ValueError('Choose --preset or --template')
    path=Path(selected)
    if path.is_file():
        doc=load(path);p=doc.get('params',doc.get('defaults',{}));kind='template' if request.get('template') else 'preset'
        p=lib.params(p);locks=doc.get('locked_fields',list(p))
        if not isinstance(locks,list) or any(not isinstance(k,str) or k not in lib.DEFAULT for k in locks):raise ValueError('locked_fields must name supported preset properties')
        if type(doc.get('version',1)) is not int or doc.get('version',1)<1:raise ValueError('Preset version must be a positive integer')
        return dict(name=doc.get('name',path.stem),version=doc.get('version',1),params=p,sha256=media.sha(path),file=str(path.resolve()),kind=kind,
                                  creator=doc.get('creator','local-creator'),series=doc.get('series','headless'),template=doc.get('template'),reference_moments=doc.get('moments',[]),
                                  locked_fields=locks,model_requested=doc.get('model','rules'),approval='Imported settings; no new human approval inferred')
    if ws:
        matches=[s for s in lib.migrate(ws)['styles'].values() if s['name'].casefold()==str(selected).casefold()]
        if len(matches)==1 and matches[0]['versions']:
            s=matches[0];v=s['versions'][-1];_,p=lib.preset(ws,s['id'],v['version'])
            return dict(name=s['name'],version=v['version'],params=p,sha256=v['sha256'],kind='workspace_preset',style=s['id'],creator=s['creator'],series=s['series'],locked_fields=v['locked_fields'])
    raise ValueError('Preset/template file or unique saved preset name not found: '+str(selected))

def plan(request,ws=None):
    inputs=Path(request['inputs']).resolve(strict=True);out=Path(request['out']).resolve();workspace=Path(request['workspace']).resolve()
    if inputs==out or is_under(inputs,out):raise ValueError('Outputs must be a distinct directory, not an ancestor of inputs')
    excluded=[out,workspace]
    if request.get('components') and Path(request['components']).is_dir():excluded.append(Path(request['components']).resolve())
    if ws:
        excluded += [Path(r['request']['out']) for r in ws.data.get('auto_runs',{}).values()]
    recordings,skipped=scan(inputs,excluded);components=component_catalog(request.get('components'))
    component_paths={str(Path(c['file']).resolve()) for c in components if c.get('file')}
    recordings=[p for p in recordings if str(p) not in component_paths]
    manifest=Path(request['manifest']) if request.get('manifest') else inputs/'thc-manifest.json'
    declared=[]
    if manifest.is_file():
        doc=load(manifest)
        for e in doc.get('episodes',[]):
            e=copy.deepcopy(e)
            if not e.get('recording'):raise ValueError('Episode manifest needs recording path')
            e['recording']=str(absolute(e['recording'],manifest.parent))
            if e.get('script'):e['script']=str(absolute(e['script'],manifest.parent))
            e['mapping_basis']='creator_manifest';declared.append(e)
        if doc.get('components'):
            # Inline component paths use this manifest's directory, independently of caller CWD.
            for c in doc['components']:
                c=copy.deepcopy(c)
                if c.get('file'):c['file']=str(absolute(c['file'],manifest.parent))
                c['catalog_file']=str(manifest);components.append(c)
    if ws:
        for c in ws.data.get('personal_components',{}).values():
            c=copy.deepcopy(c);a=ws.data['assets'].get(c.get('asset'))
            if a:c.update(file=a['path'],rights=a.get('series_rights',{}),pinned=c['id'] in ws.data.get('selected_components',[]));components.append(c)
    duplicates={c['id'] for c in components if sum(x['id']==c['id'] for x in components)>1}
    for c in components:
        if c['id'] in duplicates:c['index_issue']='Duplicate component ID; clarify which source/version is intended'
    episodes=declared or [dict(recording=str(p),id=p.stem+'-'+digest(str(p))[:8],mapping_basis='unique_filename') for p in recordings]
    ids=[str(e.get('id') or Path(e['recording']).stem) for e in episodes]
    if len(set(ids))!=len(ids):raise ValueError('Episode IDs must be unique; duplicate filenames need distinct manifest IDs')
    scripts=[]
    if request.get('scripts'):
        directory=Path(request['scripts']);paths=[directory] if directory.is_file() else sorted(p for p in directory.rglob('*') if p.suffix.casefold() in ('.srt','.txt') and p.is_file() and not p.is_symlink())
        scripts=[dict(name=p.name,text=p.read_text(encoding='utf-8-sig'),path=str(p.resolve())) for p in paths]
    pseudo={key:dict(id=key) for key in ids};assets={key:dict(name=Path(e['recording']).name) for key,e in zip(ids,episodes)}
    assigned,ambiguous=match_scripts(pseudo,assets,ids,scripts) if scripts else ([],[]);matched=dict(assigned)
    config=style_config(request,ws);rows=[]
    for key,e in zip(ids,episodes):
        row={**e,'id':key,'issues':[],'input_path':e['recording'],'preset':dict(name=config['name'],version=config['version'],sha256=config['sha256'])}
        source=Path(e['recording'])
        if not source.is_file() or source.suffix.casefold() not in VIDEO:row['issues'].append('Recording is missing or unsupported')
        else:
            try:
                v=media.stream(source,'video');media.stream(source,'audio');row.update(source_sha256=media.sha(source),duration=media.duration(v),width=v['width'],height=v['height'])
            except (ValueError,KeyError) as error:row['issues'].append(str(error))
        if e.get('takes'):row['issues'].append('Multi-take assembly is not supported by this command yet. Supply the explicitly selected take as recording and remove takes, or assemble a source EDL first; no take was discarded.')
        script=e.get('script');confirmed=(ws.data.get('auto_mappings',{}).get(str(source.resolve()),{}) if ws else {})
        if not script and confirmed.get('source_sha256')==row.get('source_sha256') and confirmed.get('script_path'):script=confirmed['script_path'];row['mapping_basis']='confirmed_mapping'
        if script:
            try:row.update(script_path=str(Path(script).resolve(strict=True)),script_text=Path(script).read_text(encoding='utf-8-sig'))
            except (OSError,UnicodeError):row['issues'].append('Declared script is unavailable or not UTF-8')
        elif key in matched:row.update(script_path=matched[key]['path'],script_text=matched[key]['text'])
        elif request.get('allow_transcribe'):row.update(script_path=None,script_text=None,script_origin='recording_transcript_requested')
        else:row['issues'].append('Script mapping is ambiguous or missing; provide manifest mapping or --allow-transcribe')
        if row.get('script_text'):row['script_sha256']=digest(row['script_text']);row.setdefault('script_origin','creator_supplied')
        rows.append(row)
    return dict(version=VERSION,episodes=rows,components=components,config=config,excluded_directories=skipped,mapping_questions=ambiguous,
                model=dict(actual='rules + workspace-local scoped preference retrieval',adapter_loaded=False,external_provider_called=False),plan_only=request.get('plan_only',False))

def import_file(ws,path,kind,role=None,owner=None):
    path=Path(path).resolve(strict=True);sha=media.sha(path);key=digest([str(path),sha,kind,role,owner]);ledger=ws.data.setdefault('auto_assets',{})
    if key in ledger and ledger[key] in ws.data['assets']:return ledger[key]
    incoming=ws.root/'work'/('intake-'+uuid.uuid4().hex+path.suffix);shutil.copyfile(path,incoming)
    asset=ws.import_asset(incoming,path.name,kind,source_role=role,owners=[owner] if owner and kind!='host' else ())
    ws.data['assets'][asset]['original_path']=str(path);ledger[key]=asset;ws.save();return asset

def import_style(ws,config):
    if config.get('style'):return config['style'],config['version']
    ledger=ws.data.setdefault('auto_presets',{});key=config['sha256']
    if key in ledger:return ledger[key]['style'],ledger[key]['version']
    s=lib.create(ws,dict(name=config['name'],creator=config['creator'],series=config['series'],params=config['params']))
    v=dict(version=config['version'],params=copy.deepcopy(config['params']),locked_fields=config['locked_fields'],moments=[],approved_by=None,reviewer_kind='imported',aesthetic_approved=False,
           distribution_approved=False,training_approved=False,origin_sha256=config['sha256'],origin_file=config.get('file'),created=time.time())
    v['sha256']=digest(v);lib.migrate(ws)['styles'][s['id']]['versions'].append(v);ledger[key]=dict(style=s['id'],version=v['version']);ws.save();return s['id'],v['version']

def action_for(quote):
    q=quote.casefold();return next((action for action,words in ACTIONS.items() if any(word in q for word in words)),None)

def shortlist(components,role,quote,creator,action=None,episode_id=None):
    eligible=[];excluded=[];words=set(re.findall(r'\w+',quote.casefold()))
    for c in components:
        if c.get('role')!=role:continue
        reasons=[];rights=c.get('rights',{})
        if c.get('index_issue'):reasons.append(c['index_issue'])
        if rights.get('output') is not True:reasons.append('No explicit output permission')
        if c.get('creator') not in (None,creator):reasons.append('Different creator scope')
        if c.get('episodes') and episode_id not in c['episodes']:reasons.append('Different episode scope')
        if not c.get('file') or not Path(c['file']).is_file():reasons.append('Source file unavailable')
        elif c.get('source_sha256') and media.sha(c['file'])!=c['source_sha256']:reasons.append('Changed source bytes; inspect and rebind its observations')
        if role=='screen_recording' and (not action or c.get('demonstrates')!=action):reasons.append('No matching action/result declaration; filenames are not proof')
        if role=='screen_recording' and not c.get('anchors'):reasons.append('Missing observed control/contact/result anchors')
        if c.get('runtime','native')!='native':reasons.append('External runtime is not configured for this source')
        if reasons:excluded.append(dict(id=c['id'],reasons=reasons));continue
        tags=set(re.findall(r'\w+',' '.join(c.get('tags',[]))+' '+c.get('description','').casefold()));score=len(words&tags)
        if role in ('broll','image') and not score:excluded.append(dict(id=c['id'],reasons=['No declared content match']));continue
        eligible.append((score+(100 if c.get('pinned') else 0),c))
    eligible.sort(key=lambda x:(-x[0],x[1]['id']));return [c for _,c in eligible],excluded

def illustration(ws,c,duration,job):
    if c['role']=='image':
        if Path(c['file']).suffix.casefold() not in ('.png','.jpg','.jpeg'):raise ValueError('Image page must be rendered to a cleared PNG/JPEG first')
        folder=ws.root/'series-cache'/'stills';folder.mkdir(parents=True,exist_ok=True);path=folder/(digest([media.sha(c['file']),duration,VERSION])+'.mp4')
        if not path.exists():media.ff('-loop','1','-framerate','30','-i',c['file'],'-t',duration,'-vf','scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2','-an','-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p',path)
        asset=import_file(ws,path,'reference','broll',job);a=ws.data['assets'][asset];a.update(media_is_reusable_proof=False,data_class='reference_excerpt',original_image_sha256=media.sha(c['file']),original_image=c['file'])
    else:asset=import_file(ws,c['file'],'reference','broll',job);a=ws.data['assets'][asset]
    lib.set_rights(ws,dict(asset=asset,source_sha256=a['source_sha256'],revision=a.get('series_rights',{}).get('revision',0),rights={**c['rights'],'train':False},evidence=c.get('permission_evidence','Creator-declared illustration permission; not software proof'),reviewer='Creator manifest declaration'))
    return asset

def prepare_episode(ws,row,config,components):
    if row['issues']:return dict(row=row,blockers=row['issues'])
    key=import_file(ws,row['recording'],'host',owner=row['id']);job=ws.data['jobs'][key];host=ws.data['assets'][key]
    host['technical_fixture']=row.get('technical_fixture') is True
    script=row.get('script_text')
    if script is None:
        if ws.speech_setup.snapshot()['status']!='READY':return dict(row=row,blockers=['Local transcription is not configured; supply this recording’s TXT/SRT or set up local ASR. Other episodes can continue.'])
        import speech
        t=speech.load_or_transcribe(ws.root,host,language=None);script=speech.captions(t['words']);job['transcript']=t
    settings=copy.deepcopy(job['settings']);p=config['params'];settings.update(script=script,style=p['caption_style'],motion_intensity=.35,music_mode='off' if p['music_mode']=='off' else 'auto',music_track=p['music_track'],music_gain_db=p['music_gain_db'],planner_mode='built_in')
    settings.update(copy.deepcopy(job.get('auto_manual_settings',{})))
    settings['inserts']=[q for q in settings['inserts'] if not (q.get('origin')=='auto_edit' and q.get('auto_episode')==row['id'])]
    if settings!=job['settings']:ws.update([key],settings,{key:job['revision']})
    job=ws.data['jobs'][key];job['auto_episode_id']=row['id'];ws.data.setdefault('auto_mappings',{})[str(Path(row['recording']).resolve())]=dict(source_sha256=row['source_sha256'],script_path=row.get('script_path'),script_sha256=digest(script),job=key)
    episode=studio.episode(ws,dict(job=key));beats=copy.deepcopy(row.get('beats') or episode['beats']);decisions=[];selected=[];end=0
    # A sparse editorial baseline preserves A-roll rather than filling every phrase with graphics.
    chosen_roles=set()
    for beat in beats:
        beat=copy.deepcopy(beat);beat.setdefault('quote',next((b['quote'] for b in episode['beats'] if b['start']<=beat['start']<b['end']),''));beat.setdefault('id','beat-'+digest([row['source_sha256'],beat['start'],beat['quote']])[:16])
        beat.setdefault('title',beat['quote'] if len(beat['quote'])<=70 else '')
        beat.setdefault('requires_proof',beat['role']=='demo');beat.setdefault('proof',None)
        if (beat['role'] in chosen_roles and beat['role'] in ('hook','cta','showcase')) or beat['start']<end-.001:continue
        if beat['role'] not in ('hook','demo','cta','showcase','explain'):continue
        if beat['end']-beat['start']<1:continue
        action=beat.get('action') or action_for(beat['quote']);decision=dict(beat=beat['id'],role=beat['role'],quote=beat['quote'],source_range=[beat['start'],beat['end']],why=[],excluded=[])
        decision['sequence_context']=dict(previous_treatment=p['role_treatments'].get(selected[-1]['role'],p['treatment']) if selected else None,previous_camera='steady',demo_importance='high' if beat['role']=='demo' else 'normal')
        manual=[q for q in settings['inserts'] if q.get('origin')!='auto_edit' and q['at']<beat['end'] and q['at']+q['duration']>beat['start']]
        if manual:
            decision.update(fallback='Keep creator-assigned cutaway',assets=[q['asset'] for q in manual]);decision['why'].append('Preserved manual footage placement; no second camera/scene controller was stacked on top.');decisions.append(decision);continue
        if beat['role']=='demo':
            candidates,excluded=shortlist(components,'screen_recording',beat['quote'],config['creator'],action,row['id']);decision['excluded']=excluded
            if beat.get('component'):candidates=[c for c in candidates if c['id']==beat['component']]
            if candidates:
                c=candidates[0];asset=import_file(ws,c['file'],'reference','broll',key);a=ws.data['assets'][asset]
                a['technical_fixture']=c.get('technical_fixture') is True
                lib.set_rights(ws,dict(asset=asset,source_sha256=a['source_sha256'],revision=a.get('series_rights',{}).get('revision',0),rights=c['rights'],evidence=c.get('permission_evidence','Creator manifest explicitly declares usage scope'),reviewer='Creator manifest · declaration, not authenticated identity'))
                proof=copy.deepcopy(c['anchors'])
                proof['asset']=asset;proof.setdefault('offset',0)
                if c.get('framing'):proof['framing']=c['framing']
                if c.get('context_crop'):proof['context_crop']=c['context_crop']
                if c.get('baked_camera'):
                    proof.pop('framing',None);decision['why'].append('Capture already has camera motion; keep it instead of stacking another zoom.')
                if c.get('baked_sfx'):
                    beat.setdefault('scene_patch',{})['sfx_enabled']=False;decision['why'].append('Recorded SFX retained; no second click bus is added.')
                needed=proof['result']-proof['offset']+max(.8,c.get('result_hold_seconds',.8))
                if needed>beat['end']-beat['start']:decision['excluded'].append(dict(id=c['id'],reasons=['Result cannot hold in this spoken scene without consuming its neighbor']))
                beat['proof']=proof;beat['subject']=action;beat['claim']=beat['quote']
                try:
                    if needed>beat['end']-beat['start']:raise ValueError('Readable result would overlap the adjacent spoken scene')
                    studio._proof(ws,beat,beat['end']-beat['start'])
                except (ValueError,PermissionError) as error:decision['excluded'].append(dict(id=c['id'],reasons=[str(error)]));beat['proof']=None
                else:decision.update(component=c['id'],asset=asset,component_sha256=media.sha(c['file']),proof=copy.deepcopy(proof));decision['why'].append('Explicit action '+str(action)+' matches the current script; rights/runtime/anchor/hold gates passed. Visible result still needs human review.')
            if not beat['proof']:
                beat['pickup']='Quay bổ sung cho câu “'+beat['quote']+'”: đúng đối tượng '+str(action or 'trong lời nói')+', mục tiêu xuất hiện → thao tác thật → kết quả đủ lâu để đọc.'
                decision.update(pickup=beat['pickup'],fallback='Presenter + visibly labelled illustration');decision['why'].append('No eligible current-episode proof; draft continues honestly.')
        if beat['role']=='explain':
            videos,v_ex=shortlist(components,'broll',beat['quote'],config['creator'],episode_id=row['id']);images,i_ex=shortlist(components,'image',beat['quote'],config['creator'],episode_id=row['id'])
            candidates=videos+images;decision['excluded']=v_ex+i_ex
            if candidates:
                c=candidates[0];duration=min(4,beat['end']-beat['start']);asset=illustration(ws,c,duration,key);a=ws.data['assets'][asset];duration=min(duration,a['duration'])
                settings['inserts'].append(dict(id='auto-'+row['id']+'-'+beat['id'],asset=asset,at=beat['start'],offset=c.get('offset',0),duration=duration,origin='auto_edit',auto_episode=row['id']))
                decision.update(component=c['id'],asset=asset,component_sha256=media.sha(c['file']),source_range=[beat['start'],beat['start']+duration],illustration=True)
                decision['why'].append('Cleared declared tags match this spoken explanation; illustration only, not action/result proof.')
                decisions.append(decision);chosen_roles.add('explain');end=beat['end'];continue
        if beat['end']>host['duration']:beat['end']=host['duration']
        beat['start']=round(beat['start']*30)/30;beat['end']=round(beat['end']*30)/30
        if not beat['title']:
            words=beat['quote'].split()[:9]
            while words and len(' '.join(words))>60:words.pop()
            beat['title']=' '.join(words)
            if not beat['title']:decision['why'].append('No short label available; keep presenter and defer the graphic');decisions.append(decision);continue
            decision['why'].append('Short title copied from this spoken phrase; no new claim was invented.')
        decision['source_range']=[beat['start'],beat['end']];decision['beat_binding']=beat;decision['why'].append('Use the locked native style for this current spoken beat; keep original voice/captions and a hard cut, with no extra camera controller.')
        selected.append(beat);decisions.append(decision);end=beat['end'];chosen_roles.add(beat['role'])
    # Optional cleared logo and music are independent factual assets, not learned style changes.
    optional=[]
    for role in ('logo','music'):
        if role=='music' and (p['music_mode']=='off' or set(config['locked_fields'])&{'music_mode','music_track'}):continue
        candidates,excluded=shortlist(components,role,script,config['creator'],episode_id=row['id'])
        if candidates:
            c=candidates[0];asset=import_file(ws,c['file'],'graphic' if role=='logo' else 'music',owner=key)
            if role=='logo':settings['brand_logo']=asset
            else:settings.update(music_mode='my_track',music_asset=asset)
            optional.append(dict(role=role,component=c['id'],sha256=media.sha(c['file']),why='Cleared creator-scoped '+role+' supplied in inventory'))
    if settings!=job['settings']:ws.update([key],settings,{key:job['revision']});job=ws.data['jobs'][key]
    if settings['music_mode']!='off' and not any(c['role']=='music' for c in optional):optional.append(dict(role='music',component='bundled:'+p['music_track'],sha256=media.sha(Path(__file__).parent/'music'/(p['music_track']+'.wav')),gain_db=settings['music_gain_db'],why='Locked preset music palette; existing native sidechain ducking under the original narration'))
    pins=[]
    for r in lib.migrate(ws)['rounds'].values():
        if r['job']==key and r.get('choices') and r['choices'][-1]['reviewer_kind'] in ('human','agent') and r['choices'][-1]['choice'] in r['variants']:
            choice=r['choices'][-1]['choice'];pins.append(dict(beat=r['beat']['id'],params=r['variants'][choice]['params']))
    ws.save();fingerprint=digest(dict(source=row['source_sha256'],script=digest(script),preset=config['sha256'],settings=settings,beats=selected,optional=optional,manual_pins=pins,runtime=studio.runtime_identity(),pipeline=VERSION,service_sha256=media.sha(__file__)))
    return dict(row=row,job=key,revision=job['revision'],beats=selected,decisions=decisions,optional=optional,fingerprint=fingerprint,blockers=[],model=dict(mode='rules+local_retrieval',weights_loaded=False,provider_called=False,reason='Native baseline; no suitable configured adapter required',retrieval_scope='Prior scene choices from this style/job/beat and locked role preferences; no sealed/future targets'),transcript_status='ASR_WORD_TIMED' if job.get('transcript',{}).get('words') else 'SUPPLIED_SCRIPT_TIMING_UNVERIFIED_AUDIO')

def progress(ws,run,event):
    event={**event,'time':time.time()};file=ws.root/'auto-runs'/run['id']/'progress.jsonl';file.parent.mkdir(parents=True,exist_ok=True)
    with file.open('a',encoding='utf8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
    print(json.dumps(event,ensure_ascii=False),file=sys.stderr,flush=True)

def result(ws,run):
    return dict(run_id=run['id'],status=run['status'],workspace=str(ws.root),episodes=copy.deepcopy(run['episodes']),
                progress_log=str(ws.root/'auto-runs'/run['id']/'progress.jsonl'),model='rules + local scoped preference retrieval',human_approvals_created=0)

def execute(ws,run,stop_after=None):
    fresh=plan(run['request'],ws);config=fresh['config'];style,version=import_style(ws,config);completed=0
    run['status']='RUNNING';ws.save()
    by_id={e['episode_id']:e for e in run['episodes']}
    for row in fresh['episodes']:
        entry=by_id.setdefault(row['id'],dict(episode_id=row['id'],status='PENDING',history=[]))
        if entry not in run['episodes']:run['episodes'].append(entry)
        try:
            prepared=prepare_episode(ws,row,config,fresh['components'])
            if prepared['blockers']:
                entry.update(status='NEEDS_INPUT',issues=prepared['blockers'],next_action='Resolve mapping/source issues; other episodes continue');ws.save();continue
            if entry.get('fingerprint')==prepared['fingerprint'] and entry.get('output_path') and Path(entry['output_path']).is_file() and media.sha(entry['output_path'])==entry.get('master_sha256'):
                entry['resumed_without_render']=True;progress(ws,run,dict(episode=row['id'],event='REUSED_COMPLETED',export_id=entry['export_id']));continue
            if entry.get('output_path'):entry['history'].append({k:copy.deepcopy(entry[k]) for k in ('output_path','master_sha256','revision','export_id','fingerprint') if k in entry})
            entry.update(status='RENDERING',job=prepared['job'],script_path=row.get('script_path'),script_origin=row.get('script_origin'),transcript_status=prepared['transcript_status'],source_path=row['recording'],source_sha256=row['source_sha256'],script_sha256=row.get('script_sha256'),preset={k:config[k] for k in ('name','version','sha256')},model={**prepared['model'],'requested':run['request'].get('model','rules')},decisions=prepared['decisions'],optional_components=prepared['optional'])
            ws.save();progress(ws,run,dict(episode=row['id'],event='START_EPISODE',job=prepared['job']))
            rounds=[]
            for beat in prepared['beats']:
                try:
                    current=ws.data['jobs'][prepared['job']];mix_patch={**beat.get('scene_patch',{}),**{k:v for k,v in current.get('auto_manual_settings',{}).items() if k in lib.DEFAULT}}
                    if mix_patch.get('music_mode') in ('auto','my_track'):mix_patch['music_mode']='built_in'
                    r=studio.render_round(ws,dict(style=style,preset_version=version,job=prepared['job'],revision=current['revision'],beat=beat,axis='visual',require_reference=False,scene_patch=mix_patch))
                    first=next(iter(r['variants']));studio.select(ws,dict(round=r['id'],choice=first,scope='scene',reviewer='auto-edit baseline',reviewer_kind='auto',consent_train=False))
                    rounds.append(r['id'])
                except (ValueError,PermissionError) as error:
                    prepared['decisions'].append(dict(beat=beat['id'],fallback='Keep original presenter',why=[str(error)],pickup=beat.get('pickup')))
            if rounds:studio.apply_choices(ws,dict(rounds=rounds,revision=ws.data['jobs'][prepared['job']]['revision']))
            elif ws.data['jobs'][prepared['job']].get('series_selection'):
                job=ws.data['jobs'][prepared['job']];job.setdefault('series_selection_history',[]).append(job.pop('series_selection'));job['revision']+=1
            job=ws.data['jobs'][prepared['job']];job['auto_requirements']=[d for d in prepared['decisions'] if d.get('pickup')]
            job['auto_run']=run['id'];ws.save();ws.queue([job['id']],request_id=run['id']+'-'+row['id']+'-'+str(job['revision']),start=False);ws.run(job['id'])
            job=ws.data['jobs'][job['id']]
            if job['status']=='Failed' or not job.get('latest'):raise ValueError(job.get('stage','Render did not produce an export'))
            export=ws.export(job['latest']);master=Path(export['folder'])/'edit.mp4'
            if not master.is_file():raise ValueError('Renderer did not produce master')
            safe=re.sub(r'[^\w .-]','_',row['id'],flags=re.UNICODE).strip(' .')[:70] or 'episode';revision=export['revision']
            folder=Path(run['request']['out'])/('episode-'+safe)/('v'+str(revision).zfill(3)+'-'+export['id'][:8]);folder.mkdir(parents=True,exist_ok=True);out=folder/'edit.mp4'
            if out.exists() and media.sha(out)!=export['sha256']:raise Conflict('Keep prior output; choose a new revision')
            if not out.exists():shutil.copyfile(master,out)
            pickups=[d['pickup'] for d in prepared['decisions'] if d.get('pickup')]
            previews=[dict(round=rid,role=lib.migrate(ws)['rounds'][rid]['beat']['role'],variants={k:dict(path=str(studio.media_path(ws,rid,k,'mp4')),url=v['url'],sha256=v['sha256'],why=v['why']) for k,v in lib.migrate(ws)['rounds'][rid]['variants'].items()}) for rid in rounds]
            qc=load(Path(export['folder'])/'qc.json');status='QC_FAILED' if qc.get('status') in ('REVISE','BLOCKED') else 'NEEDS_REVIEW'
            used=[dict(role=lib.migrate(ws)['rounds'][rid]['beat']['role'],round=rid,choice=lib.migrate(ws)['rounds'][rid]['choices'][-1]['choice'],
                       native_components=[o['component'] for o in lib.migrate(ws)['rounds'][rid]['variants'][lib.migrate(ws)['rounds'][rid]['choices'][-1]['choice']]['spec']['objects']],
                       sfx=[s['id'] for s in lib.migrate(ws)['rounds'][rid]['variants'][lib.migrate(ws)['rounds'][rid]['choices'][-1]['choice']]['spec'].get('sfx',[])],transition='hard_cut') for rid in rounds]
            entry.update(status=status,draft=bool(pickups),pickups=pickups,revision=revision,export_id=export['id'],output_path=str(out.resolve()),master_sha256=media.sha(out),components_used=used,
                         preview_paths=previews,qc_status=qc['status'],qc_path=str(Path(export['folder'])/'qc.json'),fingerprint=prepared['fingerprint'],
                         elapsed_seconds=export['technical'].get('performance',{}).get('elapsed_seconds'),
                         next_action='Record the listed pickups, then watch/listen to the new whole master at 1×' if pickups else 'Watch and listen to this exact whole master at 1×; no human approval recorded')
            write(folder/'receipt.json',{k:v for k,v in entry.items() if k!='history'});ws.save();completed+=1;progress(ws,run,dict(episode=row['id'],event='EXPORTED',status=status,path=str(out)))
            if stop_after and completed>=stop_after:run['status']='INTERRUPTED';ws.save();return result(ws,run)
        except KeyboardInterrupt:
            entry['status']='INTERRUPTED';run['status']='INTERRUPTED';ws.save();return result(ws,run)
        except Exception as error:
            entry.update(status='ERROR',error=str(error),next_action='Repair this episode, then resume the run');ws.save();progress(ws,run,dict(episode=row['id'],event='EPISODE_ERROR',error=str(error)))
    run['status']='COMPLETED_WITH_ISSUES' if any(e['status'] in ('ERROR','NEEDS_INPUT','QC_FAILED') for e in run['episodes']) else 'COMPLETED';run['finished']=time.time();ws.save();return result(ws,run)

def auto_edit(ws,request):
    p=plan(request,ws)
    if request.get('plan_only'):return dict(status='PLAN_ONLY',**p)
    key=uuid.uuid4().hex;run=dict(id=key,version=VERSION,request=copy.deepcopy(request),created=time.time(),status='PENDING',episodes=[])
    ws.data.setdefault('auto_runs',{})[key]=run;ws.save();return execute(ws,run,request.get('stop_after'))

def resume(ws,run_id,stop_after=None):return execute(ws,ws.data['auto_runs'][run_id],stop_after)
def status(root,run_id):
    data=load(Path(root)/'workspace.json');run=data.get('auto_runs',{})[run_id];return dict(run_id=run_id,status=run['status'],episodes=run['episodes'],workspace=str(Path(root).resolve()))

def revise(ws,b):
    run=ws.data['auto_runs'][b['run']];entry=next(e for e in run['episodes'] if e['episode_id']==b['episode']);job=ws.data['jobs'][entry['job']]
    patch=copy.deepcopy(b['patch']);request=digest([run['id'],entry['episode_id'],b.get('request_id') or patch]);old=ws.data.setdefault('auto_revision_requests',{}).get(request)
    if old and old.get('patch_sha256')!=digest(patch):raise Conflict('Revision request ID reused with a different patch')
    if old:return {**copy.deepcopy(old),'replayed':True}
    if b.get('revision') is not None and b['revision']!=job['revision']:raise Conflict('Episode revision changed')
    if 'round' in patch or 'choice' in patch:
        if set(patch)!={'round','choice'}:raise ValueError('Change a scene choice separately from mix settings')
        r=lib.migrate(ws)['rounds'][patch['round']]
        if r['job']!=job['id']:raise ValueError('Scene belongs to another episode')
        studio.select(ws,dict(round=r['id'],choice=patch['choice'],scope='scene',reviewer='CLI episode directive',reviewer_kind='agent',consent_train=False,note='Explicit terminal choice; not a human watch/listen attestation'))
        rounds=job.get('series_selection',{}).get('rounds',[r['id']]);studio.apply_choices(ws,dict(rounds=rounds,revision=job['revision']));entry.pop('fingerprint',None)
        answer=dict(run_id=run['id'],episode_id=entry['episode_id'],revision=job['revision'],status='DRAFT',preset_changed=False,next_action='resume this run to render and QC a new master')
        answer['patch_sha256']=digest(b['patch']);ws.data['auto_revision_requests'][request]=answer;ws.save();return answer
    if 'when_quote' in patch:
        quote=lib.text(patch.pop('when_quote'),240);delta=patch.pop('music_delta_db',None)
        import creator_editor
        matches=[c for c in creator_editor.caption_cues(job['settings']['script']) if quote.casefold() in c['text'].casefold()]
        if len(matches)!=1:raise ValueError('Scoped music needs one unique timed phrase in this episode; supply timed captions or a more specific quote')
        if type(delta) not in (int,float) or not -24<=delta<=6:raise ValueError('Use a bounded music_delta_db of -24…6')
        cue=matches[0];automation=copy.deepcopy(job['settings'].get('music_automation',[]));automation.append(dict(source_range=[cue['start'],cue['end']],gain_db=delta,reason='Explicit episode-only request: '+quote));patch['music_automation']=automation
    allowed={'music_gain_db','music_mode','music_track','music_automation','style','caption_position'}
    if set(patch)-allowed:raise ValueError('Unsupported episode setting; use a declared scene choice or scoped music/caption patch')
    config=style_config(run['request'],ws)
    mapped={'style':'caption_style'}
    for k,v in patch.items():
        key=mapped.get(k,k);value='built_in' if k=='music_mode' and v in ('auto','my_track') else v
        if key in config['locked_fields'] and value!=config['params'][key]:raise ValueError('Episode setting changes locked preset '+key+'; use a scoped music cue or explicitly fork the preset')
    ws.update([job['id']],patch,{job['id']:job['revision']});job.setdefault('auto_manual_settings',{}).update(copy.deepcopy(patch));entry.pop('fingerprint',None);entry['manual_settings']=copy.deepcopy(patch);ws.save()
    # Other completed episodes keep their exact export IDs and hashes.
    answer=dict(run_id=run['id'],episode_id=entry['episode_id'],revision=ws.data['jobs'][job['id']]['revision'],status='DRAFT',next_action='resume this run to export a new version',preset_changed=False)
    answer['patch_sha256']=digest(b['patch']);ws.data['auto_revision_requests'][request]=answer;ws.save();return answer

def library(ws):
    import motion_catalog
    return dict(presets=lib.snapshot(ws)['styles'],components=motion_catalog.inventory(),runs=[dict(id=r['id'],status=r['status'],episodes=len(r['episodes'])) for r in ws.data.get('auto_runs',{}).values()])
