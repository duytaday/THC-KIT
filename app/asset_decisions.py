"""B1 stock decisions for the existing headless editor; scoped B2 only after approval."""
import copy,os
from pathlib import Path
import asset_library,asset_models,asset_planner,asset_retrieval
from asset_store import Store
from revisions import digest

def select(ws,beat,config,job):
    root=asset_library.root(ws)
    if not (root/'assets.sqlite3').is_file() or beat.get('requires_proof') or beat.get('role')!='explain':return None,dict(status='NO_ILLUSTRATION',reason='Real proof and non-explanation beats keep their existing workflow')
    store=Store(root)
    try:
        found=asset_retrieval.search(store,beat['quote'],3)['results']
        found=[r for r in found if r['score']>=.15]
        if not found:return None,dict(status='NO_MATCH',mode='B1',reason='Keep presenter when library relevance is weak')
        candidates=[dict(asset_id=r['asset_id'],duration=r['duration'],usable_windows=r['usable_windows'],category=r['category'],caption=r['caption'],source_sha256=r['sha256'],proof_kind='illustration') for r in found]
        ctx=dict(episode_id=job.get('auto_episode_id',job['id']),source_revision=job['revision'],beat_id=beat['id'],script_span=dict(text=beat['quote'],timeline_in=beat['start'],timeline_out=min(beat['end'],beat['start']+4)),locked_style=copy.deepcopy(config['params']),candidates=candidates,requires_real_demo=False,cue_refs=[],rag_candidates=[dict(asset_id=r['asset_id'],score=r['score']) for r in found])
        mode='B1';fallback=None;plan=None
        registry=asset_models.registry(root);scope=digest(['A',config['creator'],config['name']]);active=registry.get('active_scopes',{}).get(scope,'B1')
        if active!='B1':
            entry=registry['runs'].get(active,{})
            if entry.get('state')=='active' and entry.get('human_approved') is True and entry.get('creator')==config['creator'] and entry.get('style')==config['name']:
                python=ws.data.get('stock_model_python') or os.environ.get('THC_MODEL_PYTHON')
                try:
                    if not python:raise ValueError('Local model runtime is not configured')
                    output=asset_models.infer(root,active,[ctx],python)['outputs'][0]
                    if output.get('error'):raise ValueError(output['error'])
                    plan=asset_planner.validate(output['plan'],ctx);mode='B2'
                except (ValueError,KeyError,RuntimeError) as error:fallback=str(error)
        if plan is None:plan=asset_planner.rules(ctx,ctx['rag_candidates'])
        receipt=dict(status='DRAFT_DECISION',mode=mode,active=active,fallback_to_B1=fallback,plan=plan,request=asset_planner.request_receipt(ctx,model=active),human_approved=False)
        if not plan['edits']:return None,receipt
        chosen=plan['edits'][0];asset=store.get(chosen['asset_id']);component=asset_planner.component(asset)
        component.update(offset=chosen['source_in'],timeline_at=chosen['timeline_in'],max_source_duration=chosen['source_out']-chosen['source_in'],tags=[beat['quote']],permission_evidence='User-directed stock illustration; '+asset['source_url']+' · '+str(asset['license'].get('name'))+'; training rights not inferred')
        if chosen['crop']!=[0,0,1,1]:
            w,h=asset['dimensions'];nx,ny,nw,nh=chosen['crop'];x,y=round(nx*w),round(ny*h)
            cw,ch=min(w-x,round(nw*w)),min(h-y,round(nh*h))
            if min(cw,ch)<2:return None,{**receipt,'status':'NATIVE_CROP_REJECTED','reason':'Normalized crop is too small at native source resolution; keep presenter'}
            component['crop']=[cw,ch,x,y]
        return component,receipt
    finally:store.close()
