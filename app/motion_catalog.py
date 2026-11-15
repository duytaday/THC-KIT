"""Versioned motion-source catalog. Hard eligibility precedes contextual ranking."""
import copy,json,math
from pathlib import Path
from engine import media

ROOT=Path(__file__).parent/'animation_runtime'
FAMILIES=('intro','title','badge','callout','comparison','counter','diagram','image_sequence','transition','cta')
def data():return json.loads((ROOT/'sources.json').read_text(encoding='utf8'))

def inventory():
    import motion_bridge,openshot_bridge
    d=data()
    states={'motion':motion_bridge.availability(),'libopenshot':openshot_bridge.status()}
    for source in d['providers']:
        source['runtime']=states.get(source['id'],dict(available=False,status='EXTERNAL_OUTPUT_IMPORT',reason='Import an explicitly supplied render; upstream app generation is not configured in Cutroom.'))
    d['catalog_sha256']=media.sha(ROOT/'sources.json')
    return d

def recommend(context,limit=5):
    if not isinstance(context,dict) or set(context)-{'family','duration','niche','aspect','available_inputs','reference_tags','complexity_budget'}:
        raise ValueError('Use declared family, duration, niche, aspect, inputs, reference tags and complexity budget.')
    family=context.get('family','title')
    if family not in FAMILIES:raise ValueError('Unknown scene family.')
    duration=context.get('duration',5)
    if type(duration) not in (int,float) or not math.isfinite(duration) or not 0<duration<=30:raise ValueError('Use a 0–30 second scene duration.')
    inputs=context.get('available_inputs',[])
    tags=context.get('reference_tags',[])
    if not isinstance(inputs,list) or not isinstance(tags,list) or len(inputs)>32 or len(tags)>32 or any(not isinstance(x,str) or len(x)>80 for x in inputs+tags):
        raise ValueError('Use bounded input and reference tag lists.')
    budget=context.get('complexity_budget',2)
    if type(budget) is not int or not 0<=budget<=3:raise ValueError('Complexity budget is 0–3.')
    niche=context.get('niche','')
    if not isinstance(niche,str) or len(niche)>100:raise ValueError('Niche is a short label.')
    catalog=inventory();providers={p['id']:p for p in catalog['providers']};accepted=[];excluded=[]
    for original in catalog['recipes']:
        r=copy.deepcopy(original);reasons=[]
        if family not in r['families']:reasons.append('Different scene purpose')
        if context.get('aspect','9:16') not in r['aspects']:reasons.append('Unsupported aspect')
        if duration<r['min_seconds']:reasons.append('Insufficient readable hold')
        missing=sorted(set(r['requires'])-set(inputs))
        if missing:reasons.append('Missing inputs: '+', '.join(missing))
        if r['complexity']>budget:reasons.append('Exceeds motion complexity budget')
        if not providers[r['provider']]['runtime'].get('available'):reasons.append('Runtime/setup not available')
        r['eligible']=not reasons;r['reasons']=reasons
        if reasons:excluded.append(r);continue
        overlap=len(set(tags)&set(r['tags']))
        r['score']=100+(8 if r.get('default_treatment') else 0)+overlap*12+(8 if niche.lower() in r['tags'] else 0)-r['complexity']*3
        r['why']=['Matches '+family,'Required inputs present','Renderer available']+(['Reference/style tags match'] if overlap else [])
        accepted.append(r)
    accepted.sort(key=lambda r:(-r['score'],r['id']))
    return dict(version=catalog['version'],catalog_sha256=catalog['catalog_sha256'],candidates=accepted[:max(1,min(10,limit))],excluded=excluded,
                authority='A recommendation is a treatment proposal, not source proof or editorial approval.')

def apply_recipe(spec,context,recipe_id,reference):
    rows={r['id']:r for r in data()['recipes']}
    if recipe_id not in rows:raise ValueError('Unknown versioned motion recipe.')
    row=rows[recipe_id]
    available=['recording','text']+(['reference'] if reference else [])
    result=recommend(dict(family=row['families'][0],duration=context['frames']/30,available_inputs=available),10)
    if recipe_id not in {r['id'] for r in result['candidates']}:
        raise ValueError('Recipe is not executable with the current source/reference/runtime inputs.')
    if row['provider']!='motion':raise ValueError('Import the supplied external render through its adapter first.')
    if any(o.get('component')!=row['component'] for o in spec['objects'] if 'text' in o):
        raise ValueError('Recipe component does not match this scene. Select the recipe component before rendering.')
    import motion_bridge
    return motion_bridge.apply(spec,context,row['easing'])

def search_sources(query,limit=30):
    if not isinstance(query,str) or len(query)>120:raise ValueError('Use a short catalog search.')
    rows=json.loads((ROOT/'source-index.json').read_text(encoding='utf8'))
    words=query.lower().split()
    return [r for r in rows if all(w in (r['provider']+' '+r['path']).lower() for w in words)][:max(1,min(limit,50))]

def register_render(ws,body):
    """Output-ingestion adapter for all six reviewed providers, with explicit provenance."""
    provider=body['provider'];sources={p['id']:p for p in data()['providers']}
    if provider not in sources:raise ValueError('Choose a reviewed provider.')
    asset=ws.data['assets'][body['asset']]
    if asset.get('kind')!='reference':raise ValueError('Import the external render with the explicit reference/illustration role first.')
    ws.evaluation_access.asset(asset)
    if media.sha(asset['path'])!=body.get('source_sha256'):raise ValueError('External render changed; reopen the current asset.')
    import animation_library
    key=animation_library.excerpt(ws,body['asset'],body['start'],body['end'],body['title'],permission=body.get('permission',''))
    with ws.lock:
        entry=ws.data['animation_library'][key]
        entry.update(external_provider=provider,upstream_repository=sources[provider]['repository'],
                     upstream_revision=sources[provider]['revision'],integration_kind='supplied_render_import',
                     external_claim='Illustration; never current-episode action/result proof',
                     redesign_required=True,provider_claim_verified=False,origin_note='Provider identity is user-declared; the supplied file hash is observed.')
        media.write_json(Path(entry['folder'])/'template.json',entry);ws.save()
    return dict(id=key,kind='reference_excerpt',editable=False,status=entry['status'],review_required=True)
