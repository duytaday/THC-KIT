"""Saved-master read model and narrowly scoped creator commands.

The UI submits intent, not an authoritative replacement timeline. All times here
are source seconds; retained segments explicitly map them to edited seconds.
"""
import copy
import json
import re
import uuid
from pathlib import Path

from engine import media
from revisions import Conflict, digest

STAMP = r'(\d{1,3}):(\d{2}):(\d{2})[,.](\d{1,3})'
RANGE = re.compile(r'^' + STAMP + r'\s*-->\s*' + STAMP + r'(?:[^\r\n]*)\r?$', re.M)


def _seconds(parts):
    return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2]) + int(parts[3].ljust(3, '0'))/1000


def caption_cues(script):
    """Text spans permit changing words without rewriting other cues or headers."""
    result = []
    for block in re.finditer(r'[^\r\n].*?(?=\r?\n[ \t]*\r?\n|\Z)', script, re.S):
        value = block.group(); match = RANGE.search(value)
        if not match:
            continue
        start = match.end()
        if value[start:start+2] == '\r\n': start += 2
        elif value[start:start+1] == '\n': start += 1
        end = len(value.rstrip('\r\n'))
        if start >= end: continue
        a, b = _seconds(match.groups()[:4]), _seconds(match.groups()[4:])
        if a >= b: continue
        result.append(dict(index=len(result), start=a, end=b, text=value[start:end],
                           span=[block.start()+start, block.start()+end]))
    return result


def segments(start, end, keep):
    result, offset = [], 0.
    for left, right in keep:
        a, b = max(start, left), min(end, right)
        if a < b:
            result.append(dict(source_start=a, source_end=b,
                               edit_start=offset+a-left, edit_end=offset+b-left))
        offset += right-left
    return result


def read(ws, job_id, export_id):
    with ws.lock:
        job = ws.data['jobs'][job_id]; entry = ws.export(export_id)
        if entry['job'] != job_id: raise ValueError('This cut belongs to another recording.')
        project = json.loads((Path(entry['folder'])/'project.json').read_text(encoding='utf8'))
        plan = project['plan']; script = project['settings']['script']
        keep = plan.get('keep') or [[0, ws.data['assets'][job_id]['duration']]]
        cues = caption_cues(script)
        beats = copy.deepcopy(plan.get('creator', {}).get('beats') or [])
        basis = 'saved_creator_beats'
        if not beats:
            basis = 'saved_timed_captions_not_verified_transcript'
            beats = [dict(id='caption-'+str(c['index']), source_start=c['start'],
                          source_end=c['end'], quote=c['text']) for c in cues]
        if not beats:
            basis = 'saved_caption_pages_not_verified_transcript'
            beats = [dict(id='page-'+str(i), source_start=p[0][0], source_end=p[-1][1],
                          quote=' '.join(w[2] for w in p)) for i,p in enumerate(plan.get('captions', [])) if p]
        for beat in beats:
            beat['segments'] = segments(beat['source_start'], beat['source_end'], keep)
            # A cue crossing a passage boundary belongs in advanced editing.
            beat['cues'] = [{k:c[k] for k in ('index','start','end','text')} for c in cues
                            if c['start'] >= beat['source_start']-1e-6 and c['end'] <= beat['source_end']+1e-6]
        return dict(job=job_id, export=export_id, sha256=entry['sha256'], revision=entry['revision'],
                    current_revision=job['revision'], editable=job['revision']==entry['revision'] and
                    job['status'] not in ('Queued','Rendering') and not job.get('archived'),
                    basis=basis, beats=beats, plan=plan, settings=project['settings'])


def _selection(ws, body):
    view = read(ws, body['id'], body['export'])
    job = ws.data['jobs'][body['id']]
    if type(body.get('revision')) is not int or body['revision'] != job['revision'] or not view['editable']:
        raise Conflict('This cut changed. Reopen the current cut before editing its passages.')
    if body.get('sha256') != view['sha256']:
        raise Conflict('Reopen the exact master shown in the player.')
    entry = ws.export(body['export'])
    try:actual=media.sha(Path(entry['folder'])/'edit.mp4')
    except OSError as error:raise Conflict('The exact master is missing. Restore this export or render a new version.') from error
    if actual != view['sha256']:
        raise Conflict('The master file changed. Render and review a new version.')
    beat = next((b for b in view['beats'] if b['id']==body['beat']), None)
    if beat is None or not beat['segments']: raise ValueError('Choose a retained passage in this cut.')
    return job, view, beat


def caption(ws, body, *, prepare=False):
    with ws.lock:
        job, view, beat = _selection(ws, body)
        allowed = {c['index'] for c in beat['cues']}; edits = body.get('cues')
        if not isinstance(edits, list) or not edits or len(edits)>len(allowed):
            raise ValueError('Choose timed captions wholly inside this passage; otherwise use advanced editing.')
        script = job['settings']['script']
        if script != view['settings']['script']: raise Conflict('Caption source changed; render the current revision.')
        cues = caption_cues(script); replacements = []; seen = set()
        for edit in edits:
            index, text = edit.get('index'), edit.get('text')
            if type(index) is not int or index not in allowed or index in seen:
                raise ValueError('Caption edit is outside the selected passage or duplicated.')
            if not isinstance(text,str) or not text.strip() or len(text)>500 or len(text.splitlines())>2 or '-->' in text or any(ord(c)<32 and c!='\n' for c in text):
                raise ValueError('Use one or two nonempty caption lines, up to 500 characters.')
            if any(not line.strip() for line in text.strip().splitlines()): raise ValueError('Keep text on each caption line.')
            seen.add(index); replacements.append((*cues[index]['span'], text.strip()))
        for start,end,text in sorted(replacements, reverse=True): script = script[:start]+text+script[end:]
        changes = {'script': script}
        return changes if prepare else save_passage(ws, body, changes)


def shot(ws, body, *, prepare=False):
    with ws.lock:
        job, view, beat = _selection(ws, body)
        ranges = [(s['source_start'],s['source_end']) for s in beat['segments']]
        # Generated scenes have their own versioned editor. Never silently cover
        # or remove one here, whether it is locked or merely enabled.
        for record in ws.data.get('artifacts',{}).values():
            p = record['plan']
            if record['job']==job['id'] and record.get('inserted') and p.get('enabled',True) and any(a<p['at']+p['duration'] and b>p['at'] for a,b in ranges):
                raise ValueError('This passage contains an inserted scene. Use its scene editor; its lock and sound are preserved.')
        chosen = body.get('asset')
        asset = ws.data['assets'].get(chosen) if chosen else None
        if chosen and (not asset or asset['kind']!='reference' or asset.get('source_role')!='broll' or job['id'] not in asset.get('owner_jobs',[])):
            raise ValueError('Choose B-roll assigned to this recording; style references stay off screen.')
        original = job['settings']['inserts']; result = copy.deepcopy(original)
        overlapping = [q for q in original if any(q['at']<b and q['at']+q['duration']>a for a,b in ranges)]
        if chosen and overlapping and all(q['asset']==chosen for q in overlapping) and all(any(q['at']<=a and q['at']+q['duration']>=b for q in overlapping) for a,b in ranges):
            return {} if prepare else dict(revision=job['revision'], status=job['status'], changed=False)
        if any(q.get('demonstrates') or q.get('visual_claim') for q in overlapping):
            raise ValueError('Rebind this real demonstration and its proof markers in the demo editor.')
        if any(p['start'] < b and p['end'] > a for p in view['plan'].get('proof', []) for a,b in ranges) and job.get('series_selection'):
            raise ValueError('Use the selected series scene editor to replace its bound footage.')
        if any(q.get('cue','').strip() for q in overlapping):
            raise ValueError('Resolve the spoken-anchor cutaway in advanced editing before splitting it.')
        for left,right in ranges:
            next_shots = []
            for q in result:
                start,end=q['at'],q['at']+q['duration']
                if end<=left or start>=right: next_shots.append(q); continue
                if q.get('locked'): raise ValueError('Unlock this cutaway before replacing it.')
                for a,b in ((start,min(end,left)),(max(start,right),end)):
                    if b<=a: continue
                    if b-a < 1/30-1e-7: raise ValueError('This change would leave a cutaway shorter than one frame. Adjust it in advanced editing.')
                    fragment=copy.deepcopy(q);fragment.update(id=uuid.uuid4().hex,at=a,duration=b-a,offset=q['offset']+a-start)
                    if fragment.get('anchors'):
                        for marker in ('target','contact','result'):
                            pts=fragment['anchors'].get(marker)
                            if pts is not None and not fragment['offset']<=pts<fragment['offset']+fragment['duration']:
                                fragment['anchors'].pop(marker)
                    next_shots.append(fragment)
            result=next_shots
        if chosen:
            # Across removed gaps, preserve the screen recording's progression.
            needed=max(b for a,b in ranges)-beat['source_start']
            if asset['duration']+1e-6 < needed: raise ValueError('The chosen footage is too short for the complete passage. Choose a longer take or use advanced editing.')
            for left,right in ranges:
                result.append(dict(id=uuid.uuid4().hex,asset=chosen,at=left,offset=left-beat['source_start'],duration=right-left,cue=''))
        result.sort(key=lambda q:q['at'])
        changes = {'inserts': result}
        return changes if prepare else save_passage(ws, body, changes)


def revise(ws, body):
    """Apply both controls to one saved passage in one revision."""
    with ws.lock:
        if not {'cues', 'asset'}.intersection(body):
            raise ValueError('Provide caption corrections or a shot choice.')
        changes = caption(ws, body, prepare=True) if 'cues' in body else {}
        if 'asset' in body:
            changes.update(shot(ws, body, prepare=True))
        return save_passage(ws, body, changes)


def save_passage(ws, body, changes):
    job = ws.data['jobs'][body['id']]
    before = job['settings']['script']
    changed = any(job['settings'][key] != value for key, value in changes.items())
    if not changed:
        return dict(revision=job['revision'], status=job['status'], changed=False)
    previous = copy.deepcopy(ws.data)
    was_deferred = getattr(ws, '_save_deferred', False)
    ws._save_deferred = True
    try:
        ws.update([job['id']], changes, {job['id']: body['revision']})
        selection = job.get('series_selection')
        if selection and selection['source_script_sha256'] == digest(before) and 'script' in changes:
            # Caption text changed. Source ranges and selected A/B/C assets stay bound.
            selection['source_script_sha256'] = digest(changes['script'])
        mark_export_revision(ws, job)
        ws._save_deferred = was_deferred
        ws.save()
    except BaseException:
        ws.data = previous
        ws._save_deferred = was_deferred
        raise
    return dict(revision=job['revision'], status=job['status'], changed=True, review_required=True)


def mark_export_revision(ws, job):
    job['passage_revision'] = job['revision']
    run = ws.data.get('auto_runs', {}).get(job.get('auto_run'))
    if run:
        entry = next(e for e in run['episodes'] if e.get('job') == job['id'])
        entry.update(passage_revision=job['revision'], status='DRAFT',
                     next_action='Render the updated cut from Outputs or resume this run.')
