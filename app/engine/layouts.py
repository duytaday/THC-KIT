"""Source-linked presenter PiP. One placement per cutaway; never chase the cursor."""
import math

W, H = 1080, 1920


def options(clip):
    layout = clip.get('layout', 'full_demo')
    shape, crop = presenter_options(clip)
    corner = clip.get('pip_corner', 'bottom_right' if shape=='circle' else 'auto')
    size = clip.get('pip_width', .25)
    if layout not in ('full_demo', 'presenter_pip'):
        raise ValueError('Choose a rendered layout: full_demo or presenter_pip.')
    if corner not in ('auto', 'top_left', 'top_right', 'bottom_left', 'bottom_right'):
        raise ValueError('Choose an available PiP corner.')
    if isinstance(size, bool) or not isinstance(size, (int, float)) or not math.isfinite(size) or not .18 <= size <= .36:
        raise ValueError('PiP width must be 0.18–0.36 of the canvas.')
    return layout, corner, size


def presenter_options(clip):
    shape=clip.get('pip_shape','rectangle')
    if shape not in ('rectangle','circle'):raise ValueError('Choose rectangle or circle for the presenter.')
    crop=clip.get('pip_crop',[.5,.38,1.])
    if not isinstance(crop,(list,tuple)) or len(crop)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in crop) or not 0<=crop[0]<=1 or not 0<=crop[1]<=1 or not 1<=crop[2]<=3:
        raise ValueError('Presenter crop is [center x, center y, zoom]: centers 0–1 and zoom 1–3.')
    return shape,list(crop)


def presenter_filter(label,decision,output):
    _,_,width,height=decision['rect'];shape=decision.get('shape','rectangle')
    if shape=='rectangle' and decision.get('crop',[.5,.38,1.])==[.5,.38,1.]:return f'[{label}]scale={width}:{height},setsar=1[{output}]'
    cx,cy,zoom=decision['crop']
    crop=f"crop=w='min(iw,ih)/{zoom}':h='min(iw,ih)/{zoom}':x='max(0,min(iw-ow,iw*{cx}-ow/2))':y='max(0,min(ih-oh,ih*{cy}-oh/2))'"
    if shape=='rectangle':
        crop=f"crop=w='min(iw,ih*{width}/{height})/{zoom}':h='ow*{height}/{width}':x='max(0,min(iw-ow,iw*{cx}-ow/2))':y='max(0,min(ih-oh,ih*{cy}-oh/2))'"
        return f'[{label}]{crop},scale={width}:{height},setsar=1[{output}]'
    mask="geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='255*clip(W/2-sqrt(pow(X-W/2,2)+pow(Y-H/2,2))+0.5,0,1)'"
    return f'[{label}]{crop},scale={width}:{height},setsar=1,format=rgba,{mask}[{output}]'


def intersects(a, b):
    x, y, w, h = a
    bx, by, bw, bh = b
    return x < bx+bw and bx < x+w and y < by+bh and by < y+h


def resolve(clip, protected):
    layout, corner, size = options(clip)
    result = dict(requested=layout, resolved='full_demo', reason='Full demo requested', rect=None)
    if layout == 'full_demo':
        return result
    width = round(W*size/2)*2
    shape,crop=presenter_options(clip)
    height = width if shape=='circle' else round(width*16/9/2)*2
    margin = 36
    boxes = {
        'bottom_right': [W-margin-width, H-margin-height, width, height],
        'bottom_left': [margin, H-margin-height, width, height],
        'top_right': [W-margin-width, margin, width, height],
        'top_left': [margin, margin, width, height],
    }
    choices = list(boxes) if corner == 'auto' else [corner]
    for name in choices:
        box = boxes[name]
        if not any(intersects(box, p) for p in protected):
            return dict(requested=layout, resolved=layout, corner=name, rect=box, shape=shape, crop=crop,
                        reason='Stable corner avoids observed control, result and captions')
    if corner != 'auto':
        raise ValueError('The chosen PiP corner covers protected content. Move it, reduce its size, choose Auto or Full demo.')
    result['reason'] = 'No safe PiP corner; preserve readable evidence in full demo'
    return result


def protected_scene_regions(scene, caption_position=None):
    protected=[[60,310 if caption_position=='top' else 1420,960,160]]
    animation=scene['animation'];ctx=animation['context'];spec=animation['spec']
    # A fixed corner must remain safe through entrances and replacement states.
    import motion_specs
    anchors={a['id']:a for a in ctx['anchors']}
    for obj in spec['objects']:
        bounds=[];first=motion_specs.object_start(obj,anchors)
        for frame in range(first,motion_specs.lifetime_end(obj,ctx)):
            pose=motion_specs.pose(obj['keyframes'],frame-first)
            if pose['opacity']<=.05:continue
            _,rect,_=motion_specs.object_state(obj,anchors,frame)
            bounds.append(motion_specs.pose_bounds(rect,pose))
        if bounds:
            x=min(b[0] for b in bounds);y=min(b[1] for b in bounds)
            right=max(b[0]+b[2] for b in bounds);bottom=max(b[1]+b[3] for b in bounds)
            protected.append([x*W,y*H,(right-x)*W,(bottom-y)*H])
    for anchor in ctx['anchors']:
        if anchor.get('roi'):
            x,y,w,h=anchor['roi'];protected.append([x*W,y*H,w*W,h*H])
    return protected


def compose_scene(render_plan, scene, start, end, proof=None):
    composition=scene.get('composition') or {}
    if not composition:return
    if set(composition)-{'layout','pip_shape','pip_corner','pip_width','pip_crop'}:
        raise ValueError('Unknown presenter composition field.')
    layout,_,_=options(composition)
    if layout=='full_demo':return
    protected=protected_scene_regions(scene,render_plan.get('caption_position'))
    decision=resolve(composition,protected)
    if decision['resolved']!='presenter_pip':
        raise ValueError('No safe presenter position. Reduce diameter, move the presenter or use full scene.')
    if proof is not None:proof['layout_decision']=decision
    else:render_plan.setdefault('presenter_scenes',[]).append(dict(start=start,end=end,decision=decision,background='paper_illustration'))


def place_preview_annotation(render_plan, scene):
    """Preview-only status must avoid the same swept motion, captions and PiP."""
    if scene['animation']['context'].get('voice_aligned',False):return None
    decisions=[q['decision'] for q in render_plan.get('presenter_scenes',[])]
    decisions += [q['layout_decision'] for q in render_plan.get('proof',[]) if q.get('layout_decision',{}).get('resolved')=='presenter_pip']
    if not decisions:return None  # Preserve existing full-scene previews.
    occupied=protected_scene_regions(scene,render_plan.get('caption_position'))
    occupied += [d['rect'] for d in decisions]
    for cy in (1340,80,1780,1120,600,960):
        rect=[60,cy-24,960,48]
        if not any(intersects(rect,r) for r in occupied):
            return dict(rect=rect,center=[540,cy],font_size=30,role='preview_only_storyboard_status')
    raise ValueError('No clear area for the preview status label. Move or resize the presenter, or simplify the scene.')
