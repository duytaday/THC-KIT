"""Persist logical feedback once, and transfer only explicitly selected style fields."""
import copy, hashlib, json, math, re, time, uuid

STYLE_FIELDS=('style','fit','caption_position','motion_profile','motion_intensity',
              'music_mode','music_track','music_gain_db','brand_logo')


class Conflict(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def submit(ws,body):
    request=body.get('request_id')
    if not isinstance(request,str) or not re.fullmatch(r'[\w-]{8,128}',request):
        raise ValueError('Supply a stable request_id for this logical feedback submission')
    if set(body)-{'project','master','sha256','request_id','note','action','revision'}:
        raise ValueError('Unknown feedback field')
    key=digest([body.get('project'),body.get('master'),request]);payload=digest(body)
    with ws.lock:
        old=ws.data.get('feedback_requests',{}).get(key)
        if old:
            if old['payload_sha256']!=payload:raise Conflict('This request_id already belongs to different feedback')
            return {**copy.deepcopy(old['result']),'replayed':True}
        job=ws.data['jobs'][body['project']];entry=ws.export(body['master'])
        if entry['job']!=job['id']:raise ValueError('Feedback master belongs to another recording')
        from engine import media
        from pathlib import Path
        if entry['sha256']!=body.get('sha256') or media.sha(Path(entry['folder'])/'edit.mp4')!=entry['sha256']:
            raise ValueError('Feedback must identify the exact viewed master')
        ws.artifacts._check_job(job)
        if job['revision']!=body.get('revision'):raise Conflict('Draft changed; reopen it before submitting new feedback')
        note=body.get('note')
        if not isinstance(note,str) or not 8<=len(note.strip())<=2000 or not re.search(r'\b\d{1,2}:[0-5]\d\b',note):
            raise ValueError('Give a concrete feedback note with its viewed-master timecode')
        action=body.get('action',{});kind=action.get('kind');before=copy.deepcopy(ws.data)
        if getattr(ws,'_save_deferred',False):raise RuntimeError('Nested feedback transaction')
        ws._save_deferred=True
        try:
            if kind=='cue_gain':
                if set(action)!={'kind','id','gain_db'} or type(action['gain_db']) not in (int,float) or not math.isfinite(action['gain_db']) or not -60<=action['gain_db']<=6:
                    raise ValueError('Change one cue with an ID and a gain between -60 and 6 dB')
                events=copy.deepcopy(job['settings']['events']);event=next(e for e in events if e['id']==action['id'])
                event.setdefault('sound',{})['gain_db']=action['gain_db'];event.update(origin='manual',manual_override=True)
                ws.update([job['id']],{'events':events});changed=['settings.events.'+action['id']+'.sound.gain_db']
            elif kind=='scene':
                if set(action)!={'kind','id','version','changes'}:raise ValueError('Supply one scene, its version and its changed fields')
                if ws.artifacts.records()[action['id']]['job']!=job['id']:raise ValueError('Scene belongs to another recording')
                ws.artifacts.edit(action['id'],action['changes'],action['version']);changed=['scenes.'+action['id']+'.'+k for k in action['changes']]
            elif kind=='note':
                if set(action)!={'kind'}:raise ValueError('A note does not silently change the timeline')
                changed=[]
            elif kind=='pickup':
                if set(action)!={'kind','quote','requirement'} or not all(isinstance(action[k],str) and action[k].strip() for k in ('quote','requirement')):
                    raise ValueError('Specify the missing recorded sentence or result, and the exact pickup required')
                changed=[]
            else:raise ValueError('Choose scene, cue_gain, note or pickup feedback')
            record=dict(id=uuid.uuid4().hex,request_id=request,project=job['id'],master=entry['id'],sha256=entry['sha256'],
                        note=note.strip(),action=copy.deepcopy(action),changed_fields=changed,
                        before_revision=before['jobs'][job['id']]['revision'],after_revision=job['revision'],created=time.time(),
                        disposition='NEEDS_INPUT' if kind=='pickup' else 'APPLIED' if changed else 'RECORDED',
                        editor_confirmed=False,training_eligible=False)
            ws.data.setdefault('feedback',[]).append(record)
            result=dict(note_id=record['id'],revision=job['revision'],changed_fields=changed,disposition=record['disposition'],replayed=False)
            ws.data.setdefault('feedback_requests',{})[key]=dict(payload_sha256=payload,result=copy.deepcopy(result))
            ws._save_deferred=False;ws.save()
            return result
        except BaseException:
            # Render files may be orphaned if a process dies before this one atomic
            # workspace commit; they are never a second committed logical edit.
            ws.data=before;ws._save_deferred=False
            raise


def lock_style(ws,job_id,fields,revision):
    if not isinstance(fields,list) or len(fields)!=len(set(fields)) or set(fields)-set(STYLE_FIELDS):
        raise ValueError('Lock only explicitly selected transferable style fields')
    with ws.lock:
        job=ws.data['jobs'][job_id];ws.artifacts._check_job(job)
        if job['revision']!=revision:raise Conflict('Reopen the current draft before selecting style locks')
        job['style_locks']={k:copy.deepcopy(job['settings'][k]) for k in fields}
        job['style_lock_history']=job.get('style_lock_history',[])+[dict(fields=fields,revision=revision,time=time.time())]
        ws.save();return copy.deepcopy(job['style_locks'])


def transfer_style(ws,source,targets):
    with ws.lock:
        original=ws.data['jobs'][source];locked=original.get('style_locks',{})
        if not locked:raise ValueError('Select the style fields to lock before transferring them')
        targets=list(dict.fromkeys(targets));prepared=[]
        for id_ in targets:
            if id_==source:raise ValueError('Choose different target recordings')
            target=ws.data['jobs'][id_];ws.artifacts._check_job(target)
            own=set(target.get('manual_style_fields',[]))|set(target.get('style_locks',{}))
            changes={k:copy.deepcopy(v) for k,v in locked.items() if k not in own or target['settings'][k]==v}
            ws.valid(target,{**target['settings'],**changes});prepared.append((id_,changes,sorted(set(locked)-set(changes))))
        # Validate the complete batch before its single commit.
        previous=copy.deepcopy(ws.data);ws._save_deferred=True
        try:
            result=[]
            for id_,changes,skipped in prepared:
                ws.update([id_],changes);target=ws.data['jobs'][id_]
                target.setdefault('style_locks',{}).update(changes)
                target['style_transfer']=dict(source=source,fields=sorted(changes),source_revision=original['revision'],
                    basis='Selected style only; episode approval, script, anchors and proof are not transferred')
                result.append(dict(job=id_,applied=sorted(changes),manual_overrides_preserved=skipped))
            ws._save_deferred=False;ws.save();return result
        except BaseException:ws.data=previous;ws._save_deferred=False;raise
