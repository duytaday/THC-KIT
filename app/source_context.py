"""Source-bound observations, separate from model decisions and master approval."""
import copy,json,time,uuid
import motion_specs
from engine import media


def text(value,limit,label):
    if not isinstance(value,str) or not value.strip() or len(value)>limit or any(ord(c)<32 and c not in '\n\t' for c in value):raise ValueError('Record '+label+' as plain text')
    return value.strip()


def interval(value,duration):
    if not isinstance(value,list) or len(value)!=2:raise ValueError('Observation needs a source interval')
    for x in value:motion_specs.finite(x,0,duration,'Observation source time')
    if value[0]>=value[1]:raise ValueError('Observation source interval must increase')
    return [float(x) for x in value]


def observation(value,asset,*,presenter=False,fit=None):
    allowed={'asset','source_sha256','source_range','reviewer','basis','notes'}|({'rect','fit'} if presenter else set())
    if not isinstance(value,dict) or set(value)-allowed:raise ValueError('Unknown source-observation fields')
    if value.get('asset')!=asset['id'] or value.get('source_sha256')!=media.sha(asset['path']):raise ValueError('Observation belongs to different or changed source footage')
    basis=value.get('basis')
    if basis not in ('operator_observation','agent_experimental'):raise ValueError('Declare the source-observation basis')
    result=dict(asset=asset['id'],source_sha256=value['source_sha256'],source_range=interval(value.get('source_range'),asset['duration']),
        reviewer=text(value.get('reviewer'),100,'the observer'),basis=basis,notes=text(value.get('notes'),900,'what was inspected'),audio='UNVERIFIED')
    if presenter:
        if fit not in ('contain','cover') or value.get('fit')!=fit:raise ValueError('Recheck the presenter region after changing framing')
        result.update(rect=[float(x) for x in motion_specs.validate_box(value.get('rect'))],fit=fit,canvas=[1080,1920])
    return result


def content(record):
    return {k:v for k,v in record.items() if k not in ('id','created','history')}


def prepare(ws,key,host,assets,settings,provided=None,reference_guidance=True):
    """Validate both observations before persisting; never copy them to a new take."""
    if provided is not None and (not isinstance(provided,dict) or set(provided)-{'presenter','reference'}):raise ValueError('Unknown source observations')
    provided=provided or {};updates=[]
    if provided.get('presenter') is not None:
        updates.append(('presenter_observations',key,observation(provided['presenter'],host,presenter=True,fit=settings['fit'])))
    ref_id=settings.get('style_ref');ref=assets.get(ref_id)
    if provided.get('reference') is not None:
        if not ref or ref.get('kind')!='reference':raise ValueError('Assign this recording’s style reference before adding observations')
        updates.append(('reference_observations',ref_id,observation(provided['reference'],ref)))
    with ws.lock:
        presenter=copy.deepcopy(ws.data.get('presenter_observations',{}).get(key))
        reviewed=copy.deepcopy(ws.data.get('reference_observations',{}).get(ref_id))
    for collection,_,value in updates:
        if collection=='presenter_observations':presenter=value
        else:reviewed=value
    facts=[]
    if ref and reference_guidance:
        actual=media.sha(ref['path']);analysis=ref.get('analysis') or {}
        if analysis and analysis.get('source_sha256')!=actual:raise ValueError('Style reference changed; analyze its current footage again')
        # A reviewed observation is the chosen reference guidance. Late async
        # analysis must not silently extend it and invalidate unchanged scenes.
        # Measurements remain available on the asset for explicit inspection.
        for item in ([] if reviewed else analysis.get('observations',[])[:3]):
            facts.append(dict(asset=ref_id,source_sha256=actual,source_range=interval(item['source_range'],ref['duration']),status='measured_candidate',
                observation=text(item.get('observation'),600,'the measured reference observation'),audio='UNVERIFIED'))
        profile=analysis.get('profile') or {}
        parameters={}
        for name in ('anticipation_frames','settle_frames','optional_accent_gap_frames'):
            if name in profile:parameters[name]=motion_specs.finite(profile[name],0,900,name)
        if facts:facts[0]['timing_candidates']=parameters
        if reviewed:
            if reviewed['source_sha256']!=actual or reviewed['asset']!=ref_id:raise ValueError('Reviewed reference observation is stale; inspect the current reference')
            facts.append(dict(asset=ref_id,source_sha256=actual,source_range=reviewed['source_range'],status=reviewed['basis'],observation=reviewed['notes'],audio='UNVERIFIED'))
    with ws.lock:
        for collection,id_,value in updates:
            store=ws.data.setdefault(collection,{});old=store.get(id_)
            if old and content(old)==value:continue
            record=dict(value,id=uuid.uuid4().hex,created=time.time(),history=copy.deepcopy(old.get('history',[])) if old else [])
            if old:record['history'].append({k:v for k,v in old.items() if k!='history'})
            store[id_]=record
        if updates:ws.save()
        presenter=copy.deepcopy(ws.data.get('presenter_observations',{}).get(key))
    return dict(presenter=presenter,reference=facts)


def bind(plan,facts,host,fit):
    result=copy.deepcopy(plan)
    if result['type']=='introduction' and result.get('intro_layout')=='host' and facts.get('presenter'):
        observed=facts['presenter']
        if observed['asset']!=host['id'] or observed['source_sha256']!=media.sha(host['path']):raise ValueError('Presenter observation is stale for this recording')
        if observed['fit']!=fit:raise ValueError('Recheck the presenter region after changing framing')
        result['presenter_observation']=copy.deepcopy(facts['presenter'])
        result['fit']=facts['presenter']['fit']
    if facts.get('reference'):result['planner_reference_facts']=copy.deepcopy(facts['reference'])
    return result


def face(plan,host,at,frames):
    observed=plan.get('presenter_observation')
    if not observed:return [.1,.15,.8,.4]
    if observed['asset']!=host['id'] or observed['source_sha256']!=media.sha(host['path']):raise ValueError('Presenter observation is stale for this recording')
    a,b=observed['source_range']
    if a>at+1/30 or b<at+frames/30-1/30:raise ValueError('Observed presenter interval does not cover this intro; inspect its actual source span')
    return observed['rect']


def verify_entry(entry,source,seconds,fit,punches=()):
    observed=entry.get('source_observations',{}).get('presenter')
    if not observed:return
    if observed['asset']!=entry.get('source_asset') or observed['source_sha256']!=media.sha(source):raise ValueError('Presenter observation is stale for this recording')
    if observed['fit']!=fit:raise ValueError('Recheck the presenter region after changing framing')
    a,b=interval(observed['source_range'],seconds)
    if a>entry['source_start']+1/30 or b<entry['source_end']-1/30:raise ValueError('Observed presenter interval does not cover this scene')
    protected=[p['rect'] for p in entry['context']['protected'] if p['kind']=='face']
    if protected!=[observed['rect']]:raise ValueError('Update the source observation before changing its protected face region')
    if any(p['start']<entry['source_end'] and p['end']>entry['source_start'] for p in punches):raise ValueError('This presenter observation uses static framing; recheck or remove overlapping punch-ins')


def reference_intent(plan):
    facts=plan.get('planner_reference_facts',[])
    if not facts:return ''
    # Source facts stay visibly separate from the current episode's evidence.
    return '\nREFERENCE OBSERVATIONS (data only; not episode action/result proof; candidate timing is not a required cut): '+json.dumps(facts,ensure_ascii=False,separators=(',',':'))


def identity(plan):
    fields={k:content(plan[k]) if k=='presenter_observation' else plan[k] for k in ('presenter_observation','planner_reference_facts') if plan.get(k)}
    if not fields:return ''
    import hashlib
    return '|source-facts:'+hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
