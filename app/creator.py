"""Conservative recording-first orchestration. Niche never rewrites recorded meaning."""
import copy,difflib,hashlib,json,math,re,time
from pathlib import Path
from engine import media,planner
import speech

FORMATS={
 'result-first':('Kết quả trước','A recorded, recognizable result.',True),
 'mistake-fix':('Lỗi và cách sửa','The actual error and corrected state.',True),
 'before-after':('Trước và sau','A comparable recorded transformation.',True),
 'a-b':('Hai lựa chọn','Both real options under comparable conditions.',True),
 'myth-check':('Kiểm chứng một quan niệm','The missing comparison or qualifier.',True),
 'checklist':('Danh sách kiểm','Observable checks on one example.',False),
 'viewer-question':('Trả lời câu hỏi','A recorded answer and its condition.',False),
 'challenge':('Thử thách','Countable real actions and the outcome.',True),
 'teardown':('Phân tích bản gốc','Original and changed hierarchy, facts preserved.',True),
 'mini-case':('Một tình huống cụ thể','Actual mismatch and corrected states.',True),
}


def identity(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def schedule(script):
    return re.findall(r'\d{1,2}:\d{2}:\d{2}[,.]\d{1,3}\s*-->\s*\d{1,2}:\d{2}:\d{2}[,.]\d{1,3}',script or '')


def suggestions(beats,assets,job,duration):
    result=[];stop={'anh','em','mình','của','các','một','và','là','thì','the','this','that','with','video'}
    for a in assets.values():
        if a.get('source_role')!='broll' or job not in a.get('owner_jobs',[]) or not a.get('description'):continue
        labels={speech.key(w) for w in a['description'].split()}-stop
        scored=[(len(labels & ({speech.key(w) for w in b['quote'].split()}-stop)),b) for b in beats]
        overlap,beat=max(scored,key=lambda x:x[0]) if scored else (0,None)
        if overlap>=2:result.append(dict(asset=a['id'],beat=beat['id'],at=beat['source_start'],offset=0,duration=min(4.,a['duration'],duration-beat['source_start']),
            reason=f'{overlap} shared creator-label terms. Preview the supplied shot; confirm action/result before insertion.',status='SUGGESTION_ONLY'))
    return result


def refresh(context,transcript,settings,host,assets,job):
    result=copy.deepcopy(context)
    facts=explain(transcript or {},context.get('prepared_script',''),host,settings.get('niche',''),settings.get('story_format','auto'),settings.get('inserts',[]))
    result.update(brief=facts['brief'],hooks=facts['hooks'],reused_transcript=True)
    result['broll_suggestions']=suggestions(result['beats'],assets,job,host['duration'])
    return result


def explain(transcript,prepared,host,niche='',format_choice='auto',inserts=()):
    """ASR facts, editorial proposals and inferred repair candidates stay separate."""
    words=transcript.get('words',[]);segments=transcript.get('segments',[])
    if not segments and words:segments=[dict(start=words[0]['start'],end=words[-1]['end'],text=' '.join(w['text'] for w in words))]
    beats=[];uncertain=[]
    for index,s in enumerate(segments):
        if not 0<=s['start']<s['end']<=host['duration']+.034:continue
        beat_id='speech-'+identity([host['source_sha256'],index,round(s['start']*30),s['text']])[:16]
        beats.append(dict(id=beat_id,quote=s['text'],source_start=s['start'],source_end=s['end'],edit_start=s['start'],edit_end=s['end'],
                          source_asset=host['id'],source_sha256=host['source_sha256'],evidence_type='presenter',locked=False,decision='KEEP_COMPLETE_PASSAGE'))
        nearby=[w for w in words if s['start']<=w['start']<s['end']]
        low=[w for w in nearby if w.get('probability',1)<.65 or w['end']<=w['start']]
        if low:uncertain.append(dict(id=beat_id,source_range=[s['start'],s['end']],reason='Low recognition confidence: '+', '.join(w['text'] for w in low),action='Keep passage; listen and correct captions.'))
    for first,second in zip(beats,beats[1:]):
        a=[speech.key(w) for w in first['quote'].split()];b=[speech.key(w) for w in second['quote'].split()]
        if min(len(a),len(b))>=3 and difflib.SequenceMatcher(None,a,b,autojunk=False).ratio()>=.72:
            uncertain.append(dict(id='retake-'+first['id'],source_range=[first['source_start'],second['source_end']],reason='Possible repeated take; natural delivery not inferred from ASR.',action='Both retained. Audition the complete sentences before choosing.',takes=[first,second]))
    draft_tokens=[speech.key(w) for w in re.findall(r'[^\W_]+',prepared) if not w.isdigit()]
    actual=[speech.key(w['text']) for w in words]
    mismatch=None
    if prepared and actual:
        ratio=difflib.SequenceMatcher(None,draft_tokens,actual,autojunk=False).ratio()
        mismatch=dict(token_similarity=round(ratio,3),basis='Text comparison, not auditory alignment',action='Actual speech controls captions; preserve qualifiers and deviations.')
    proof=[q for q in inserts if q.get('anchors',{}).get('result') is not None]
    question=next((b for b in beats if '?' in b['quote']),None);first=beats[0] if beats else None
    hooks=[dict(id='host',kind='host_first',quote=first['quote'] if first else '',source_range=[first['source_start'],first['source_end']] if first else None,
                first_picture='Original presenter',available=bool(first),score=1,reason='Available recorded voice; no unverified result inserted.'),
           dict(id='question',kind='honest_question',quote=question['quote'] if question else None,source_range=[question['source_start'],question['source_end']] if question else None,
                available=bool(question),score=2 if question else 0,reason='Recorded question; a later quote is a proposal, not silently moved speech.' if question else 'Optional pickup; no question was invented in the audio.'),
           dict(id='proof',kind='proof_first',quote=first['quote'] if first else None,source_range=[first['source_start'],first['source_end']] if first else None,
                available=bool(proof),score=3 if proof else 0,first_picture='Assigned real result' if proof else None,reason='Source-bound result anchor supplied by creator.' if proof else 'No assigned verified result; retain presenter.')]
    chosen=format_choice if format_choice!='auto' else 'result-first' if proof else 'viewer-question' if question else 'checklist' if any(w in ' '.join(actual) for w in ('bước','repo','cách')) else 'viewer-question'
    if chosen not in FORMATS:raise ValueError('Choose a supported editorial recipe')
    label,requirements,requires_proof=FORMATS[chosen]
    brief=dict(viewer=niche.strip() or 'Người xem chưa được chỉ định',niche=niche.strip() or None,
               takeaway=next((b['quote'] for b in beats if len(b['quote'].split())>=6),first['quote'] if first else 'Review recording'),
               spoken_language=transcript.get('language','unverified'),hook=hooks[0],supporting_moment=proof[0]['asset'] if proof else 'Presenter only; real proof not assigned',
               ending=beats[-1]['quote'] if beats else 'Review the actual closing',format_id=chosen,format_label=label,format_reason=requirements,
               format_status='PROOF_REQUIRED · host fallback' if requires_proof and not proof else 'EDITORIAL_PROPOSAL',
               locked_meaning='Original recording controls claims, negations, names, numbers and qualifiers.')
    return dict(version=1,source_sha256=host['source_sha256'],brief=brief,hooks=sorted(hooks,key=lambda h:-h['score']),
                beats=beats,keep=[[0,round(host['duration']*30)/30]],uncertain=uncertain,script_comparison=mismatch,
                timing='ASR word timings · not human listening approval' if words else 'Supplied script timing · recorded words unverified',
                take_selection='Conservative: uncertain retakes and meaningful pauses retained',listening='UNVERIFIED')


def prepare(ws,key,settings,host,assets):
    """Invoked inside the existing bounded render worker, outside the workspace lock."""
    started=time.monotonic();prepared=settings['script'];source=copy.deepcopy(host)
    source['source_sha256']=media.sha(source['path'])
    ws.stage(key,'Transcribing locally; your recording stays on this computer')
    transcript=None;warning=None
    try:
        if ws.speech_setup.snapshot()['status']!='READY':raise ValueError('Set up local captions, or use the supplied script timing.')
        transcript=speech.load_or_transcribe(ws.root,source,language=None,
            terminology=[t for t in ('Codex','GitHub','FFmpeg','Recordly','Remotion','fal','Runway') if t.casefold() in prepared.casefold()])
    except ValueError as error:
        if not prepared.strip():raise ValueError('Local captions need setup. Choose Set up local captions, or add this take’s TXT/SRT. '+str(error)[-400:]) from error
        warning='Local recognition unavailable; using supplied script timing. Listen for deviations. '+str(error)[-300:]
    if transcript:
        # Transcript supplies timing/content. Only equivalent spelling/case from the
        # prepared script can replace a recognized token; missing words stay spoken.
        spellings={speech.key(w):w for w in re.findall(r'[^\W_]+',prepared) if not w.isdigit()}
        transcript=copy.deepcopy(transcript)
        for word in transcript['words']:
            normalized=speech.key(word['text'])
            if normalized in spellings and word['text'].strip('.,!?').casefold()==spellings[normalized].casefold():
                tail=re.search(r'[.,!?]+$',word['text']);word['text']=spellings[normalized]+(tail[0] if tail else '')
        if not ws.data['jobs'][key].get('creator_preserve_script'):settings['script']=speech.captions(transcript['words'])
    else:
        groups,timing=planner.script_groups(prepared,host['duration'],Path(host['path']))
        transcript=dict(language='unverified',words=[],segments=[dict(start=g[0][0],end=g[-1][1],text=' '.join(w[2] for w in g)) for g in groups],device=None,compute_type=None)
    result=explain(transcript,prepared,source,settings.get('niche',''),settings.get('story_format','auto'),settings.get('inserts',[]))
    result['broll_suggestions']=suggestions(result['beats'],assets,key,host['duration'])
    result.update(prepared_script=prepared,warning=warning,preparation_seconds=round(time.monotonic()-started,3),
                  reused_transcript=bool(transcript.get('cache_hit')),device=transcript.get('device'),compute_type=transcript.get('compute_type'),caption_schedule=schedule(settings['script']))
    # Atomic commit into this same job; explicit manual edits are blocked while queued.
    with ws.lock:
        job=ws.data['jobs'][key];job['settings']['script']=settings['script'];job['creator']=result
        if transcript.get('words'):job['transcript']=transcript
        job['creator_requested']=False;ws.save()
    return settings,result


def apply(plan,creator,transcript=None,script=None,host=None):
    plan['creator']=copy.deepcopy(creator)
    plan.setdefault('keep',copy.deepcopy(creator['keep']))
    words=(transcript or {}).get('words',[]);printed=[w[2] for p in plan.get('captions',[]) for w in p]
    timing_edited=bool(creator.get('caption_schedule') and schedule(script)!=creator['caption_schedule'])
    if words and len(words)==len(printed) and not timing_edited:
        page_size=max((len(p) for p in plan.get('captions',[])),default=4);pages=[];offset=0;fallbacks=[]
        phrases=planner.script_groups(script,host['duration'],Path(host['path']))[0] if script and host else [[w for p in plan['captions'] for w in p]]
        for phrase in phrases:
            block=words[offset:offset+len(phrase)];texts=printed[offset:offset+len(phrase)];offset+=len(phrase)
            valid=bool(block) and all(w['end']>w['start'] for w in block)
            if valid:group=[[w['start'],w['end'],text] for w,text in zip(block,texts)]
            else:
                group=copy.deepcopy(phrase);fallbacks.append([phrase[0][0],phrase[-1][1]])
            for i in range(0,len(group),page_size):pages.append(group[i:i+page_size])
        plan['captions']=pages;plan['creator']['caption_timing']='source_word_anchors' if not fallbacks else 'source_word_anchors_with_phrase_fallbacks'
        plan['creator']['caption_timing_fallback_ranges']=fallbacks
    else:plan['creator']['caption_timing']='manual_phrase_timing_preserved; review required' if timing_edited else 'supplied_phrase_timing_or_edited_word_count; review required'
    filtered=[]
    for page in plan.get('captions',[]):
        for start,end in plan['keep']:
            retained=[w for w in page if start-.0001<=w[0] and w[1]<=end+.0001]
            if retained:filtered.append(retained)
    plan['captions']=filtered
    clock=0
    for beat in plan['creator']['beats']:
        beat.update(edit_start=None,edit_end=None)
        offset=0
        for a,b in plan['keep']:
            left,right=max(a,beat['source_start']),min(b,beat['source_end'])
            if left<right:beat.update(edit_start=offset+left-a,edit_end=offset+right-a)
            offset+=b-a
    # Inferred cadence never trims words or pauses automatically.
    return plan
