"""Per-recording artifact versions and bounded insertion; no agent credentials required."""
import copy,json,re,time,uuid
from pathlib import Path
import artifacts,storyboard,source_context
from engine import media

def plain(script):return ' '.join(line.strip() for line in script.replace('\r','').splitlines() if line.strip() and not line.strip().isdigit() and '-->' not in line)

class ArtifactStore:
    def __init__(self,workspace):self.ws=workspace;self.generating=set()
    def records(self):return self.ws.data.setdefault('artifacts',{})
    def _check_job(self,job):
        if job['status'] in ('Queued','Rendering'):raise ValueError('Wait for the current render before changing its scenes.')
        if job.get('id') in self.generating:raise ValueError('Wait for this recording’s scene generation to finish.')
    def _dirty(self,job):
        job.update(revision=job['revision']+1,status='Draft',stage='Scene changed; render a new export for review.')
    def _render_version(self,record,plan,assets=None):
        version=record.get('version',0)+1;folder=self.ws.root/'artifacts'/record['id']/f'v{version:03d}'
        # A crash before the atomic workspace commit can leave an uncommitted
        # render folder. Retain it and allocate the next version on retry.
        while folder.exists():
            version+=1;folder=self.ws.root/'artifacts'/record['id']/f'v{version:03d}'
        folder.resolve().relative_to((self.ws.root/'artifacts').resolve())
        assets=assets if assets is not None else self.ws.data['assets']
        generated=artifacts.render(plan,folder,assets[record['job']],assets)
        if record.get('version'):record.setdefault('versions',[]).append({k:copy.deepcopy(record[k]) for k in ('version','folder','sha256','plan')})
        record.update(version=version,folder=str(folder),sha256=media.sha(folder/'preview.mp4'),plan=generated,status=generated['status'])
        record.pop('pending_proposal',None)
        return record
    def generate(self,ids,evidence=None,spoken_confirmed=False,design=None,animation_mode=None,animation_style=None,intro_layout=None,observations=None,reference_guidance=True,intro_headline=None):
        if animation_style not in (None,'balanced','maverick_fast'):raise ValueError('Choose a supported animation style')
        if intro_layout not in (None,'full','host'):raise ValueError('Choose full or host for the intro')
        if intro_layout=='host' and not animation_mode:raise ValueError('Choose an editable animation planner for the host intro')
        if type(reference_guidance) is not bool:raise ValueError('Choose whether reference observations guide these proposals')
        if observations and len(set(ids))!=1:raise ValueError('Record source observations on one recording at a time; they are never copied across a batch')
        if isinstance(intro_headline,str) and not intro_headline.strip():intro_headline=None
        if intro_headline is not None:
            import motion_specs
            intro_headline=motion_specs.clean_text(intro_headline)
            if len(set(ids))!=1:raise ValueError('Declare the intro promise for one recording at a time')
        results=[]
        for key in dict.fromkeys(ids):
            started=time.monotonic()
            with self.ws.lock:
                original=self.ws.data['jobs'][key];self._check_job(original)
                job=copy.deepcopy(original);assets=copy.deepcopy(self.ws.data['assets']);host=assets[key]
                previous=copy.deepcopy(self.ws.data.get('storyboards',{}).get(key,{}).get('passages',[]))
                existing_records=copy.deepcopy([r for r in self.records().values() if r['job']==key]);self.generating.add(key)
            try:
                settings=job['settings'];staged=[]
                if not settings['script'].strip():raise ValueError('Attach this recording’s script first.')
                facts=source_context.prepare(self.ws,key,host,assets,settings,observations,reference_guidance)
                proof=copy.deepcopy(evidence)
                if proof:
                    asset=assets.get(proof.get('asset'))
                    if not asset or asset['kind']!='reference':raise ValueError('Choose actual on-screen proof, separate from the style reference.')
                    if asset.get('media_is_reusable_proof') is False or asset.get('data_class') not in (None,'real_screen'):raise ValueError('Choose actual screen footage; an illustration or reference excerpt is not action proof')
                    if asset.get('data_class')=='reference_excerpt':raise ValueError('An archived reference animation is an illustration. Add it as a cutaway; capture this episode’s actual product result separately.')
                    if proof['asset']==settings.get('style_ref'):raise ValueError('This file is assigned only for pacing. Choose an on-screen proof asset explicitly.')
                    proof['duration']=asset['duration'];proof['source_sha256']=media.sha(asset['path'])
                    if proof.get('for_repo') and proof['for_repo'] not in storyboard.REPOS:raise ValueError('Choose a named repository for this proof')
                ref=assets.get(settings.get('style_ref'),{}).get('analysis',{})
                reference=[dict(reference_id=ref.get('source_sha256'),source_range=o['source_range'],observation=o['observation'],status=o['status'],confidence=o['confidence'],rule_parameters=ref.get('profile',{})) for o in ref.get('observations',[])[:1]]
                proposal=storyboard.propose(settings['script'],host['duration'],Path(host['path']),proof,reference,spoken_confirmed)
                if animation_style:
                    for plan in proposal['artifacts']:plan['motion_style']=animation_style
                mapping={}
                for i,p in enumerate(proposal['passages']):
                    if i<len(previous) and previous[i]['quote']!=p['quote'] and not any(x['quote']==p['quote'] for x in previous):mapping[p['id']]=previous[i]['id'];p['id']=previous[i]['id']
                for plan in proposal['artifacts']:
                    plan['passage_ids']=[mapping.get(id_,id_) for id_ in plan['passage_ids']]
                    if plan['type']=='introduction' and intro_layout=='host':plan['intro_layout']='host'
                    if plan['type']=='introduction' and intro_headline is not None:plan.update(title=intro_headline,headline_origin='declared_visual_promise')
                proposal['artifacts']=[source_context.bind(plan,facts,host,settings['fit']) for plan in proposal['artifacts']]
                candidate=None
                if animation_mode in ('base_rag','fine_tuned'):
                    import motion_policy
                    candidate=motion_policy.candidate(self.ws.root)
                def identity(plan):
                    kind='animation_spec' if animation_mode and plan['kind']!='placeholder' else plan['kind']
                    value=plan['type']+'|'+'|'.join(plan['passage_ids'])+'|'+(plan['title'] if plan.get('claim','').startswith('Show this repository') else kind if plan['type']=='demo' else '')
                    if animation_mode:
                        import motion_storyboard
                        value+='|animation:'+animation_mode+'|context:'+str(motion_storyboard.CONTEXT_VERSION)
                    if animation_style:value+='|style:'+animation_style
                    if plan['type']=='introduction' and intro_layout=='host':value+='|intro:host'
                    if plan.get('headline_origin')=='declared_visual_promise':value+='|headline:'+storyboard.digest(plan['title'])
                    if candidate:value+='|weights:'+candidate['checkpoint_sha256']+'|dataset:'+candidate['dataset_fingerprint']
                    value+=source_context.identity(plan)
                    return value
                previous_by_key={r.get('story_key'):r for r in existing_records}
                if animation_mode:
                    import motion_storyboard,motion_policy
                    transcript=job.get('transcript')
                    eligible=[(i,p) for i,p in enumerate(proposal['artifacts']) if p['kind']!='placeholder' and (identity(p) not in previous_by_key or previous_by_key[identity(p)]['plan']['source_quote']!=p['source_quote'])]
                    prepared=[motion_storyboard.context(p,host,assets,transcript) for _,p in eligible]
                    predictions=motion_policy.infer(self.ws.root,[ctx for ctx,_ in prepared],animation_mode,media.sha(host['path'])) if prepared else []
                    if candidate and any(p['model'].get('version')!=candidate['version'] or p['model'].get('checkpoint_sha256')!=candidate['checkpoint_sha256'] for p in predictions):raise ValueError('Model candidate changed during generation; previous scenes were preserved')
                    for (i,p),(ctx,at),prediction in zip(eligible,prepared,predictions):proposal['artifacts'][i]=motion_storyboard.attach(p,ctx,at,prediction)
                for n,plan in enumerate(proposal['artifacts']):
                    plan['design']=copy.deepcopy(design or {})
                    if not animation_mode and plan['type']=='demo' and all(plan['design'].get(k) for k in ('before','after')):
                        plan.update(kind='before_after',intended_visual='Supplied before/after images with consistent fit; verify they show the claimed change.',enabled=True,status='STORYBOARD · NARRATION PICKUP')
                    story_key=identity(plan);existing=previous_by_key.get(story_key)
                    if existing:
                        if existing['plan']['source_quote']!=plan['source_quote']:
                            existing.update(pending_proposal=plan,status='STALE · source passage changed')
                        else:proposal['artifacts'][n]=copy.deepcopy(existing['plan'])
                        staged.append(existing);continue
                    record=dict(id=uuid.uuid4().hex,job=key,story_key=story_key,inserted=False,versions=[])
                    self._render_version(record,plan,assets);staged.append(record)
                if candidate and motion_policy.candidate(self.ws.root)['version']!=candidate['version']:raise ValueError('Model candidate changed during generation; previous scenes were preserved')
                with self.ws.lock:
                    current=self.ws.data['jobs'][key]
                    if current['revision']!=job['revision'] or current['status'] in ('Queued','Rendering'):raise ValueError('Project changed during generation; stale proposals were not applied. Generate again from the current script.')
                    for record in staged:self.records()[record['id']]=record
                    self.ws.data.setdefault('storyboards',{})[key]=proposal;self._dirty(current);self.ws.save();results.extend(staged)
                    self.ws.data.setdefault('generation_attempts',[]).append(dict(id=uuid.uuid4().hex,job=key,mode=animation_mode or 'native',style=animation_style or 'balanced',intro_layout=intro_layout or 'full',reference_guidance=reference_guidance,status='GENERATED',scene_ids=[r['id'] for r in staged],wall_seconds=time.monotonic()-started,source_script_sha256=storyboard.digest(settings['script'])))
                    self.ws.save()
            except Exception as error:
                with self.ws.lock:
                    self.ws.data.setdefault('generation_attempts',[]).append(dict(id=uuid.uuid4().hex,job=key,mode=animation_mode or 'native',style=animation_style or 'balanced',intro_layout=intro_layout or 'full',reference_guidance=reference_guidance,status='REJECTED',error=str(error),wall_seconds=time.monotonic()-started,source_script_sha256=storyboard.digest(job['settings']['script'])))
                    self.ws.save()
                raise
            finally:
                with self.ws.lock:self.generating.discard(key)
        return [r['id'] for r in results]
    def edit(self,id_,changes,expected_version,regenerate=True):
        allowed={'title','duration','at','position','intensity','sound','sounds','enabled','source_quote','passage_ids','occurrence','evidence','design','animation','locked'}
        if set(changes)-allowed:raise ValueError('Unknown scene setting.')
        with self.ws.lock:
            record=self.records()[id_];job=self.ws.data['jobs'][record['job']];self._check_job(job)
            if expected_version!=record['version']:raise ValueError('This scene has a newer version. Reopen its settings.')
            if 'locked' in changes:
                if set(changes)!={'locked'} or type(changes['locked']) is not bool:raise ValueError('Change the scene lock separately')
                record['locked']=changes['locked'];self.ws.save();return
            if record.get('locked'):raise ValueError('Unlock this scene before editing or regenerating it')
            plan=copy.deepcopy(record.get('pending_proposal',record['plan']))
            for k in record.get('manual_fields',[]):plan[k]=copy.deepcopy(record['plan'][k])
            plan.update(copy.deepcopy(changes))
            if plan['kind']=='animation_spec':
                import motion_policy,motion_specs
                if 'animation' in changes:
                    if changes['animation'].get('model')!=record['plan']['animation'].get('model'):raise ValueError('Model provenance is immutable; edit the scene specification instead')
                    if changes['animation'].get('source_observations')!=record['plan']['animation'].get('source_observations'):raise ValueError('Source observations are immutable in scene edits; review the source in Generate intro & demos')
                    plan['animation']['manual_override']=True
                if any(k in changes and changes[k]!=record['plan'].get(k) for k in ('at','source_quote')) and 'animation' not in changes:raise ValueError('Reassign animation source anchors when moving it to another spoken passage')
                if not changes and 'animation' not in record.get('manual_fields',[]):
                    ctx=plan['animation']['context'];mode=plan['animation']['model']['mode']
                    predicted=motion_policy.infer(self.ws.root,[ctx],mode,media.sha(self.ws.data['assets'][record['job']]['path']))[0]
                    plan['animation'].update(spec=predicted['spec'],model=predicted['model'])
                if 'duration' in changes:plan['animation']['context']['frames']=round(float(plan['duration'])*30)
                motion_specs.validate(plan['animation']['spec'],plan['animation']['context'])
            if plan['kind']=='generated_video' and not plan.get('evidence'):raise ValueError('Preserve the generated illustration’s source and provenance.')
            if plan.get('evidence') and plan['kind']=='placeholder':
                plan['kind']='software';plan['intended_visual']='Actual supplied screen footage; verify its own control, action and readable result.'
            if plan['position'] not in ('top','center','bottom') or type(plan['intensity']) not in (int,float) or not 0<=plan['intensity']<=1:raise ValueError('Choose a valid scene position and intensity.')
            current=self.ws.data.get('storyboards',{}).get(record['job'],{}).get('passages',[])
            if current and plan['source_quote'] not in [p['quote'] for p in current]:raise ValueError('Choose a passage from the current script; keep uncertain matches unassigned.')
            record['manual_fields']=sorted(set(record.get('manual_fields',[]))|set(changes))
            plan['review_status']='UNVERIFIED';plan['status']='NEEDS_REVIEW' if plan.get('narration_status')=='operator_confirmed' else 'STORYBOARD · NARRATION PICKUP'
            if plan['kind']=='placeholder':plan['status']='NEEDS_INPUT · proof capture'
            self._render_version(record,plan);self._dirty(job);self.ws.save()
            if 'animation' in changes:
                import uuid,time
                previous=record['versions'][-1]['plan']
                self.ws.data.setdefault('corrections',[]).append(dict(id=uuid.uuid4().hex,job=record['job'],source=self.ws.data['assets'][record['job']]['path'],source_sha256=media.sha(self.ws.data['assets'][record['job']]['path']),before={'animation':previous['animation']},after={'animation':copy.deepcopy(plan['animation'])},reason=None,editor_confirmed=False,created=time.time(),alignment='stable scene/source anchors; proposed and final animation specs; not a human training label until confirmed',task='animation_spec_edit_v1',source_span=[plan['at'],plan['at']+plan['duration']]))
                self.ws.save()
    def insert(self,id_,enabled):
        with self.ws.lock:
            record=self.records()[id_];job=self.ws.data['jobs'][record['job']];self._check_job(job)
            if enabled and (record['status'].startswith(('STALE','NEEDS_INPUT')) or record['plan']['kind']=='placeholder'):raise ValueError(record['plan']['intended_visual'])
            record['inserted']=bool(enabled);self._dirty(job);self.ws.save()
    def reuse(self,id_,library_id,version):
        import animation_library
        with self.ws.lock:
            record=self.records()[id_];job=self.ws.data['jobs'][record['job']];self._check_job(job)
            if record.get('locked') or record['version']!=version:raise ValueError('Unlock and reopen the current scene version before adapting a template')
            plan=copy.deepcopy(record['plan'])
            if plan['kind']!='animation_spec':raise ValueError('Generate an editable spec scene for this take first')
            prediction=animation_library.adapt(self.ws.root,library_id,plan['animation']['context'])
            plan['animation'].update(spec=prediction['spec'],model=prediction['model']);plan['status']='NEEDS_REVIEW'
            self._render_version(record,plan);record['manual_fields']=sorted(set(record.get('manual_fields',[]))|{'animation'});self._dirty(job);self.ws.save()
    def toggle(self,id_,enabled):
        with self.ws.lock:
            record=self.records()[id_];job=self.ws.data['jobs'][record['job']];self._check_job(job)
            record['plan']['enabled']=bool(enabled);self._dirty(job);self.ws.save()
    def invalidate_script(self,key,script):
        text=plain(script)
        for r in self.records().values():
            if r['job']==key and r['plan']['source_quote'] not in text:r['status']='STALE · source passage changed'
    def apply(self,key,plan):
        script_hash=storyboard.digest(self.ws.data['jobs'][key]['settings']['script'])
        plan['capture_requirements']=[dict(id='capture-'+p['passage_ids'][0]+'-'+storyboard.digest(p['title'])[:8],subject=p['title'],
            claim=p['claim'],source_quote=p['source_quote'],intended_visual=p['intended_visual'])
            for p in self.ws.data.get('storyboards',{}).get(key,{}).get('artifacts',[])
            if p['kind']=='placeholder' and p.get('source_script_sha256')==script_hash]
        for r in self.records().values():
            if r['job']!=key or not r.get('inserted') or not r['plan'].get('enabled',True):continue
            if r['status'].startswith(('STALE','NEEDS_INPUT')):raise ValueError('Regenerate or disable scene '+r['plan']['title']+' after the script/proof change.')
            scene=r['plan'];start=float(scene['at']);end=start+float(scene['duration']);length=self.ws.data['assets'][key]['duration']
            if end>length:raise ValueError('Scene '+scene['title']+' runs past the recording; shorten it or move its insertion.')
            if any(start<q['end'] and end>q['start'] for q in plan['proof']):raise ValueError('Scene '+scene['title']+' overlaps a manual cutaway. Move/disable one; manual work was preserved.')
            if scene['kind']=='animation_spec':
                import motion_render
                if any(start<e['source_end'] and end>e['source_start'] for e in plan.get('motion_specs',[])):raise ValueError('Animation scenes overlap; move or disable one before rendering')
                entry=copy.deepcopy(scene['animation']);entry.update(id=r['id'],source_start=start,source_end=end,source_asset=key,artifact_version=r['version'])
                for fact in entry.get('source_observations',{}).get('reference',[]):
                    reference=self.ws.data['assets'][fact['asset']]
                    if media.sha(reference['path'])!=fact['source_sha256']:raise ValueError('Style reference changed; recheck its source observations')
                    dependency=dict(file=reference['path'],source_sha256=fact['source_sha256'])
                    if dependency not in plan.setdefault('style_dependencies',[]):plan['style_dependencies'].append(dependency)
                plan.setdefault('motion_specs',[]).append(entry)
                plan['events'].extend(motion_render.sound_events(entry))
                proof=entry['context'].get('proof')
                if proof:
                    a=self.ws.data['assets'][proof['asset']]
                    if proof.get('source_sha256') and media.sha(a['path'])!=proof['source_sha256']:raise ValueError('Screen source changed; reassign its action/result anchors')
                    binding=dict(demonstrates=proof['for_repo']) if proof.get('for_repo') else {}
                    anchors={x['kind']:x['source_pts'] for x in entry['context']['anchors'] if x.get('source_pts') is not None and x['kind'] in ('control','contact','result')}
                    if 'control' in anchors:anchors['target']=anchors.pop('control')
                    plan['proof'].append(dict(id='motion-proof-'+r['id'],file=a['path'],start=start,end=end,source_start=proof.get('offset',0),artifact_type=scene['type'],artifact_kind='software',source_name=a['name'],anchors=anchors,**binding))
                continue
            evidence=scene.get('evidence') or {};binding=dict(demonstrates=evidence['for_repo']) if scene['kind']=='software' and evidence.get('for_repo') else {}
            plan['proof'].append(dict(id='artifact-'+r['id'],start=start,end=end,file=str(Path(r['folder'])/'preview.mp4'),source_start=0,artifact_id=r['id'],artifact_version=r['version'],artifact_type=scene['type'],artifact_kind=scene['kind'],source_name=scene['title'],**binding))
            for cue in scene.get('events',[]):
                e=copy.deepcopy(cue);e['id']='artifact-'+r['id']+'-'+e['id'];e['anchor']['timeline_source_pts']=start+e['master_frame']/30;e['visual_disabled']=True;plan['events'].append(e)
        plan['proof'].sort(key=lambda q:q['start'])
        return plan
