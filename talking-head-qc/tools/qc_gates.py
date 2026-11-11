"""Six export gates. Measurements never impersonate watching or listening."""
import array
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

GATES={'A':'Opening and payoff','B':'Visual proof','C':'Vietnamese captions','D':'Animation and SFX','E':'Voice and mix','F':'Final export'}
STATES={'PASS','FAIL','UNVERIFIED','N/A'}

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def command(args):return subprocess.run(list(map(str,args)),capture_output=True,timeout=1800)
def finite(x):return type(x) in (int,float) and math.isfinite(x)
def span(x,duration):return isinstance(x,list) and len(x)==2 and all(finite(v) for v in x) and 0<=x[0]<x[1]<=duration+.05
def norm(text):return ' '.join(unicodedata.normalize('NFC',text).casefold().split())
def covered(ranges,start,end):
    cursor=start
    for a,b in sorted(ranges):
        if b<=cursor:continue
        if a>cursor+.05:return False
        cursor=max(cursor,b)
    return cursor>=end-.05

def validate_profile(p):
    if p.get('schema_version')!=1 or not p.get('revision') or p.get('job_kind') not in ('real','fixture'):raise ValueError('Invalid acceptance profile identity')
    s=p['specs']
    if not all(re.fullmatch('[0-9a-f]{64}',p.get('plan_hashes',{}).get(k,'')) for k in ('brief.md','timeline.json','delivery.json')):raise ValueError('Profile must bind brief/timeline/delivery revisions')
    for k in ('width','height','expected_frames'):
        if type(s.get(k)) is not int or s[k]<=0:raise ValueError('Profile needs positive '+k)
    if not finite(s.get('fps')) or not 0<s['fps']<=240:raise ValueError('Invalid profile fps')
    if not 0<=s.get('frame_tolerance',1)<=1:raise ValueError('Frame tolerance must be0–1 output frames')
    for k in ('caption_tolerance_ms','sfx_tolerance_frames','sync_tolerance_frames'):
        if not finite(p['thresholds'].get(k)) or p['thresholds'][k]<0:raise ValueError('Invalid threshold '+k)
    if p['thresholds']['sfx_tolerance_frames']>1:raise ValueError('Frame-locked SFX tolerance cannot exceed one output frame')
    if p.get('speech_free_fixture') and (p['job_kind']!='fixture' or not p.get('speech_free_reason')):raise ValueError('Dialogue exemption requires a documented speech-free fixture')
    if p.get('fixture_visual_assertions') and p['job_kind']!='fixture':raise ValueError('Synthetic pixel assertions cannot certify real proof')
    ids=[d['id'] for d in p.get('demonstrations',[])]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate demonstration IDs')
    count=p.get('required_repository_count')
    if count is not None and (type(count) is not int or count<=0 or len({d.get('repo_name') for d in p.get('demonstrations',[]) if d.get('repo_name')})!=count):raise ValueError('Declared repository count differs from named proof requirements')
    for key,config in p.get('gates',{}).items():
        if key not in GATES:raise ValueError('Unknown QC gate')
        if p['job_kind']=='real' and key!='F' and config.get('applicable') is not False and config.get('review_required') is False:raise ValueError('A real master requires actual editorial review for gate '+key)
        if config.get('applicable') is False:
            if not config.get('reason'):raise ValueError('N/A requires an applicability reason')
            if key=='B' and ids:raise ValueError('Required demonstrations cannot be N/A')
            if key=='C' and s.get('caption_modes'):raise ValueError('Requested captions cannot be N/A')
            if key=='E' and not p.get('speech_free_fixture'):raise ValueError('Voice gate cannot be dismissed for a real dialogue episode')
    return p

def srt_rows(path):
    def time(t):
        h,m,s=t.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)
    result=[]
    for block in re.split(r'\n\s*\n',Path(path).read_text(encoding='utf-8-sig').strip()):
        lines=block.splitlines()
        if len(lines)<3:raise ValueError('Malformed SRT')
        a,b=lines[1].split(' --> ');result.append({'start':time(a),'end':time(b),'lines':lines[2:],'text':' '.join(lines[2:])})
    return result

def measurement(id_,target,actual,ok=None,when=None,reason=''):
    return {'id':id_,'kind':'measurement','status':'UNVERIFIED' if ok is None else 'PASS' if ok else 'FAIL','target':target,'actual':actual,'master_range':when,'evidence':reason,'severity':'major' if ok is False else 'none'}

def rgb_mean(video,seconds,roi):
    x,y,w,h=roi
    r=command(['ffmpeg','-v','error','-ss',f'{seconds:.9f}','-i',video,'-vf',f'crop={w}:{h}:{x}:{y},format=gray','-frames:v','1','-f','rawvideo','-'])
    if r.returncode or len(r.stdout)!=w*h:raise ValueError('Cannot decode visual assertion frame')
    return sum(r.stdout)/len(r.stdout)

def pcm(path):
    r=command(['ffmpeg','-v','error','-i',path,'-map','0:a:0','-vn','-ac','1','-ar','48000','-f','f32le','-'])
    if r.returncode:raise ValueError('Cannot decode isolated/final audio')
    values=array.array('f');values.frombytes(r.stdout)
    if sys.byteorder!='little':values.byteswap()
    return values


def mix_alignment(scores,tolerance,threshold=.65):
    """A periodic/masked waveform may match several lags; that is not a defect.

    Never turn ambiguity into PASS. A unique supported shift still fails at the
    unchanged one-frame tolerance; isolated timing failures remain failures.
    """
    best=max(scores,default=(-1,None))
    inside=max((s for s in scores if abs(s[1])<=tolerance+1e-6),default=(-1,None))
    outside=max((s for s in scores if abs(s[1])>tolerance+1e-6),default=(-1,None))
    competing=inside if best[1] is not None and abs(best[1])>tolerance+1e-6 else outside
    ambiguous=competing[0]>=threshold and best[0]-competing[0]<.05
    status='UNVERIFIED' if best[0]<threshold or ambiguous else 'FAIL' if abs(best[1])>tolerance+1e-6 else 'PASS'
    return dict(status=status,correlation=best[0],lag_frames=best[1],competing_correlation=competing[0],competing_lag_frames=competing[1],ambiguous=ambiguous)

def cue_measure(video,profile,cue,cache,duration):
    """Peak from isolated stem; matched correlation, never final-voice peak picking."""
    fps=profile['specs']['fps'];event=cue['visual_frame']/fps;window=cue.get('window_seconds',.12)
    result={'id':cue['id'],'visual_assigned_frame':cue['visual_frame'],'landmark':cue.get('landmark','peak_abs'),'timebase':'decoded master seconds, frame zero','master_range':[max(0,event-window),min(duration,event+window)]}
    try:
        if cue.get('landmark','peak_abs')!='peak_abs':raise ValueError('Unsupported acoustic landmark; specify peak_abs or add a measured implementation')
        stem=Path(cue['stem_path'])
        if sha(stem)!=cue['stem_sha256']:raise ValueError('Isolated stem bytes changed')
        key=str(stem.resolve())
        if key not in cache:cache[key]=pcm(stem)
        data=cache[key];offset=cue.get('stem_master_offset_seconds',0);lo=max(0,round((event-offset-window)*48000));hi=min(len(data),round((event-offset+window)*48000))
        if hi<=lo or max(map(abs,data[lo:hi]),default=0)<1e-6:raise ValueError('No isolated acoustic landmark in assigned window')
        index=max(range(lo,hi),key=lambda i:abs(data[i]));peak=index/48000+offset
        delta=(peak-event)*fps;result.update(isolated_peak_seconds=peak,offset_frames=delta,isolated_peak_dbfs=20*math.log10(abs(data[index])))
        intended=cue.get('expected_offset_frames',0)
        if intended and not cue.get('editorial_exception'):intended=0
        result.update(expected_offset_frames=intended,deviation_frames=delta-intended)
        result['status']='PASS' if abs(delta-intended)<=profile['thresholds']['sfx_tolerance_frames']+1e-6 else 'FAIL'
        probe=cue.get('visual_probe')
        if probe:
            if profile['job_kind']!='fixture':raise ValueError('Synthetic markers cannot certify a real control action')
            hits=[]
            for frame in range(max(0,cue['visual_frame']-2),cue['visual_frame']+3):
                if frame/fps>=duration:continue
                if rgb_mean(video,frame/fps,probe['roi'])>=probe['min_mean']:hits.append(frame)
            if not hits:result.update(status='FAIL',visual_actual_frame=None,visual_probe='Assigned synthetic marker absent')
            else:
                actual=min(hits,key=lambda f:abs(f-cue['visual_frame']));result['visual_actual_frame']=actual
                result['offset_frames']=(peak-actual/fps)*fps
                if abs(result['offset_frames'])>profile['thresholds']['sfx_tolerance_frames']+1e-6:result['status']='FAIL'
        if 'final_pcm' not in cache:cache['final_pcm']=pcm(video)
        mixed=cache['final_pcm'];radius=round(.014*48000);a=max(0,index-radius);b=min(len(data),index+radius);template=data[a:b]
        expected=round((a/48000+offset)*48000);norm_a=sum(v*v for v in template);scores=[]
        # Submillisecond grid around the assigned offset, with normalized score.
        # Search the declared evidence window, not only ±2frames. A four-frame
        # routing error must be observable rather than disappearing outside search.
        lag_limit=round(min(.5,max(2/fps,window))*48000)
        for lag in range(-lag_limit,lag_limit+1,24):
            start=expected+lag
            if start<0 or start+len(template)>len(mixed):continue
            sample=mixed[start:start+len(template)];energy=sum(v*v for v in sample)
            corr=sum(x*y for x,y in zip(template,sample))/math.sqrt(max(norm_a*energy,1e-20))
            scores.append((corr,lag/48000*fps))
        alignment=mix_alignment(scores,profile['thresholds']['sfx_tolerance_frames'],cue.get('correlation_threshold',.65))
        result['final_mix_correlation']=alignment['correlation'];result['final_mix_lag_frames']=alignment['lag_frames'];result['final_mix_alignment']=alignment
        if alignment['status']=='UNVERIFIED':result['final_mix_crosscheck']='UNVERIFIED: ambiguous alignment or overlapping voice/codec requires listening or stronger separation'
        elif alignment['status']=='FAIL':result.update(status='FAIL',final_mix_crosscheck='FAIL')
        else:result['final_mix_crosscheck']='PASS'
    except (OSError,ValueError,subprocess.SubprocessError) as e:result.update(status='UNVERIFIED',reason=str(e))
    return result

def assess(folder,profile,bundle,info,technical_failures,review,decode_failures=None):
    profile=validate_profile(profile);video=folder/'edit.mp4';duration=float(info['format']['duration']);fps=profile['specs']['fps'];spec=profile['specs']
    gates={k:{'name':name,'status':'UNVERIFIED','checks':[]} for k,name in GATES.items()};issues=[];metrics={};cache={}
    def add(k,item):
        gates[k]['checks'].append(item)
        if item['status']=='FAIL':issues.append({'id':item['id'],'gate':k,'severity':item.get('severity','major'),'master_range':item.get('master_range') or [0,duration],'expected':item['target'],'actual':item['actual'],'correction':item.get('correction') or 'Correct the source timeline/profile as appropriate, render a fresh revision and inspect that exact export.','evidence':item.get('evidence','')})
    streams=info['streams'];picture=next(s for s in streams if s['codec_type']=='video' and not s.get('disposition',{}).get('attached_pic'));audio=next((s for s in streams if s['codec_type']=='audio'),{});subs=[s for s in streams if s['codec_type']=='subtitle']
    measurements=[('video_codec',spec['video_codec'],picture.get('codec_name'),picture.get('codec_name')==spec['video_codec']),('dimensions',[spec['width'],spec['height']],[picture['width'],picture['height']],[picture['width'],picture['height']]==[spec['width'],spec['height']])]
    try:actual_fps=float(Fraction(picture['avg_frame_rate']))
    except (KeyError,ValueError,ZeroDivisionError):actual_fps=None
    measurements.append(('frame_rate',fps,actual_fps,None if actual_fps is None else abs(actual_fps-fps)<1e-6))
    count=int(picture['nb_read_frames']) if picture.get('nb_read_frames','').isdigit() else None
    metrics['decoded_frames']=count;measurements.append(('frame_count',{'expected':spec['expected_frames'],'tolerance_frames':spec.get('frame_tolerance',1)},count,None if count is None else abs(count-spec['expected_frames'])<=spec.get('frame_tolerance',1)))
    if spec.get('audio_expected',True):
        measurements.extend([('audio_codec',spec['audio_codec'],audio.get('codec_name'),audio.get('codec_name')==spec['audio_codec']),('audio_sample_rate',spec['sample_rate'],int(audio.get('sample_rate',0)),int(audio.get('sample_rate',0))==spec['sample_rate'])])
    if 'selectable' in spec.get('caption_modes',[]):measurements.append(('selectable_captions','at least one subtitle stream',len(subs),bool(subs)))
    if 'burned_in' in spec.get('caption_modes',[]) and subs:measurements.append(('no_default_duplicate_caption','selectable captions default off when burned in',[s.get('disposition',{}).get('default',0) for s in subs],not any(s.get('disposition',{}).get('default') for s in subs)))
    for id_,target,actual,ok in measurements:add('F',measurement(id_,target,actual,ok,[0,duration],'Decoded export metadata/count, not timeline-only inference.'))
    decode_errors=technical_failures if decode_failures is None else decode_failures
    add('F',measurement('full_decode','complete picture/audio decode',decode_errors,not decode_errors,[0,duration]))
    if technical_failures:add('F',measurement('delivery_checks','delivery format and required timeline beats',technical_failures,False,[0,duration]))
    planned=profile.get('plan_hashes',{});plan_matches=all(bundle.get(name)==expected for name,expected in planned.items())
    add('F',measurement('profile_plan_revision','profile bound before rendering to this brief/timeline/delivery',planned,True if plan_matches else None,[0,duration],'A changed plan requires a refreshed profile and fresh review.'))
    for name,expected in profile.get('project_hashes',{}).items():
        valid=bundle.get(name)==expected
        add('F',measurement('project_revision:'+name,expected,bundle.get(name),True if valid else None,[0,duration],'A changed renderer/project requires a refreshed profile and repeatability check.'))
    repeat=folder/'repeatability.json'
    try:
        r=read(repeat);output=Path(r['rerender_path']);project=folder/'render-project.json'
        ok=r['master_sha256']==bundle['edit.mp4'] and r['project_sha256']==sha(project) and sha(output)==r['rerender_sha256'] and r['rerender_sha256']==bundle['edit.mp4']
        add('F',measurement('project_rerun','reopened/rerun project yields same exact master',r,ok,[0,duration]))
    except (OSError,ValueError,KeyError):add('F',measurement('project_rerun','actual rerun receipt bound to master and project',None,None,[0,duration]))
    try:captions=srt_rows(folder/'captions.srt')
    except (ValueError,IndexError):
        captions=[];add('C',measurement('srt_structure','ordered valid SubRip cues','Malformed SRT',False,[0,duration]))
    max_lines=max((len(c['lines']) for c in captions),default=0)
    add('C',measurement('caption_lines',profile['thresholds'].get('max_caption_lines',2),max_lines,max_lines<=profile['thresholds'].get('max_caption_lines',2),[0,duration]))
    for assertion in profile.get('caption_assertions',[]):
        if not span(assertion['master_range'],duration):raise ValueError('Caption assertion range invalid')
        a,b=assertion['master_range'];text=' '.join(c['text'] for c in captions if c['start']<b and c['end']>a)
        good=bool(re.search(r'(?<!\w)'+re.escape(norm(assertion['text']))+r'(?!\w)',norm(text)))
        add('C',measurement('caption:'+assertion['id'],assertion['text'],text,good,[a,b],'SRT text assertion only; speech and burned text still require review.'))
    for anchor in profile.get('caption_timing_anchors',[]):
        matches=[c for c in captions if norm(anchor['text']) in norm(c['text']) and c['start']<anchor['end']+.5 and c['end']>anchor['start']-.5]
        if not matches:add('C',measurement('caption_timing:'+anchor['id'],anchor,None,None,[anchor['start'],anchor['end']]))
        else:
            first,last=matches[0],matches[-1];offsets=[1000*(first['start']-anchor['start']),1000*(last['end']-anchor['end'])];ok=max(map(abs,offsets))<=profile['thresholds']['caption_tolerance_ms']
            if not ok and anchor.get('editorial_exception'):ok=None
            if not anchor.get('human_verified_anchor'):ok=None
            add('C',measurement('caption_timing:'+anchor['id'],{'tolerance_ms':profile['thresholds']['caption_tolerance_ms']},offsets,ok,[anchor['start'],anchor['end']],anchor.get('editorial_exception') or 'ASR-only anchors are provisional, not a listening pass.'))
    for demo in profile.get('demonstrations',[]):
        if not span(demo['master_range'],duration):raise ValueError('Demonstration range invalid')
        path=Path(demo['source_asset'])
        valid=path.is_file() and sha(path)==demo['source_sha256']
        add('B',measurement('source:'+demo['id'],{'claim':demo['claim'],'source_range':demo['source_range']},str(path),True if valid else None,demo['master_range'],'Source identity is not proof of visibility; inspect the opened master at phone size1x.'))
    for assertion in profile.get('fixture_visual_assertions',[]):
        actual=rgb_mean(video,assertion['time'],assertion['roi']);add('B',measurement('fixture_region:'+assertion['id'],{'min_mean':assertion['min_mean']},round(actual,3),actual>=assertion['min_mean'],[assertion['time'],assertion['time']+1/fps],'Synthetic controlled ROI only, not a general screen-proof detector.'))
    cue_results=[]
    for cue in profile.get('motion_cues',[]):
        if not cue.get('frame_locked'):continue
        result=cue_measure(video,profile,cue,cache,duration);cue_results.append(result)
        ok={'PASS':True,'FAIL':False}.get(result['status']);add('D',measurement('sfx:'+cue['id'],{'tolerance_frames':profile['thresholds']['sfx_tolerance_frames'],'visual_frame':cue['visual_frame']},result,ok,result['master_range'],'Peak measured from isolated stem, checked against decoded output timebase.'))
        if result.get('final_mix_crosscheck','').startswith('UNVERIFIED'):add('D',measurement('mix_offset:'+cue['id'],'cross-check isolated cue in final mix',result,None,result['master_range']))
    metrics['cue_offsets']=cue_results
    loud=command(['ffmpeg','-hide_banner','-nostdin','-i',video,'-map','0:a:0','-vn','-af','loudnorm=I=-16:TP=-1:LRA=11:print_format=json','-f','null','-']) if audio else None
    try:
        text=loud.stderr.decode('utf-8',errors='replace');data=json.JSONDecoder().raw_decode(text[text.rfind('{'):])[0];i,tp=float(data['input_i']),float(data['input_tp']);metrics.update(integrated_lufs=i if math.isfinite(i) else None,true_peak_dbtp=tp if math.isfinite(tp) else None,lra_lu=float(data['input_lra']))
        if profile.get('speech_free_fixture'):add('E',{'id':'dialogue_loudness','kind':'measurement','status':'N/A','target':'dialogue -16LUFS±2','actual':i,'evidence':profile['speech_free_reason'],'severity':'none','master_range':[0,duration]})
        else:
            target=profile['thresholds']['loudness_lufs'];tol=profile['thresholds']['loudness_tolerance_lu'];add('E',measurement('dialogue_loudness',{'lufs':target,'tolerance_lu':tol},i,abs(i-target)<=tol,[0,duration]))
        add('E',measurement('true_peak',profile['thresholds']['max_true_peak_dbtp'],tp,tp<=profile['thresholds']['max_true_peak_dbtp'],[0,duration]))
    except (AttributeError,ValueError,TypeError):add('E',measurement('audio_measurement','decoded-output loudness/true peak',None,None,[0,duration],'Audio/loudnorm unavailable; complete independent checks and name the dependency.'))
    review_matches=review.get('bundle')==bundle
    reviewer=review.get('reviewer',{}) if review_matches else {};watched=review.get('watched_ranges',[]) if review_matches else [];listened=review.get('listened_ranges',[]) if review_matches else []
    for ranges in (watched,listened):
        if any(not span(r,duration) for r in ranges):raise ValueError('Review range outside master')
    full_watch=reviewer.get('can_watch') is True and covered(watched,0,duration) and review.get('viewing',{}).get('speed')==1 and 0<review.get('viewing',{}).get('width_px',9999)<=profile.get('phone_width_px',360)
    full_listen=reviewer.get('can_listen') is True and covered(listened,0,duration) and review.get('listening_speed')==1
    for k in GATES:
        config=profile.get('gates',{}).get(k,{})
        if config.get('applicable') is False:
            if any(c['status']=='FAIL' for c in gates[k]['checks']):raise ValueError('N/A cannot hide a detected required failure')
            gates[k].update(status='N/A',reason=config['reason']);continue
        needed=config.get('evidence_ids',[]);observed=review.get('gates',{}).get(k,{}) if review_matches else {};status=observed.get('status','UNVERIFIED');evidence=observed.get('evidence',[])
        if status not in STATES:raise ValueError('Unknown review status')
        valid_evidence=isinstance(evidence,list) and bool(evidence) and all(isinstance(e,dict) and e.get('id') and span(e.get('master_range'),duration) and e.get('expected') and e.get('actual') for e in evidence)
        if status=='FAIL' and valid_evidence and reviewer.get('id'):
            for e in evidence:
                modality=e.get('modality','visual')
                seen=reviewer.get('can_watch') is True and covered(watched,*e['master_range'])
                heard=reviewer.get('can_listen') is True and covered(listened,*e['master_range'])
                if not (seen if modality=='visual' else heard if modality=='audio' else seen and heard):continue
                item=measurement('review:'+e['id'],e['expected'],e['actual'],False,e['master_range'],e.get('evidence',''));item.update(kind='observation',severity=e.get('severity','major'),correction=e.get('correction'));add(k,item)
        required=config.get('review_required',profile['job_kind']=='real' and k!='F')
        if required:
            ids={e.get('id') for e in evidence if isinstance(e,dict)} if isinstance(evidence,list) else set()
            capable=full_watch if k in ('A','B','D') else full_listen if k=='E' else full_watch and full_listen
            if k=='D' and profile.get('motion_cues'):capable=capable and full_listen
            valid=status=='PASS' and valid_evidence and set(needed)<=ids and capable and bool(reviewer.get('id'))
            ranges=profile.get('evidence_ranges',{})
            valid=valid and all(any(e.get('id')==id_ and max(e['master_range'][0],ranges[id_][0])<min(e['master_range'][1],ranges[id_][1]) for e in evidence) for id_ in needed if id_ in ranges) if valid else False
            if k=='E' and profile.get('visible_speech',True):
                observations=review.get('sync_observations',[]) if review_matches and reviewer.get('can_listen') and reviewer.get('can_watch') else [];anchors=profile.get('sync_sample_times',[min(3,duration/4),duration/2,max(0,duration-2)])
                valid=valid and all(any(finite(o.get('time')) and finite(o.get('offset_frames')) and abs(o['time']-t)<=3 for o in observations) for t in anchors)
                for o in observations:
                    if finite(o.get('offset_frames')) and abs(o['offset_frames'])>profile['thresholds']['sync_tolerance_frames'] and not o.get('editorial_exception'):add('E',measurement('av_sync',profile['thresholds']['sync_tolerance_frames'],o,False,[o['time'],min(duration,o['time']+1/fps)]))
            add(k,{'id':'actual_review','kind':'observation','status':'PASS' if valid else 'UNVERIFIED','target':{'evidence_ids':needed,'phone_1x_watch':k!='E','full_listening':k in ('C','E')},'actual':{'review_matches_master':review_matches,'reviewer':reviewer,'full_watch':full_watch,'full_listen':full_listen},'evidence':evidence,'master_range':[0,duration],'severity':'none'})
        if k=='D' and review_matches and full_listen:
            for c in gates[k]['checks']:
                if c['id'].startswith('mix_offset:') and c['status']=='UNVERIFIED':
                    cue_id=c['id'].split(':',1)[1]
                    for o in review.get('cue_observations',[]):
                        if o.get('id')==cue_id and o.get('stem_checked') is True and o.get('final_mix_checked') is True and finite(o.get('offset_frames')):
                            c.update(kind='observation',actual=o,status='PASS' if abs(o['offset_frames'])<=profile['thresholds']['sfx_tolerance_frames'] else 'FAIL')
                            if c['status']=='FAIL':issues.append({'id':c['id'],'gate':'D','severity':'major','master_range':c['master_range'],'expected':c['target'],'actual':o,'correction':'Retime the cue and render a new version.'})
        checks=gates[k]['checks'];gates[k]['status']='FAIL' if any(c['status']=='FAIL' for c in checks) else 'UNVERIFIED' if any(c['status']=='UNVERIFIED' for c in checks) else 'PASS' if checks else 'UNVERIFIED'
    missing=[k for k,g in gates.items() if g['status']=='UNVERIFIED']
    final_approval=bool(review.get('approved_by')) and review_matches if profile['job_kind']=='real' else True
    status='REVISE' if issues else 'NEEDS_REVIEW' if missing or not final_approval or not plan_matches else 'READY'
    return {'schema_version':2,'status':status,'job_kind':profile['job_kind'],'bundle':bundle,'profile_revision':profile['revision'],'gates':gates,'issues':issues,'measurements':metrics,'reviewer':reviewer,'watched_ranges':watched,'listened_ranges':listened,'approved_by':review.get('approved_by','') if review_matches else '', 'review_binding_valid':review_matches,'pending_gates':missing,'next_action':'Fix verified issues in a new version; then review the exact export.' if issues else 'A capable reviewer watches at phone size1x, hears the entire master, completes the bound review and signs off.' if status=='NEEDS_REVIEW' else 'Deliver this exact master.'}

def markdown(report):
    def cell(value):
        text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
        if len(text)>650:text=text[:650]+'… (full detail: qc.json)'
        return text.replace('|','\\|').replace('\n','<br>')
    lines=['# Final-video QC',f"\nStatus: **{report['status']}** · {report.get('job_kind','legacy')}\n",'|Gate|Verdict|','|---|---|']
    for k,g in report.get('gates',{}).items():
        lines.append(f"|{k}. {g['name']}|{g['status']}|")
    lines+=['\n## Check evidence','|Gate / check|Target|Actual|Evidence / edited seconds|Severity|Verdict|','|---|---|---|---|---|---|']
    for k,g in report.get('gates',{}).items():
        if g['status']=='N/A':lines.append(f"|{k}|Applicable content|{cell(g.get('reason',''))}|Profile applicability reason|none|N/A|")
        for c in g['checks']:
            lines.append(f"|{k}: {cell(c['id'])}|{cell(c.get('target'))}|{cell(c.get('actual'))}|{cell(c.get('master_range'))}; {cell(c.get('evidence',''))}|{c.get('severity','none')}|{c['status']}|")
    lines+=['\n## Measurements','```json',json.dumps(report.get('measurements',{}),ensure_ascii=False,indent=2),'```','\n## Issues','```json',json.dumps(report.get('issues',[]),ensure_ascii=False,indent=2),'```',f"\nMaster SHA256: `{report['bundle'].get('edit.mp4')}`",f"\nReviewer: {json.dumps(report.get('reviewer',{}),ensure_ascii=False)}",f"\nWatched: {report.get('watched_ranges',[])} · Listened: {report.get('listened_ranges',[])}",f"\nNext action: {report.get('next_action','Complete profile/review.')}"]
    return '\n'.join(lines)+'\n'
