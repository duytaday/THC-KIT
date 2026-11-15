"""Current-episode scene selection and persistent, source-linked style evidence."""
import copy
import time
import uuid
from pathlib import Path

import creator_editor
import motion_specs
import motion_storyboard
import source_context
from engine import media
from revisions import Conflict, digest

FAMILIES=('intro','title','badge','callout','comparison','counter','diagram','image_sequence','transition','cta')
TEXT_COMPONENTS={'05','07','08','09','15','19'}


def _source(ws, observation):
    candidates=[ws.data['assets'].get(observation['asset'])]+list(ws.data['assets'].values())
    for asset in candidates:
        if not asset or asset.get('kind')!='reference' or asset.get('source_sha256')!=observation['source_sha256']:continue
        ws.evaluation_access.asset(asset)
        path=Path(asset['path'])
        if path.is_file() and media.sha(path)==observation['source_sha256']:return asset
    return None


def board(ws):
    with ws.lock:
        rows=[]
        for stored in ws.data.get('style_board',{}).values():
            row=copy.deepcopy(stored);asset=_source(ws,row)
            row.update(available=bool(asset),seek_asset=asset['id'] if asset else None,
                       state='SOURCE_LINKED_OBSERVATION' if asset else 'NEEDS_RELINK',
                       next_action='Inspect source range' if asset else 'Import the same source bytes to relink; observation retained.')
            rows.append(row)
        return dict(observations=rows,families=list(FAMILIES))


def save_observation(ws,body):
    with ws.lock:
        asset=ws.data['assets'][body['asset']];ws.evaluation_access.asset(asset)
        if asset['kind']!='reference':raise ValueError('Choose an imported reference video.')
        actual=media.sha(asset['path'])
        if body.get('source_sha256')!=actual:raise Conflict('Reference bytes changed. Reopen the source before recording an observation.')
        interval=source_context.interval(body['source_range'],asset['duration'])
        family=body['family']
        if family not in FAMILIES:raise ValueError('Choose a declared scene family.')
        visual=source_context.text(body['visual'],1500,'visible motion/layout observation')
        reviewer=source_context.text(body['reviewer'],120,'observer identity')
        confidence=motion_specs.finite(body.get('visual_confidence',.5),0,1,'Visual confidence')
        heard=body.get('can_listen',False)
        if type(heard) is not bool:raise ValueError('Declare audio access explicitly.')
        audio=source_context.text(body.get('audio'),1500,'heard audio observation') if heard else None
        audio_confidence=motion_specs.finite(body.get('audio_confidence',.5),0,1,'Audio confidence') if heard else None
        identity=digest([actual,interval,family,visual,reviewer,audio])
        previous=next((o for o in ws.data.get('style_board',{}).values() if o['identity']==identity),None)
        if previous:return dict(id=previous['id'],replayed=True)
        key=uuid.uuid4().hex
        row=dict(id=key,identity=identity,version=1,asset=asset['id'],source_sha256=actual,source_range=interval,
                 family=family,visual=visual,visual_confidence=confidence,reviewer=reviewer,
                 audio=audio,audio_confidence=audio_confidence,audio_status='OBSERVED' if heard else 'UNVERIFIED',
                 status='OBSERVATION_ONLY · not an approved preset or reusable proof',created=time.time())
        ws.data.setdefault('style_board',{})[key]=row;ws.save();return dict(id=key,replayed=False)


def read(ws,job_id):
    with ws.lock:
        job=ws.data['jobs'][job_id];host=ws.data['assets'][job_id];ws.evaluation_access.asset(host)
        source_sha=host.get('source_sha256') or media.sha(host['path'])
        cues=creator_editor.caption_cues(job['settings']['script'])
        passages=[dict(id='source-'+digest([source_sha,c['start'],c['end']])[:20],quote=c['text'],start=c['start'],end=c['end'],timing='supplied_timed_caption · speech not newly verified') for c in cues]
        if not passages:
            import storyboard
            passages,_=storyboard.passages(job['settings']['script'],host['duration'],Path(host['path'])) if job['settings']['script'].strip() else ([],None)
        choices=ws.data.get('scene_choices',{}).get(job_id,{})
        for passage in passages:
            passage['choice']=copy.deepcopy(choices.get(passage['id']))
            passage['scenes']=[dict(id=r['id'],version=r['version'],locked=r.get('locked',False),inserted=r.get('inserted',False),status=r['status']) for r in ws.data.get('artifacts',{}).values() if r['job']==job_id and (passage['id'] in r['plan'].get('passage_ids',[]) or (r['plan']['at']<passage['end'] and r['plan']['at']+r['plan']['duration']>passage['start']))]
        return dict(job=job_id,revision=job['revision'],source_sha256=source_sha,passages=passages,
                    reference=board(ws),library=[dict(id=r['id'],kind=r['kind'],title=r['title'],version=r.get('template_version',1),status=r['status'],editable=r['kind']=='native_spec') for r in ws.data.get('animation_library',{}).values()])


def create(ws,body):
    """One scene proposal. No automatic insertion, speech change or template write."""
    request=body.get('request_id')
    if not isinstance(request,str) or not 8<=len(request)<=128:raise ValueError('Use a stable scene request ID.')
    fingerprint=digest(body)
    with ws.lock:
        previous=ws.data.get('scene_plan_requests',{}).get(request)
        if previous:
            if previous['payload']!=fingerprint:raise Conflict('Scene request ID belongs to a different command.')
            return {**copy.deepcopy(previous['result']),'replayed':True}
        job=ws.data['jobs'][body['id']];ws.artifacts._check_job(job)
        if job.get('archived'):raise ValueError('Restore this recording before editing its scenes.')
        if type(body.get('revision')) is not int or body['revision']!=job['revision']:raise Conflict('Scene plan changed. Reopen it before creating a scene.')
        view=read(ws,job['id']);passage=next((p for p in view['passages'] if p['id']==body['passage']),None)
        if not passage:raise Conflict('This passage is no longer in the current script.')
        start=round(passage['start']*30)/30;end=round(passage['end']*30)/30
        if end-start<1 or end-start>30:raise ValueError('Choose a 1–30 second passage, or adjust the timed cue in advanced editing.')
        if any(r['job']==job['id'] and r.get('inserted') and r['plan'].get('enabled',True) and r['plan']['at']<end and r['plan']['at']+r['plan']['duration']>start for r in ws.data.get('artifacts',{}).values()):
            raise ValueError('This passage already has an inserted scene. Edit that instance or disable it explicitly; its lock is preserved.')
        component=body['component'];library_id=component[8:] if component.startswith('library:') else None
        if not library_id and component not in TEXT_COMPONENTS:raise ValueError('Choose a supported editable text component. Real control markers need observed current-episode proof.')
        title=motion_specs.clean_text(body['title'])
        reference=[];observation_id=body.get('observation')
        if observation_id:
            observation=ws.data['style_board'][observation_id];asset=_source(ws,observation)
            if not asset:raise ValueError('Relink the selected reference before using its observation.')
            if job['id'] not in asset.get('owner_jobs',[]) and job['settings'].get('style_ref')!=asset['id']:
                raise ValueError('Assign this style reference to the current recording first.')
            reference=[dict(asset=asset['id'],reference_id=observation['source_sha256'],source_sha256=observation['source_sha256'],source_range=observation['source_range'],observation=observation['visual'],status='selected_observation',confidence=observation['visual_confidence'])]
        template=ws.data.get('animation_library',{}).get(library_id) if library_id else None
        if library_id and (not template or template['kind']!='native_spec'):raise ValueError('Baked reference excerpts cannot become editable text templates.')
        scene_type=template['type'] if template else 'introduction' if component=='05' else 'demo'
        plan=dict(type=scene_type,kind='animation_spec',title=title,source_quote=passage['quote'],passage_ids=[passage['id']],occurrence=0,
                  intended_visual='Current-episode explanatory text; not evidence of a software result.',duration=end-start,at=start,
                  position='top',intensity=.5,sound='none',evidence=None,enabled=True,narration_status='pickup_or_recorded_words_unverified',
                  timing=passage['timing'],status='NEEDS_REVIEW',motion_style='balanced',reference_evidence=reference)
        host=ws.data['assets'][job['id']]
        if media.sha(host['path'])!=view['source_sha256']:raise Conflict('Recording bytes changed. Import the replacement before reusing source clocks.')
        if reference:plan['planner_reference_facts']=copy.deepcopy(reference)
        ctx,at=motion_storyboard.context(plan,host,ws.data['assets'],job.get('transcript'))
        ctx['required_texts']=[title]  # The buyer explicitly requested this visible title.
        if library_id:
            import animation_library
            prediction=animation_library.adapt(ws.root,library_id,ctx)
        else:
            spec=motion_specs.rules(ctx)
            for obj in spec['objects']:
                if obj.get('text') is not None:obj['component']=component
            prediction=dict(spec=motion_specs.validate(spec,ctx),model=dict(mode='rules',weights_loaded=False,version='scene-selection-v1'))
        if body.get('recipe_id'):
            import motion_catalog
            prediction['spec']=motion_catalog.apply_recipe(prediction['spec'],ctx,body['recipe_id'],reference)
        elif body.get('motion_easing'):
            import motion_bridge
            prediction['spec']=motion_bridge.apply(prediction['spec'],ctx,body['motion_easing'])
        plan=motion_storyboard.attach(plan,ctx,at,prediction)
        plan['reference_evidence']=reference
        if body.get('composition'):plan['composition']=copy.deepcopy(body['composition'])
        # Deterministic request identity makes an uncommitted render folder
        # discoverable; the artifact store preserves it and allocates a new version.
        scene_id=digest(['scene-plan',job['id'],request])[:32]
        record=dict(id=scene_id,job=job['id'],story_key='selected:'+passage['id']+':'+request,inserted=False,versions=[],manual_fields=['animation'])
        before=copy.deepcopy(ws.data)
        try:
            ws.artifacts._render_version(record,plan)
            ws.data.setdefault('artifacts',{})[scene_id]=record
            choices=ws.data.setdefault('scene_choices',{}).setdefault(job['id'],{})
            choices[passage['id']]=dict(component=component,template_version=template.get('template_version',1) if template else 'native-v1',observation=observation_id,
                                       source_sha256=view['source_sha256'],source_range=[start,end],scene=scene_id,role='illustration',created=time.time())
            ws.artifacts._dirty(job)
            result=dict(scene=scene_id,version=record['version'],revision=job['revision'],inserted=False,replayed=False)
            ws.data.setdefault('scene_plan_requests',{})[request]=dict(payload=fingerprint,result=copy.deepcopy(result))
            ws.save();return result
        except BaseException:
            ws.data=before;raise
