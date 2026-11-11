"""Deterministic planner; paid API calls are deliberately absent."""
import argparse
import json
from video_kit import digest, read, write, validate, permission, sha

PROMPT_VERSION='selector-v1'


def select(cue, shortlist):
    if cue.get('keep_presenter') is True:
        return {'choice':'NO_EFFECT','reason':'Protected personal statement or deliberate hold','citations':[]}
    if cue.get('requires_result') and not cue.get('result_visible'):
        return {'choice':'REVIEW','reason':'The claimed result has no visible evidence','citations':[]}
    compatible=[s for s in shortlist if s.get('recipe_id') in cue.get('available_recipe_ids',[]) and s.get('citation')]
    if not compatible:
        return {'choice':'REVIEW','reason':'No authorized, retrievable compatible recipe','citations':[]}
    return {'choice':compatible[0]['recipe_id'],'reason':compatible[0]['editorial_reason'],'citations':[compatible[0]['citation']]}


def current_shortlist(retrieval):
    """Serialized retrieval is untrusted: revalidate BEFORE cache hits/selection."""
    if not retrieval.get('results'):return retrieval
    if not retrieval.get('manifest_path'):return {**retrieval,'results':[],'invalidated':'No resolvable manifest'}
    try:
        manifest=validate(read(retrieval['manifest_path']))
        if digest(manifest)!=retrieval.get('manifest_hash'):return {**retrieval,'results':[],'invalidated':'Manifest/rights changed'}
        assets={a['id']:a for a in manifest['assets']};rights={r['id']:r for r in manifest['rights']};segments={s['id']:s for s in manifest['segments']}
        valid=[]
        for candidate in retrieval['results']:
            s=segments.get(candidate.get('id'));a=assets.get(s['asset_id']) if s else None
            if not a or a.get('data_class')!=retrieval.get('data_class') or a['family_id'] in retrieval.get('exclude_families',[]):continue
            if not permission(rights[s['rights_id']],'index') or not s.get('annotation_approved'):continue
            if sha(a['path'])!=a['sha256']:continue
            expected={'asset_id':a['id'],'sha256':a['sha256'],'t_in_ms':s['t_in_ms'],'t_out_ms':s['t_out_ms']}
            if candidate.get('citation')!=expected or candidate.get('recipe_id')!=s['recipe_id']:continue
            valid.append({**candidate,**s,'data_class':a['data_class']})
        return {**retrieval,'results':valid}
    except (OSError,ValueError,KeyError):return {**retrieval,'results':[],'invalidated':'Source or rights unavailable'}


def route(cue, retrieval, cache_folder=None, model_revision='rules-v1',data_class='production'):
    retrieval=current_shortlist(retrieval)
    if retrieval.get('data_class') not in (None,data_class):retrieval={**retrieval,'results':[],'invalidated':'Fixture/production scope mismatch'}
    key=digest({'cue':cue,'shortlist':retrieval,'prompt':PROMPT_VERSION,'model_revision':model_revision,'parameters':{'max_candidates':3,'paid_budget':0}})
    path=None
    if cache_folder:
        from pathlib import Path
        path=Path(cache_folder)/(key+'.json')
        if path.exists():
            return {**read(path),'cache_hit':True}
    result={**select(cue,retrieval.get('results',[])[:3]),'cache_key':key,'cache_hit':False,'route':'local_rules','model_revision':model_revision,'api_spend':0,'tokens_in':0,'tokens_out':0,'host_codex_cost':'not included or measured by this kit'}
    if path: write(path,result)
    return result


def evaluate(rows):
    n=len(rows)
    hits=sum(r['prediction']==r['expected'] for r in rows)
    positive=[r for r in rows if r.get('retrieval_ground_truth')]
    recall=sum(len(set(r['retrieved'][:3]) & set(r['retrieval_ground_truth']))/len(set(r['retrieval_ground_truth'])) for r in positive)
    return {'n':n,'decision_accuracy':hits/n if n else None,'retrieval_queries':len(positive),'recall_at_3':recall/len(positive) if positive else None,'causal_engagement_claim':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('cue');p.add_argument('retrieval');p.add_argument('--cache')
    a=p.parse_args();print(json.dumps(route(read(a.cue),read(a.retrieval),a.cache),ensure_ascii=False,indent=2))
