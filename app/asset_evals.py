"""Matched development B0/B1/B2; never consumes sealed final or human gold."""
import copy,json,time,uuid
from pathlib import Path
from engine import media
import asset_learning,asset_models,asset_planner,asset_retrieval

def baseline(track,ctx,train,rag=False):
    if track=='A':
        ranked=None
        if rag:
            ranked=ctx.get('rag_candidates') or asset_retrieval.rank_descriptors(ctx)
        return asset_planner.rules(ctx,ranked)
    import motion_learning,motion_specs
    spec=motion_specs.rules(ctx)
    if rag:
        pool=[dict(id=r['id'],input=r['input'],target=r['target'],split='train') for r in train]
        example=motion_learning.retrieve(ctx,pool,version=3)[0]
        # Transfer only permitted treatment, never source words, rectangles or clocks.
        allowed=ctx.get('locked_style',{})
        for obj,reference in zip(spec['objects'],example['target']['objects']):
            if obj['component'] not in ('11','12','13'):
                for key in ('theme','box_style'):
                    if key in reference and key not in allowed:obj[key]=reference[key]
    return motion_specs.validate(spec,ctx)

def evaluate(root,run_id,python,limit=4):
    if not 1<=limit<=20:raise ValueError('Use1–20 development scenes for bounded evaluation')
    entry=asset_models.registry(root)['runs'][run_id];folder=Path(entry['folder']);config=json.loads((folder/'configuration.json').read_text(encoding='utf-8'));manifest,parts=asset_learning.load_package(config['dataset'])
    preflight=json.loads((folder/'token-preflight.json').read_text(encoding='utf-8'));excluded={r['id'] for r in preflight['excluded']}
    dev=[r for r in parts['development.jsonl'] if r['id'] not in excluded][:limit];train=[r for r in parts['train.jsonl'] if r['id'] not in excluded];contexts=[r['input'] for r in dev]
    if not contexts:raise ValueError('No eligible development contexts; do not open final to compensate')
    model=asset_models.infer(root,run_id,contexts,python);rows=[]
    for row,generated in zip(dev,model['outputs']):
        for arm in ('B0','B1','B2'):
            began=time.monotonic();error=None;plan=None
            try:
                if arm=='B2':
                    plan=generated['plan'];error=generated['error']
                    if error:raise ValueError(error)
                else:plan=baseline(entry['track'],row['input'],train,arm=='B1')
            except (ValueError,TypeError,KeyError,IndexError) as exc:error=str(exc)
            chosen=plan.get('edits',[{}])[0].get('asset_id') if plan and entry['track']=='A' and plan.get('edits') else None
            expected=row['target'].get('edits',[{}])[0].get('asset_id') if entry['track']=='A' and row['target'].get('edits') else None
            rows.append(dict(id=row['id'],arm=arm,valid=error is None,error=error,asset_matches_agent_experimental_label=chosen==expected if entry['track']=='A' else None,source_context_sha256=__import__('revisions').digest(row['input']),plan=plan,raw_output=generated['raw_output'] if arm=='B2' else None,expected_agent_experimental_plan=row['target'],source_binding=generated.get('source_binding') if arm=='B2' else None,runtime_seconds=generated['wall_seconds'] if arm=='B2' else time.monotonic()-began,autopick_is_human_preference=False))
    result=dict(track=entry['track'],run_id=run_id,checkpoint_sha256=model['adapter_sha256'],adapter_loaded=True,adapter_tensor_equality=model['adapter_tensor_equality'],device=model['device'],scope='Known development scene mechanical validation only; no full-episode/human preference claim',arms={arm:dict(valid=sum(r['valid'] for r in rows if r['arm']==arm),cases=len(dev),asset_matches_agent_label=sum(r['asset_matches_agent_experimental_label'] is True for r in rows if r['arm']==arm) if entry['track']=='A' else None) for arm in ('B0','B1','B2')},inputs_candidates_grader_fixed=True,renderer_exercised=False,sealed_final_read=False,human_preference=None,human_first_pass_acceptance=None,repair_minutes_per_finished_minute=None,full_mix_listening='UNVERIFIED',production_eligible=False,keep_active='B1',rows=rows)
    report=folder/'evaluations'/uuid.uuid4().hex/'development-evaluation.json';asset_learning.write(report,result)
    blocked='BLOCKED_BY_ANCHOR_REGRESSION' if any(r['arm']=='B2' and r.get('error') and 'anchor' in r['error'].lower() for r in rows) else 'BLOCKED_BY_DEVELOPMENT_REGRESSION' if result['arms']['B2']['valid']<result['arms']['B1']['valid'] else 'NEEDS_INDEPENDENT_FULL_EPISODE_REVIEW'
    asset_models.update(root,run_id,dict(state='development-evaluated',release_status=blocked,evaluation_path=str(report),evaluation_sha256=media.sha(report),inference_trace=model.get('inference_trace'),production_eligible=False))
    return {k:v for k,v in result.items() if k!='rows'}
