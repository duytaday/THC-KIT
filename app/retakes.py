"""Preview, apply and restore a source-bound repeated take."""
import copy
import json
import math
import re
import tempfile
import unicodedata
from pathlib import Path

import creator_editor
from engine import media
from engine.enhance import events_for
from revisions import Conflict, digest

FPS = 30
PAD = .10


def tokens(text):
    text = unicodedata.normalize('NFC', text).casefold()
    return re.findall(r"[^\W_]+(?:[.,]\d+)*|[%+−-](?=\d|\s|$)", text)


def timed_words(raw):
    words = []
    for i, word in enumerate(raw):
        a,b = word.get('start'),word.get('end')
        if (type(a) not in (int,float) or type(b) not in (int,float)
                or not math.isfinite(a) or not math.isfinite(b) or a<0 or a>=b
                or (words and a<words[-1]['end']-.001)):
            return []
        words.append(dict(word,id=i))
    return words


def protected(plan):
    for key in ('proof','punches','motion_specs'):
        for row in plan.get(key, []):
            yield row.get('start', row.get('source_start')), row.get('end', row.get('source_end'))
    clock, offset = [], 0.
    for a,b in plan['keep']:
        clock.append((a,b,offset))
        offset += b-a
    for row in events_for(plan,clock):
        # Account for audio offset as well as the picture hold.
        shift = row['sound'].get('offset_frames',0)
        low = min(row['start_frame'],row['master_frame']+shift)/FPS
        high = max(row['end_frame'],row['master_frame']+shift+1)/FPS
        for a,b,o in clock:
            left,right=max(low,o),min(high,o+b-a)
            if left<right:
                yield a+left-o,a+right-o
    if plan.get('cover'):
        remaining = plan['cover']['frames']/FPS
        for a,b in plan['keep']:
            end = min(b,a+remaining)
            yield a,end
            remaining -= end-a
            if remaining<=0:
                break
    for automation in plan.get('music', {}).get('automation', []):
        yield tuple(automation['source_range'])
    if plan.get('opening'):
        a,b=plan['keep'][0]
        yield a,min(b,a+3)


def proposal_options(plan, beats, raw_words, source_sha, length):
    words = timed_words(raw_words)
    if not words:
        return []
    spans = list(protected(plan))
    keep = plan['keep']
    rows = []
    for beat in beats:
        a,b = beat['source_start'],beat['source_end']
        text = beat['quote'].strip()
        matched = [w for w in words if w['end']>a+.001 and w['start']<b-.001]
        usable = (not beat.get('locked') and text.endswith(('.', '?', '!'))
                  and len(tokens(text))>=4 and bool(matched)
                  and all(w.get('probability',0)>=.75 for w in matched)
                  and tokens(text)==tokens(' '.join(w['text'] for w in matched)))
        if not usable:
            rows.append(None)
            continue
        left,right=matched[0]['start'],matched[-1]['end']
        rows.append(dict(id=beat['id'],quote=text,word_ids=[w['id'] for w in matched],
                         source_range=[left,right],edit_segments=creator_editor.segments(left,right,keep)))

    proposals = []
    for a,b in zip(rows,rows[1:]):
        if not a or not b or tokens(a['quote'])!=tokens(b['quote']):
            continue
        gap = b['source_range'][0] - a['source_range'][1]
        if not .30 <= gap <= 3:
            continue
        choices = []
        for remove, retain in ((a,b),(b,a)):
            start,end = remove['source_range']
            lo = math.floor((start-PAD)*FPS)/FPS
            hi = math.ceil((end+PAD)*FPS)/FPS
            if not 0 < lo < hi < length or hi-lo>12:
                continue
            if any(w['end']>lo-1/FPS and w['start']<hi+1/FPS and w['id'] not in remove['word_ids']
                   for w in words):
                continue
            if any(x < hi and y > lo for x,y in spans):
                continue
            mapping = creator_editor.segments(lo,hi,keep)
            if (len(mapping)!=1 or abs(mapping[0]['source_start']-lo)>1e-7
                    or abs(mapping[0]['source_end']-hi)>1e-7
                    or len(retain['edit_segments'])!=1
                    or abs(retain['edit_segments'][0]['source_start']-retain['source_range'][0])>1e-7
                    or abs(retain['edit_segments'][0]['source_end']-retain['source_range'][1])>1e-7):
                continue
            before,after=mapping[0]['edit_start'],mapping[0]['edit_end']
            if before<.2 or after>sum(y-x for x,y in keep)-.2:
                continue
            if any(lo < w[1] and hi > w[0] and not (w[0]>=lo and w[1]<=hi)
                   for page in plan.get('captions',[]) for w in page):
                continue
            cut = dict(keep_take=retain,drop_take=remove,source_cut=[lo,hi],master_cut=[before,after])
            cut['id']=digest([source_sha,cut])
            choices.append(cut)
        if choices:
            proposals.append(dict(takes=[a,b],choices=choices,
                reason='Exact transcript match with a pause. Repetition may be intentional; listen before choosing.'))
        if len(proposals)==20:
            break
    return proposals


def read(ws, job_id, export_id):
    with ws.lock:
        view = creator_editor.read(ws,job_id,export_id)
        job = ws.data['jobs'][job_id]
        host = ws.data['assets'][job_id]
        raw = job.get('transcript',{}).get('words',[])
        creator = job.get('creator')
        editable = view['editable'] and job.get('latest')==export_id and bool(creator)
        source_bound = bool(creator and creator.get('source_sha256')==host.get('source_sha256'))
        proposals = proposal_options(view['plan'],creator['beats'],raw,host['source_sha256'],host['duration']) if editable and source_bound else []
        latest = job.get('retake_history',[])
        undo = latest[-1] if latest and latest[-1]['revision']==job['revision'] else None
        can_undo = (undo and undo['action']=='apply' and job.get('latest')==export_id
                    and job['status'] not in ('Queued','Rendering') and not job.get('archived'))
        return dict(job=job_id,export=export_id,sha256=view['sha256'],revision=job['revision'],
                    source_sha256=host.get('source_sha256'),editable=editable,proposals=proposals,
                    undo=dict(prior_export=undo['prior_export']) if can_undo else None,
                    status='PROPOSALS' if proposals else 'KEEP_OR_EDIT_MANUALLY')


def selection(ws, body, *, undo=False):
    view=read(ws,body['id'],body['export'])
    if (not (view['editable'] or undo and view['undo']) or type(body.get('revision')) is not int
            or body['revision']!=view['revision'] or body.get('sha256')!=view['sha256']):
        raise Conflict('The selected parent cut changed. Open the current export.')
    entry = ws.export(view['export'])
    master = Path(entry['folder'])/'edit.mp4'
    host = ws.data['assets'][view['job']]
    if media.sha(master)!=view['sha256'] or media.sha(host['path'])!=view['source_sha256']:
        raise Conflict('The master or source changed on disk.')
    return view, master


def preview(ws, body):
    with ws.lock:
        view, master = selection(ws,body)
        choice = next((c for p in view['proposals'] for c in p['choices'] if c['id']==body['choice']),None)
        if choice is None:
            raise Conflict('Choose a current retake proposal.')
    start,end = choice['master_cut']
    left,right=max(0,start-.8),min(ws.export(view['export'])['duration'],end+.8)
    key = digest([view['sha256'],choice['id']])
    folder = master.parent/'retake-previews'/key
    with ws.archive_lock:
        if not folder.exists():
            folder.parent.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(dir=folder.parent) as d:
                temp=Path(d)
                codecs=['-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart']
                media.ff('-ss',left,'-i',master,'-t',right-left,'-vf','scale=360:640',*codecs,temp/'before.mp4')
                graph = (f'[0:v]trim=start={left}:end={start},setpts=PTS-STARTPTS,scale=360:640[v0];'
                         f'[0:a]atrim=start={left}:end={start},asetpts=PTS-STARTPTS[a0];'
                         f'[0:v]trim=start={end}:end={right},setpts=PTS-STARTPTS,scale=360:640[v1];'
                         f'[0:a]atrim=start={end}:end={right},asetpts=PTS-STARTPTS[a1];'
                         '[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]')
                media.ff('-i',master,'-filter_complex_threads','1','-filter_complex',graph,
                         '-map','[v]','-map','[a]',*codecs,temp/'after.mp4')
                media.write_json(temp/'preview.json',dict(parent=view['sha256'],choice=choice['id'],
                    before=media.sha(temp/'before.mp4'),after=media.sha(temp/'after.mp4'),
                    master_window=[left,right],splice=start-left))
                temp.rename(folder)
    return dict(id=key,master_window=[left,right],splice=start-left)


def preview_file(ws, export, key, name):
    if not re.fullmatch('[a-f0-9]{64}',key) or name not in ('before.mp4','after.mp4'):
        raise ValueError('Unknown retake preview.')
    folder=Path(ws.export(export)['folder'])/'retake-previews'/key
    record=json.loads((folder/'preview.json').read_text(encoding='utf-8'))
    path=folder/name
    if media.sha(path)!=record[name.split('.')[0]]:
        raise Conflict('Retake preview changed.')
    return path


def change(ws, body, action):
    request = body.get('request_id')
    if not isinstance(request,str) or not re.fullmatch('[a-zA-Z0-9_-]{8,96}',request) or body.get('confirmed') is not True:
        raise ValueError('Confirm the take choice and supply a stable request ID.')
    with ws.lock:
        job=ws.data['jobs'][body['id']]
        old=job.get('retake_requests',{}).get(request)
        signature=digest([action,body])
        if old:
            if old['signature']!=signature:
                raise Conflict('This request ID belongs to another retake operation.')
            return dict(old['result'],replayed=True)
        view,_=selection(ws,body,undo=action=='undo')
        creator=job['creator']
        before=copy.deepcopy(creator['keep'])
        if action=='undo':
            if not view['undo']:
                raise Conflict('The current revision has no retake cut to restore.')
            keep=copy.deepcopy(job['retake_history'][-1]['before'])
            choice=None
        else:
            choice=next((c for p in view['proposals'] for c in p['choices'] if c['id']==body.get('choice')),None)
            if not choice:
                raise Conflict('The retake proposal is no longer current.')
            key=digest([view['sha256'],choice['id']])
            if body.get('preview')!=key:
                raise ValueError('Generate the comparison preview for this exact cut first.')
            for name in ('before.mp4','after.mp4'):
                preview_file(ws,view['export'],key,name)
            lo,hi=choice['source_cut']
            keep=[[l,r] for a,b in before for l,r in ((a,min(b,lo)),(max(a,hi),b)) if l<r]
        old_state=copy.deepcopy(ws.data)
        try:
            creator.update(keep=keep,manual_cut_locked=True)
            job.update(revision=job['revision']+1,status='Draft',creator_requested=False)
            creator_editor.mark_export_revision(ws,job)
            job.setdefault('retake_history',[]).append(dict(action=action,before=before,after=keep,
                choice=choice,revision=job['revision'],prior_export=view['export']))
            result=dict(job=job['id'],revision=job['revision'],prior_export=view['export'],keep=keep,review_required=True)
            job.setdefault('retake_requests',{})[request]=dict(signature=signature,result=result)
            ws.save()
        except BaseException:
            ws.data=old_state
            raise
        return result


def dispatch(ws, body):
    action=body.get('operation')
    if action=='list':
        return read(ws,body['id'],body['export'])
    if action=='preview':
        return preview(ws,body)
    if action not in ('apply','undo'):
        raise ValueError('Choose list, preview, apply or undo.')
    return change(ws,body,action)
