"""Per-recording artifact versions and bounded insertion; no agent credentials required."""
import copy,json,re
from pathlib import Path
import artifacts,storyboard
from engine import media

def plain(script):return ' '.join(line.strip() for line in script.replace('\r','').splitlines() if line.strip() and not line.strip().isdigit() and '-->' not in line)

class ArtifactStore:
    def __init__(self,workspace):self.ws=workspace
    def records(self):return self.ws.data.setdefault('artifacts',{})
    def _check_job(self,job):
        if job['status'] in ('Queued','Rendering'):raise ValueError('Wait for the current render before changing its scenes.')
    def _dirty(self,job):
        job.update(revision=job['revision']+1,status='Draft',stage='Scene changed; render a new export for review.')
    def _render_version(self,record,plan):
        version=record.get('version',0)+1;folder=self.ws.root/'artifacts'/record['id']/f'v{version:03d}'
        folder.resolve().relative_to((self.ws.root/'artifacts').resolve())
        generated=artifacts.render(plan,folder,self.ws.data['assets'][record['job']],self.ws.data['assets'])
        if record.get('version'):record.setdefault('versions',[]).append({k:copy.deepcopy(record[k]) for k in ('version','folder','sha256','plan')})
        record.update(version=version,folder=str(folder),sha256=media.sha(folder/'preview.mp4'),plan=generated,status=generated['status'])
        record.pop('pending_proposal',None)
        return record
    def generate(self,ids,evidence=None,spoken_confirmed=False,design=None):
        results=[]
        with self.ws.lock:
            for key in dict.fromkeys(ids):
                job=self.ws.data['jobs'][key];self._check_job(job);host=self.ws.data['assets'][key];settings=job['settings']
                if not settings['script'].strip():raise ValueError('Attach this recording’s script first.')
                proof=copy.deepcopy(evidence)
                if proof:
                    asset=self.ws.data['assets'].get(proof.get('asset'))
                    if not asset or asset['kind']!='reference':raise ValueError('Choose actual on-screen proof, separate from the style reference.')
                    if proof['asset']==settings.get('style_ref'):raise ValueError('This file is assigned only for pacing. Choose an on-screen proof asset explicitly.')
                    proof['duration']=asset['duration'];proof['source_sha256']=media.sha(asset['path'])
                ref=self.ws.data['assets'].get(settings.get('style_ref'),{}).get('analysis',{})
                reference=[dict(reference_id=ref.get('source_sha256'),source_range=o['source_range'],observation=o['observation'],status=o['status'],confidence=o['confidence'],rule_parameters=ref.get('profile',{})) for o in ref.get('observations',[])[:1]]
                proposal=storyboard.propose(settings['script'],host['duration'],Path(host['path']),proof,reference,spoken_confirmed)
                previous=self.ws.data.setdefault('storyboards',{}).get(key,{}).get('passages',[])
                mapping={}
                for i,p in enumerate(proposal['passages']):
                    if i<len(previous) and previous[i]['quote']!=p['quote'] and not any(x['quote']==p['quote'] for x in previous):mapping[p['id']]=previous[i]['id'];p['id']=previous[i]['id']
                for n,plan in enumerate(proposal['artifacts']):
                    plan['design']=copy.deepcopy(design or {})
                    if plan['type']=='demo' and all(plan['design'].get(k) for k in ('before','after')):
                        plan.update(kind='before_after',intended_visual='Supplied before/after images with consistent fit; verify they show the claimed change.',enabled=True,status='STORYBOARD · NARRATION PICKUP')
                    plan['passage_ids']=[mapping.get(id_,id_) for id_ in plan['passage_ids']]
                    identity=plan['type']+'|'+'|'.join(plan['passage_ids'])+'|'+(plan['title'] if plan.get('claim','').startswith('Show this repository') else plan['kind'] if plan['type']=='demo' else '')
                    existing=next((r for r in self.records().values() if r['job']==key and r.get('story_key')==identity),None)
                    if existing:
                        if existing['plan']['source_quote']!=plan['source_quote']:
                            existing.update(pending_proposal=plan,status='STALE · source passage changed')
                        results.append(existing);continue
                    import uuid
                    record=dict(id=uuid.uuid4().hex,job=key,story_key=identity,inserted=False,versions=[])
                    self._render_version(record,plan);self.records()[record['id']]=record;results.append(record)
                self.ws.data['storyboards'][key]=proposal
                self._dirty(job)
            self.ws.save()
        return [r['id'] for r in results]
    def edit(self,id_,changes,expected_version,regenerate=True):
        allowed={'title','duration','at','position','intensity','sound','sounds','enabled','source_quote','passage_ids','occurrence','evidence','design'}
        if set(changes)-allowed:raise ValueError('Unknown scene setting.')
        with self.ws.lock:
            record=self.records()[id_];job=self.ws.data['jobs'][record['job']];self._check_job(job)
            if expected_version!=record['version']:raise ValueError('This scene has a newer version. Reopen its settings.')
            plan=copy.deepcopy(record.get('pending_proposal',record['plan']))
            for k in record.get('manual_fields',[]):plan[k]=copy.deepcopy(record['plan'][k])
            plan.update(copy.deepcopy(changes))
            if plan.get('evidence') and plan['kind']=='placeholder':
                plan['kind']='software';plan['intended_visual']='Actual supplied screen footage; verify its own control, action and readable result.'
            if plan['position'] not in ('top','center','bottom') or type(plan['intensity']) not in (int,float) or not 0<=plan['intensity']<=1:raise ValueError('Choose a valid scene position and intensity.')
            current=self.ws.data.get('storyboards',{}).get(record['job'],{}).get('passages',[])
            if current and plan['source_quote'] not in [p['quote'] for p in current]:raise ValueError('Choose a passage from the current script; keep uncertain matches unassigned.')
            record['manual_fields']=sorted(set(record.get('manual_fields',[]))|set(changes))
            plan['review_status']='UNVERIFIED';plan['status']='NEEDS_REVIEW' if plan.get('narration_status')=='operator_confirmed' else 'STORYBOARD · NARRATION PICKUP'
            if plan['kind']=='placeholder':plan['status']='NEEDS_INPUT · proof capture'
            self._render_version(record,plan);self._dirty(job);self.ws.save()
    def insert(self,id_,enabled):
        with self.ws.lock:
            record=self.records()[id_];job=self.ws.data['jobs'][record['job']];self._check_job(job)
            if enabled and (record['status'].startswith(('STALE','NEEDS_INPUT')) or record['plan']['kind']=='placeholder'):raise ValueError(record['plan']['intended_visual'])
            record['inserted']=bool(enabled);self._dirty(job);self.ws.save()
    def toggle(self,id_,enabled):
        with self.ws.lock:
            record=self.records()[id_];job=self.ws.data['jobs'][record['job']];self._check_job(job)
            record['plan']['enabled']=bool(enabled);self._dirty(job);self.ws.save()
    def invalidate_script(self,key,script):
        text=plain(script)
        for r in self.records().values():
            if r['job']==key and r['plan']['source_quote'] not in text:r['status']='STALE · source passage changed'
    def apply(self,key,plan):
        for r in self.records().values():
            if r['job']!=key or not r.get('inserted') or not r['plan'].get('enabled',True):continue
            if r['status'].startswith(('STALE','NEEDS_INPUT')):raise ValueError('Regenerate or disable scene '+r['plan']['title']+' after the script/proof change.')
            scene=r['plan'];start=float(scene['at']);end=start+float(scene['duration']);length=self.ws.data['assets'][key]['duration']
            if end>length:raise ValueError('Scene '+scene['title']+' runs past the recording; shorten it or move its insertion.')
            if any(start<q['end'] and end>q['start'] for q in plan['proof']):raise ValueError('Scene '+scene['title']+' overlaps a manual cutaway. Move/disable one; manual work was preserved.')
            plan['proof'].append(dict(id='artifact-'+r['id'],start=start,end=end,file=str(Path(r['folder'])/'preview.mp4'),source_start=0,artifact_id=r['id'],artifact_version=r['version'],artifact_type=scene['type'],artifact_kind=scene['kind'],source_name=scene['title']))
            for cue in scene.get('events',[]):
                e=copy.deepcopy(cue);e['id']='artifact-'+r['id']+'-'+e['id'];e['anchor']['timeline_source_pts']=start+e['master_frame']/30;e['visual_disabled']=True;plan['events'].append(e)
        plan['proof'].sort(key=lambda q:q['start'])
        return plan
