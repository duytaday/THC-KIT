"""Pre-render animation contract, shared by previews and assembled masters.

This validates source clocks and data, never asserts that a viewer heard a mix.
Final delivery still uses talking-head-qc/tools/qc_hook.py.
"""
import math
import motion_specs


def before_render(plan, source_seconds, fps=30):
    entries=plan.get('motion_specs',[])
    if not isinstance(entries,list):raise ValueError('motion_specs must be a list')
    if not entries:return []  # Existing projects need no migration.
    if fps!=30:raise ValueError('Animation schema v1 currently requires 30fps')
    spans=plan.get('keep') or [[0,source_seconds]]
    clock=[];offset=0
    for start,end in spans:
        start=round(start*fps)/fps;end=round(end*fps)/fps
        if not 0<=start<end<=source_seconds+.5/fps or clock and start<clock[-1][1]:raise ValueError('Invalid kept source spans')
        clock.append((start,end,offset));offset+=end-start
    seen=set();receipts=[]
    for entry in entries:
        scene_id=entry.get('id')
        if not isinstance(scene_id,str) or not scene_id or scene_id in seen:raise ValueError('Animation scene IDs must be unique')
        seen.add(scene_id)
        spec=motion_specs.validate(entry['spec'],entry['context'])
        start,end=entry['source_start'],entry['source_end']
        if any(type(t) not in (int,float) or not math.isfinite(t) for t in (start,end)):raise ValueError('Animation source times must be finite')
        frames=entry['context']['frames']
        if abs((end-start)*fps-frames)>.01:raise ValueError('Animation span must equal its editable frame count')
        for anchor in entry['context']['anchors']:
            if anchor['kind']=='visual' and abs(anchor['source_pts']-start-anchor['frame']/fps)>1/fps+.0001:
                raise ValueError('Reassign the observed visual cue to this episode’s source clock')
        kept=next((c for c in clock if c[0]-1e-6<=start<end<=c[1]+.5/fps+1e-6),None)
        if not kept:raise ValueError('Trim removed an animation span; reassign its source cues')
        frame=(kept[2]+start-kept[0])*fps
        if abs(frame-round(frame))>.01:raise ValueError('Animation onset must land on an output frame')
        model=entry.get('model',{})
        if model.get('mode')=='fine_tuned' and not model.get('checkpoint_sha256'):raise ValueError('Fine-tuned animation requires a checkpoint hash')
        receipts.append(dict(id=scene_id,master_start_frame=round(frame),frames=frames,
            voice_aligned=bool(entry['context'].get('voice_aligned')),missing=spec.get('missing',[]),
            review_status='NEEDS_REVIEW',reason='Schema validation does not establish viewing or listening.'))
    return receipts
